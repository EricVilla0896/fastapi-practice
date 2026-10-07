# FastAPI LLM Job Analyzer

A FastAPI backend project that integrates a remote jobs API, asynchronous LLM processing, structured Pydantic validation, PostgreSQL persistence, authentication, webhook processing, and a production-oriented Retrieval-Augmented Generation (RAG) pipeline.

The project retrieves remote job listings, analyzes them against a target entry-level/junior technical profile using Gemini, stores structured results in PostgreSQL, and provides a RAG API for grounded question answering using PostgreSQL with pgvector.

## Features

### Backend & API

* FastAPI REST API
* Pydantic request and response validation
* PostgreSQL integration with psycopg
* API-key authentication
* Webhook-secret authentication
* Webhook event validation and duplicate-event protection
* Automatic OpenAPI/Swagger documentation
* Request validation and error handling

### Job Analysis & LLM Integration

* Himalayas Jobs API integration
* Asynchronous external API requests with `httpx`
* Concurrent LLM processing with `asyncio.gather()`
* Google Gemini API integration
* Structured LLM output validated with Pydantic
* PostgreSQL persistence of analyzed jobs
* Request timeouts and external API error handling

### RAG

* Document chunking with configurable chunk size and overlap
* Gemini embeddings
* PostgreSQL `pgvector` similarity search
* Configurable similarity thresholds
* Source/metadata filtering
* Cross-encoder reranking with `BAAI/bge-reranker-base`
* Grounded LLM generation using retrieved context
* No-answer handling when retrieved context is insufficient
* Document re-indexing
* SHA-256 document content hashing
* Skip-if-unchanged re-indexing
* Transaction-safe document replacement
* RAG API endpoint with returned source metadata

### Testing & Deployment

* Pytest API testing
* Mocking and monkeypatching for external services
* GitHub Actions CI
* PostgreSQL service integration in CI
* Docker containerization
* Docker Compose
* PostgreSQL persistence with Docker volumes

## Architecture

### Job Analysis

```text
Himalayas Jobs API
        ↓
   FastAPI + httpx
        ↓
   Job listings
        ↓
   asyncio.gather()
        ↓
   Gemini API
        ↓
Pydantic validation
        ↓
   PostgreSQL
        ↓
 /jobs/analyzed
```

### RAG Pipeline

```text
User Question
      ↓
Gemini Embedding
      ↓
PostgreSQL + pgvector
      ↓
Initial Similarity Retrieval
      ↓
Cross-Encoder Reranking
      ↓
Top Relevant Chunks
      ↓
Grounded Gemini Generation
      ↓
Answer + Sources
```

The RAG pipeline instructs the LLM to use only the retrieved context and return a no-answer response when the available context does not contain enough information.

## Technologies

* Python
* FastAPI
* Pydantic
* PostgreSQL
* pgvector
* psycopg
* httpx
* Google Gemini API
* Sentence Transformers
* `BAAI/bge-reranker-base`
* asyncio
* uvicorn
* python-dotenv
* pytest
* Docker
* Docker Compose
* GitHub Actions

## API Endpoints

### Job Analysis

#### `GET /jobs/analyze`

Searches the Himalayas Jobs API, analyzes returned jobs concurrently with Gemini, stores the results in PostgreSQL, and returns the analyses.

Example:

```text
GET /jobs/analyze?query=python
```

Each analysis contains:

* Job category
* Seniority
* Relevance
* Reason for the classification

#### `GET /jobs/analyzed`

Retrieves previously analyzed jobs stored in PostgreSQL.

```text
GET /jobs/analyzed
```

### RAG

#### `POST /rag/query`

Retrieves relevant document chunks using pgvector, reranks them with a cross-encoder, and generates a grounded answer using Gemini.

Example:

```json
{
  "question": "How many days can employees work remotely?"
}
```

An optional source can be provided to restrict retrieval:

```json
{
  "question": "How many days can employees work remotely?",
  "source": "company_policies.pdf"
}
```

The response contains the generated answer and the retrieved source chunks.

Example:

```json
{
  "answer": "Based on the provided context, employees may work remotely up to 5 days per week.",
  "sources": [
    {
      "content": "Employees may work remotely up to 5 days per week.",
      "source": "company_policies.pdf",
      "chunk_id": 1,
      "page": 1
    }
  ]
}
```

### Applications

#### `POST /applications`

Creates an application.

Requires the `X-API-Key` header.

#### `GET /applications`

Retrieves all applications.

#### `GET /applications/{id}`

Retrieves a specific application.

#### `PUT /applications/{id}`

Replaces an existing application.

#### `PATCH /applications/{id}`

Partially updates an application. Only supplied fields are updated.

#### `DELETE /applications/{id}`

Deletes an application.

### Webhooks

#### `POST /webhooks/application`

Processes an authenticated application webhook.

Requires the `X-Webhook-Secret` header.

The endpoint:

1. Validates the webhook payload with Pydantic.
2. Checks whether the event has already been processed.
3. Creates the application record.
4. Records the webhook event ID.
5. Rejects duplicate event IDs with `409 Conflict`.

#### `POST /webhooks/application/analyze`

Processes an authenticated application webhook and analyzes the application with Gemini before storing the application and webhook event.

The response includes the generated structured analysis and the created application ID.

## RAG Document Processing

RAG documents are processed through a re-indexing workflow:

```text
Document Text
     ↓
Validation
     ↓
SHA-256 Content Hash
     ↓
Chunking
     ↓
Check Existing Hash
     ↓
Skip if Unchanged
     ↓
Generate Embeddings
     ↓
Delete Previous Chunks
     ↓
Insert New Chunks
```

Document content is hashed before re-indexing. If the content has not changed, the existing indexed document is left untouched.

When a document changes, its previous chunks are replaced with the newly generated chunks.

## Example Structured Analysis

```json
{
  "category": "Junior Python/Backend Developer",
  "seniority": "Junior",
  "relevant": true,
  "reason": "The role matches the target Python backend and API integration skill set."
}
```

## Database

The project uses PostgreSQL with the `api_practice_schema` schema and a separate `rag` schema for vector documents.

### Tables

* `applications` — stores job applications
* `webhook_events` — tracks processed webhook event IDs
* `analyzed_jobs` — stores job listings and their LLM-generated analysis
* `rag.documents` — stores document chunks, embeddings, source metadata, and content hashes

The `webhook_events` table is used to prevent duplicate webhook processing.

The `rag.documents` table uses PostgreSQL `pgvector` embeddings for similarity search.

## Environment Variables

The application requires the following environment variables:

```env
DATABASE_URL=your_database_connection_string
API_KEY=your_api_key
WEBHOOK_SECRET=your_webhook_secret
GEMINI_API_KEY=your_gemini_api_key
```

A `.env.example` file is included in the repository as a template. Actual credentials are stored in `.env` and are not committed to GitHub.

## Installation

Clone the repository and create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Configure the environment variables and create the required PostgreSQL schema and tables.

## Running with Uvicorn

Start the development server:

```bash
uvicorn main:app --reload
```

FastAPI provides interactive API documentation at:

```text
/docs
```

The OpenAPI schema is available at:

```text
/openapi.json
```

## Docker

The project includes a `Dockerfile` for containerizing the FastAPI application.

Docker Compose is used to run the FastAPI application together with PostgreSQL.

The Compose configuration provides:

* FastAPI application container
* PostgreSQL container
* PostgreSQL environment configuration
* Internal container-to-container networking
* Persistent PostgreSQL storage using a named Docker volume
* Database initialization using the project SQL schema

## Testing

The project uses pytest for automated API testing.

Tests cover areas including:

* Successful API requests
* Request validation
* Authentication failures
* Webhook validation
* Duplicate webhook events
* LLM API failures
* Missing LLM output
* RAG retrieval
* RAG no-document handling
* RAG grounded response generation

Run the test suite with:

```bash
python -m pytest
```

External services are mocked during tests where appropriate so that API behavior can be tested without relying on live LLM responses or external APIs.

## Continuous Integration

GitHub Actions runs the automated test suite on pushes and pull requests.

The CI environment includes:

* Python
* PostgreSQL
* Required environment variables through GitHub Secrets
* Database schema initialization
* Pytest execution

## Error Handling

The API handles common failures including:

* Invalid request data
* Invalid authentication
* Request timeouts
* External API errors
* Network/request failures
* Duplicate webhook events
* Missing LLM responses
* Invalid structured LLM output
* Missing database records
* Missing RAG embeddings
* Insufficient RAG context

External service failures are converted into appropriate HTTP responses instead of exposing raw upstream responses.

## What This Project Demonstrates

This project demonstrates practical backend development involving:

* Building REST APIs with FastAPI
* Request and response validation with Pydantic
* API-key and webhook authentication
* PostgreSQL CRUD operations
* Webhook processing and idempotency
* Consuming external REST APIs asynchronously
* Concurrent asynchronous processing
* Integrating LLMs into application workflows
* Generating structured LLM output
* Validating LLM responses with Pydantic
* Persisting LLM-generated results
* Vector similarity search with PostgreSQL and pgvector
* Document chunking and embedding
* RAG retrieval and grounded generation
* Cross-encoder reranking
* Source and metadata filtering
* Document re-indexing and content hashing
* Automated API testing with pytest
* CI with GitHub Actions
* Docker and Docker Compose
* Handling external-service failures and timeouts

## Disclaimer

Job classifications and LLM-generated analyses are automated results and should not be treated as authoritative employment recommendations.