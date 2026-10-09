import os, httpx, asyncio
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import Literal
from database import get_connection
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pgvector import Vector
from database_docker import search_documents, rerank_results


load_dotenv()
gemini_client = genai.Client()

app = FastAPI()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


def authenticate_api_key(x_api_key: str | None = Header(default=None)):
    expected_key = os.getenv("API_KEY")
    if x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")

def authenticate_webhook_secret(x_webhook_secret: str | None = Header(default=None)):
    expected_secret = os.getenv("WEBHOOK_SECRET")
    if expected_secret != x_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid Webhook Secret")


class Application(BaseModel):
    company: str = Field(min_length=1, max_length=100)
    position: str = Field(min_length=1, max_length=100)
    salary: int = Field(gt=40000)

class ApplicationResponse(BaseModel):
    id: int
    company: str = Field(min_length=1, max_length=100)
    position: str = Field(min_length=1, max_length=100)
    salary: int = Field(gt=40000)

class ApplicationUpdate(BaseModel):
    company: str | None = Field(default=None, min_length=1, max_length=100)
    position: str | None = Field(default=None, min_length=1, max_length=100)
    salary: int | None = Field(default=None, gt=40000)

class Webhook(BaseModel):
    event: Literal["application.created"]
    event_id: str = Field(min_length=1)
    company: str = Field(min_length=1, max_length=100)
    position: str = Field(min_length=1, max_length=100)
    salary: int = Field(gt=40000)

class ApplicationAnalysis(BaseModel):
    category: str
    seniority: str
    relevant: bool
    reason: str

class AnalyzedJob(BaseModel):
    id: int
    title: str
    company: str
    description: str
    category: str
    seniority: str
    relevant: bool
    reason: str

class RAGQuery(BaseModel):
    question: str = Field(min_length=1)
    source: str | None = None

class RAGSource(BaseModel):
    content: str = Field(min_length=1)
    source: str = Field(min_length=1)
    chunk_id: int = Field(ge=1)
    page: int = Field(ge=1)

class RAGResponse(BaseModel):
    answer: str
    sources: list[RAGSource]


async def analyze_job(jobs):
    try:
        response = await gemini_client.aio.interactions.create(
            model="gemini-3.5-flash-lite",
            input=f"""
                Analyze this job application.

                title: {jobs["title"]}
                company: {jobs["companyName"]}
                description: {jobs["description"]}

                Job categories: Junior Python/Backend Developer, API & Integration Developer, 
                Junior Automation Developer, AI Automation Specialist, Junior Software Developer, 
                Technical/Application Support, AI Agent Developer.

                Seniority: Entry-level, Junior, Associate, Graduate; exclude genuinely mid/senior 
                roles requiring substantial professional experience.

                Relevance: Prioritize roles matching my Python, FastAPI/Flask, REST APIs, PostgreSQL/SQL, 
                OAuth, webhooks, n8n, API integrations, Docker, and growing LLM/AI automation skills.
            """,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": ApplicationAnalysis.model_json_schema()
            },
            timeout=10
        )
        if response.output_text is None:
            raise HTTPException(
                status_code=502,
                detail="LLM returned no structured response"
            )
        analysis = ApplicationAnalysis.model_validate_json(
            response.output_text
        )
        return analysis
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="LLM API request failed"
        )


@app.post("/applications", response_model=ApplicationResponse, status_code=201, dependencies=[Depends(authenticate_api_key)])
def create_application(application: Application):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO api_practice_schema.applications
            (company, position, salary)
            VALUES(%s, %s, %s)
            RETURNING id
            """,
            (application.company, application.position, application.salary)
        )
        data = cursor.fetchone()
    id = data[0]
    return {
        "id": id,
        "company": application.company,
        "position": application.position,
        "salary": application.salary
    }

@app.get("/applications", response_model=list[ApplicationResponse])
def read_applications():
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT * FROM api_practice_schema.applications
            """
        )
        application_data = cursor.fetchall()
    applications_list = [
        {
            "id": data[0],
            "company": data[1],
            "position": data[2],
            "salary": data[3]
        } for data in application_data
    ]
    return applications_list

@app.get("/applications/{id}", response_model=ApplicationResponse)
def read_application(id: int):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT * FROM api_practice_schema.applications
            WHERE id = %s
            """,
            (id,)
        )
        data = cursor.fetchone()
    if not data:
        raise HTTPException(status_code=404, detail="Application not found")
    return {
        "id": data[0],
        "company": data[1],
        "position": data[2],
        "salary": data[3]
    }


@app.patch("/applications/{id}", response_model=ApplicationResponse)
def patch_application(id: int, application: ApplicationUpdate):
    data = application.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates = []
    updated_values = []
    for key, value in data.items():
        updates.append(f"{key}=%s")
        updated_values.append(value)
    set_clause = ", ".join(updates)
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            UPDATE api_practice_schema.applications
            SET {set_clause}
            WHERE id = %s
            RETURNING *
            """,
            updated_values+[id]
        )
        data = cursor.fetchone()
    if not data:
        raise HTTPException(status_code=404, detail="ID does not exist")
    return {
        "id": data[0],
        "company": data[1],
        "position": data[2],
        "salary": data[3]
    }

@app.put("/applications/{id}", response_model=ApplicationResponse)
def update_application(id: int, application: Application):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE api_practice_schema.applications
            SET company = %s, position = %s, salary = %s
            WHERE id = %s
            RETURNING *
            """,
            (application.company, application.position, application.salary, id)
        )
        data = cursor.fetchone()
    if not data:
        raise HTTPException(status_code=404, detail="ID does not exist")
    return {
        "id": data[0],
        "company": data[1],
        "position": data[2],
        "salary": data[3]
    }

@app.delete("/applications/{id}")
def delete_application(id: int):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            DELETE FROM api_practice_schema.applications
            WHERE id = %s
            """,
            (id,)
        )
        count = cursor.rowcount
    if count == 0:
        raise HTTPException(status_code=404, detail="ID does not exist")
    return "Application deleted"


@app.post("/webhooks/application", dependencies=[Depends(authenticate_webhook_secret)])
def webhook(application: Webhook):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT *
            FROM api_practice_schema.webhook_events
            WHERE event_id = %s
            """,
            (application.event_id,)
        )
        data = cursor.fetchone()
        if data:
            raise HTTPException(status_code=409, detail="Event ID already processed")
        cursor.execute(
            """
            INSERT INTO api_practice_schema.applications
                (company, position, salary)
            VALUES (%s, %s, %s)
            """,
            (application.company, application.position, application.salary)
        )
        cursor.execute(
            """
            INSERT INTO api_practice_schema.webhook_events
                (event_id)
            VALUES (%s)
            """,
            (application.event_id,)
        )
    return {
        "message": "Webhook processed",
        "event_id": application.event_id
    }

@app.post("/webhooks/application/analyze", dependencies=[Depends(authenticate_webhook_secret)])
def analyze_webhook_application(application: Webhook):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT *
            FROM api_practice_schema.webhook_events
            WHERE event_id = %s
            """,
            (application.event_id,)
        )
        data = cursor.fetchone()
        if data:
            raise HTTPException(status_code=409, detail="Event ID already processed")
    prompt = f"""Analyze this job application.
            Job categories: Junior Python/Backend Developer, API & Integration Developer, 
            Junior Automation Developer, AI Automation Specialist, Junior Software Developer, 
            Technical/Application Support, AI Agent Developer.

            Seniority: Entry-level, Junior, Associate, Graduate; exclude genuinely mid/senior 
            roles requiring substantial professional experience.

            Relevance: Prioritize roles matching my Python, FastAPI/Flask, REST APIs, PostgreSQL/SQL, 
            OAuth, webhooks, n8n, API integrations, Docker, and growing LLM/AI automation skills.

            Company: {application.company}
            Position: {application.position}
            Salary: {application.salary}
        """
    try:
        response = gemini_client.interactions.create(
            model="gemini-3.5-flash-lite",
            input=prompt,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": ApplicationAnalysis.model_json_schema()
            },
            timeout=10
        )
        if response.output_text is None:
            raise HTTPException(status_code=502, detail="LLM returned no structured response")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="LLM API request failed")
    analysis = ApplicationAnalysis.model_validate_json(response.output_text)
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO api_practice_schema.applications
                (company, position, salary)
            VALUES (%s, %s, %s) RETURNING id
            """,
            (application.company, application.position, application.salary)
        )
        data = cursor.fetchone()
        application_id = data[0]
        cursor.execute(
            """
            INSERT INTO api_practice_schema.webhook_events
                (event_id)
            VALUES (%s)
            """,
            (application.event_id,)
        )
    return {
        "message": "Application analyzed and processed successfully",
        "event_id": application.event_id,
        "application_id": application_id,
        "analysis": analysis
    }


@app.get("/jobs/analyze")
async def analyze_jobs(query: str):
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(
                "https://himalayas.app/jobs/api/search",
                params={"q": query}
            )
            response.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="External API request timed out")
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=502, detail="External API returned an error")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="External API request failed")
    job_data = response.json()
    jobs = job_data["jobs"][:4]
    jobs_list = await asyncio.wait_for(
        asyncio.gather(*(analyze_job(job) for job in jobs)),
        timeout=30
    )
    with get_connection() as connection:
        cursor = connection.cursor()
        for job, analysis in zip(jobs, jobs_list):
            cursor.execute(
                """
                INSERT INTO api_practice_schema.analyzed_jobs
                (title, company, description, category, seniority, relevant, reason)
                VALUES(%s, %s, %s, %s, %s, %s, %s)
                """,
                (job["title"], job["companyName"], job["description"], analysis.category,
                analysis.seniority, analysis.relevant, analysis.reason)
            )
    return {
        "query": query,
        "jobs": jobs_list
    }

@app.post("/rag/query", response_model=RAGResponse)
def rag_query(data: RAGQuery):

    result = gemini_client.models.embed_content(
        model="gemini-embedding-2",
        contents=data.question,
        config=types.EmbedContentConfig(output_dimensionality=1536)
    )

    if not result.embeddings:
        raise HTTPException(status_code=404, detail="No embeddings found")

    [embedding_obj] = result.embeddings

    question_embedding = Vector(embedding_obj.values)

    search_results = search_documents(
        question_embedding,
        top_k=5,
        max_distance=0.3,
        source=data.source
    )

    if not search_results:
        return {
            "answer": "I don't have enough information to answer that question",
            "sources": []
        }

    reranked_results = rerank_results(
        data.question,
        search_results,
        top_k=2
    )

    context = "\n".join(content for content, distance, source, chunk_id, page in reranked_results)

    prompt = f"""
        Answer the question using only the provided context.
        Rules:
        - Use only information explicitly stated in the context.
        - Do not use outside knowledge.
        - If the context does not contain enough information to answer the question, say:
          "I don't have enough information to answer that question."
        Context:
        {context}
        
        Question:
        {data.question}
    """

    try:
        response = gemini_client.interactions.create(
            model="gemini-3.5-flash-lite",
            input=prompt,
            timeout=10
        )

        if response.output_text is None:
            raise HTTPException(status_code=404, detail="LLM API returned no structured response")

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    sources = [{
        "content": content,
        "source": source,
        "chunk_id": chunk_id,
        "page": page
    } for content, distance, source, chunk_id, page in reranked_results
    ]

    return {
        "answer": response.output_text,
        "sources": sources
    }

@app.get("/jobs/analyzed", response_model=list[AnalyzedJob])
def read_analyzed_jobs():
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT * FROM api_practice_schema.analyzed_jobs
            """
        )
        jobs = cursor.fetchall()
    if not jobs:
        raise HTTPException(status_code=404, detail="Jobs not found")
    jobs_list = [
        {
            "id": job[0],
            "title": job[1],
            "company": job[2],
            "description": job[3],
            "category": job[4],
            "seniority": job[5],
            "relevant": job[6],
            "reason": job[7]
        } for job in jobs
    ]
    return jobs_list