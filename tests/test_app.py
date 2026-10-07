from fastapi.testclient import TestClient
from main import app
import dotenv, os, uuid
from types import SimpleNamespace

dotenv.load_dotenv()
client = TestClient(app)


def test_get_applications():
    response = client.get("/applications")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_nonexistent_application():
    response = client.get("/applications/999999")
    assert response.status_code == 404
    assert isinstance(response.json(), dict)

def test_create_application_without_api_key():
    response = client.post("/applications", json={
        "company": "Test Company",
        "position": "Junior Backend Developer",
        "salary": 50000
    })
    assert response.status_code == 401
    assert isinstance(response.json(), dict)

def test_create_application_invalid_salary():
    response = client.post("/applications", json={
        "company": "Test Company",
        "position": "Junior Backend Developer",
        "salary": 30000
    }, headers={"X-Api-Key": os.getenv("API_KEY")})
    assert response.status_code == 422
    assert isinstance(response.json(), dict)

def test_patch_application_without_fields():
    response = client.patch("/applications/21", json={})
    assert response.status_code == 400
    assert isinstance(response.json(), dict)

def test_webhook_without_secret():
    response = client.post("/webhooks/application", json={
        "event": "application.created",
        "event_id": "pytest-test-001",
        "company": "Test Company",
        "position": "Junior Backend Developer",
        "salary": 50000
    })
    assert response.status_code == 401
    assert isinstance(response.json(), dict)

def test_webhook_invalid_event():
    response = client.post("/webhooks/application", json={
        "event": "something.else",
        "event_id": "pytest-test-001",
        "company": "Test Company",
        "position": "Junior Backend Developer",
        "salary": 50000
    }, headers={"X-Webhook-Secret": os.getenv("WEBHOOK_SECRET")})
    assert response.status_code == 422
    assert isinstance(response.json(), dict)

def test_webhook_duplicate_event():
    event_id = str(uuid.uuid4())
    response = client.post("/webhooks/application", json={
        "event": "application.created",
        "event_id": event_id,
        "company": "Test Company",
        "position": "Junior Backend Developer",
        "salary": 50000
    }, headers={"X-Webhook-Secret": os.getenv("WEBHOOK_SECRET")})
    assert response.status_code == 200
    assert isinstance(response.json(), dict)

    response = client.post("/webhooks/application", json={
        "event": "application.created",
        "event_id": event_id,
        "company": "Test Company",
        "position": "Junior Backend Developer",
        "salary": 50000
    }, headers={"X-Webhook-Secret": os.getenv("WEBHOOK_SECRET")})
    assert response.status_code == 409
    assert isinstance(response.json(), dict)

def test_analyze_application(monkeypatch):
    event_id = str(uuid.uuid4())
    def mock_gemini(*args, **kwargs):
        return SimpleNamespace(
            output_text = '{"category":"Junior Python/Backend Developer","seniority":"Junior","relevant":true,"reason":"Matches the target backend skill set."}'
        )
    monkeypatch.setattr(
        "main.gemini_client.interactions.create",
        mock_gemini
    )
    response = client.post("/webhooks/application/analyze", json={
        "event": "application.created",
        "event_id": event_id,
        "company": "Test Company",
        "position": "Junior Backend Developer",
        "salary": 50000
    }, headers={"X-Webhook-Secret": os.getenv("WEBHOOK_SECRET")})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert data["event_id"] == event_id
    assert "analysis" in data
    assert data["analysis"]["category"] == "Junior Python/Backend Developer"
    assert data["analysis"]["seniority"] == "Junior"
    assert data["analysis"]["relevant"] is True

def test_analyze_jobs(monkeypatch):
    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "jobs": [
                    {
                        "title": "Junior Python Developer",
                        "companyName": "Test Company",
                        "description": "Python backend development using REST APIs and PostgreSQL."
                    },
                    {
                        "title": "Junior Backend Developer",
                        "companyName": "Another Company",
                        "description": "Backend development with Python and FastAPI."
                    }
                ]
            }

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            pass

        async def get(self, *args, **kwargs):
            return MockResponse()

    async def mock_gemini(*args, **kwargs):
        return SimpleNamespace(
            output_text='{"category":"Junior Python/Backend Developer","seniority":"Junior","relevant":true,"reason":"Matches the target backend skill set."}'
        )

    monkeypatch.setattr(
        "main.httpx.AsyncClient",
        MockAsyncClient
    )

    monkeypatch.setattr(
        "main.gemini_client.aio.interactions.create",
        mock_gemini
    )

    response = client.get("/jobs/analyze?query=python")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, dict)
    assert data["query"] == "python"
    assert data["jobs"] is not None
    assert isinstance(data["jobs"], list)
    assert len(data["jobs"]) == 2

    assert data["jobs"][0]["category"] == "Junior Python/Backend Developer"
    assert data["jobs"][0]["seniority"] == "Junior"
    assert data["jobs"][0]["relevant"] is True

def test_rag_query(monkeypatch):
    def mock_question_embedding(*args, **kwargs):
        return SimpleNamespace(
            embeddings = [
                SimpleNamespace(
                    values= [1.0, 2.0, 3.0]
                )
            ]
        )

    context  = ["Employees may work remotely up to 3 days per week.", "Remote work must be approved by the employee's manager."]
    def mock_search_documents(query_embedding, top_k=5, max_distance=0.30, source=None):
        return [
            (context[0], 0.20, "company_policies.pdf", 1, 1),
            (context[1], 0.25,"company_policies.pdf", 2, 1)
        ]

    def mock_rerank_results(question, search_results, top_k=2):
        return [
            (context[0], 0.20, "company_policies.pdf", 1, 1),
            (context[1], 0.25, "company_policies.pdf", 2, 1)
        ]

    received_prompt = {}
    def mock_gemini(*args, **kwargs):
        received_prompt["input"] = kwargs["input"]
        return SimpleNamespace(
            output_text="Test successful"
        )

    monkeypatch.setattr(
        "main.gemini_client.models.embed_content",
        mock_question_embedding
    )

    monkeypatch.setattr(
        "main.search_documents",
        mock_search_documents
    )

    monkeypatch.setattr(
        "main.rerank_results",
        mock_rerank_results
    )

    monkeypatch.setattr(
        "main.gemini_client.interactions.create",
        mock_gemini
    )
    question = "Test question"
    response = client.post("/rag/query", json={
        "question": question
    })
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Test successful"
    assert question in received_prompt["input"]
    assert context[0] in received_prompt["input"]
    assert context[1] in received_prompt["input"]
    assert isinstance(data["sources"], list)

def test_rag_query_no_documents(monkeypatch):
    def mock_question_embedding(*args, **kwargs):
        return SimpleNamespace(
            embeddings=[
                SimpleNamespace(
                    values=[1.0, 2.0, 3.0]
                )
            ]
        )

    def mock_search_documents(query_embedding, top_k=5, max_distance=0.30, source=None):
        return []

    monkeypatch.setattr(
        "main.gemini_client.models.embed_content",
        mock_question_embedding
    )

    monkeypatch.setattr(
        "main.search_documents",
        mock_search_documents
    )
    response = client.post("/rag/query", json={
        "question": "Test question"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "I don't have enough information to answer that question"
    assert data["sources"] == []

def test_rag_query_gemini_failure(monkeypatch):
    def mock_question_embedding(*args, **kwargs):
        return SimpleNamespace(
            embeddings=[
                SimpleNamespace(
                    values=[1.0, 2.0, 3.0]
                )
            ]
        )

    context = ["Employees may work remotely up to 3 days per week.", "Remote work must be approved by the employee's manager."]
    def mock_search_documents(query_embedding, top_k=5, max_distance=0.30, source=None):
        return [
            (context[0], 0.20, "company_policies.pdf", 1, 1),
            (context[1], 0.25, "company_policies.pdf", 2, 1)
        ]

    def mock_rerank_results(question, search_results, top_k=2):
        return [
            (context[0], 0.20, "company_policies.pdf", 1, 1),
            (context[1], 0.25, "company_policies.pdf", 2, 1)
        ]

    def mock_gemini(*args, **kwargs):
        raise ValueError("Mock failure")

    monkeypatch.setattr(
        "main.gemini_client.models.embed_content",
        mock_question_embedding
    )

    monkeypatch.setattr(
        "main.search_documents",
        mock_search_documents
    )

    monkeypatch.setattr(
        "main.rerank_results",
        mock_rerank_results
    )

    monkeypatch.setattr(
        "main.gemini_client.interactions.create",
        mock_gemini
    )
    response = client.post("/rag/query", json={
        "question": "Test question"
    })
    assert response.status_code == 502
    data = response.json()
    assert "Mock failure" in data["detail"]

def test_rag_query_no_query():
    response = client.post("/rag/query", json={
        "question": ""
    })
    assert response.status_code == 422

def test_rag_query_gemini_no_output(monkeypatch):
    def mock_question_embedding(*args, **kwargs):
        return SimpleNamespace(
            embeddings = [
                SimpleNamespace(
                    values= [1.0, 2.0, 3.0]
                )
            ]
        )

    context  = ["Employees may work remotely up to 3 days per week.", "Remote work must be approved by the employee's manager."]
    def mock_search_documents(query_embedding, top_k=5, max_distance=0.30, source=None):
        return [
            (context[0], 0.20, "company_policies.pdf", 1, 1),
            (context[1], 0.25, "company_policies.pdf", 2, 1)
        ]

    def mock_rerank_results(question, search_results, top_k=2):
        return [
            (context[0], 0.20, "company_policies.pdf", 1, 1),
            (context[1], 0.25, "company_policies.pdf", 2, 1)
        ]

    def mock_gemini(*args, **kwargs):
        return SimpleNamespace(
            output_text=None
        )

    monkeypatch.setattr(
        "main.gemini_client.models.embed_content",
        mock_question_embedding
    )

    monkeypatch.setattr(
        "main.search_documents",
        mock_search_documents
    )

    monkeypatch.setattr(
        "main.rerank_results",
        mock_rerank_results
    )

    monkeypatch.setattr(
        "main.gemini_client.interactions.create",
        mock_gemini
    )

    response = client.post("/rag/query", json={
        "question": "Test question"
    })
    assert response.status_code == 404
    data = response.json()
    assert "LLM API returned no structured response" in data["detail"]