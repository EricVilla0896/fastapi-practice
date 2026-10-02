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
