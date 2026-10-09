# FastAPI LLM Job Analyzer

A production-oriented FastAPI backend integrating an external jobs API, asynchronous LLM processing, structured Pydantic validation, PostgreSQL persistence, authentication, webhook processing, and Retrieval-Augmented Generation (RAG).

The application retrieves remote job listings, analyzes them using Google Gemini, stores structured results in PostgreSQL, and provides context-grounded question answering using PostgreSQL with pgvector.

The project also demonstrates automated testing, Docker containerization, GitHub Actions CI/CD, GitHub Container Registry (GHCR), and deployment through a self-hosted Linux runner.

It serves as both a practical backend engineering project and a hands-on environment for learning API development, database integration, LLM applications, testing, containerization, and deployment.

## Features

### Backend & API

* FastAPI REST API
* Pydantic request and response validation
* PostgreSQL integration using psycopg
* API-key authentication
* Webhook-secret authentication
* Webhook validation and duplicate-event protection
* CRUD operations for applications
* Automatic OpenAPI documentation
* Request validation and error handling
* API health-check endpoint

### Job Analysis & LLM Integration

* Himalayas Jobs API integration
* Asynchronous external API requests using httpx
* Concurrent processing using `asyncio.gather()`
* Google Gemini API integration
* Structured LLM output validated with Pydantic
* PostgreSQL persistence of analyzed jobs
* Request timeouts and external API error handling

### Retrieval-Augmented Generation (RAG)

* Sentence-aware document chunking
* Configurable chunk size and overlap
* Gemini embeddings with 1,536 dimensions
* PostgreSQL pgvector similarity search
* Similarity thresholds and metadata filtering
* Cross-encoder reranking using `cross-encoder/ms-marco-MiniLM-L6-v2`
* Grounded LLM generation using retrieved context
* No-answer handling when retrieved context is insufficient
* Document re-indexing
* SHA-256 document content hashing
* Skip-if-unchanged re-indexing
* Transaction-safe document replacement
* Source metadata returned with answers

### Testing & Deployment

* Pytest API testing
* Mocking and monkeypatching
* GitHub Actions continuous integration
* PostgreSQL service for CI tests
* Docker image optimization using CPU-only PyTorch
* Docker Compose service orchestration
* Persistent PostgreSQL storage
* Container health checks
* GHCR image publishing
* Automated deployment using a self-hosted GitHub Actions runner

## Technologies

* Python 3.12
* FastAPI
* Pydantic
* PostgreSQL
* pgvector
* psycopg
* httpx
* Google Gemini API
* Sentence Transformers
* `cross-encoder/ms-marco-MiniLM-L6-v2`
* CPU-only PyTorch
* asyncio
* uvicorn
* python-dotenv
* pytest
* Docker
* Docker Compose
* GitHub Actions
* GitHub Container Registry
* Ubuntu / WSL2

## Architecture

### Job Analysis

```text
Himalayas Jobs API
        ↓
   FastAPI + httpx
        ↓
    Job Listings
        ↓
   asyncio.gather()
        ↓
     Gemini API
        ↓
 Pydantic Validation
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
Similarity Retrieval
      ↓
Cross-Encoder Reranking
      ↓
Top Relevant Chunks
      ↓
Grounded Gemini Generation
      ↓
Answer + Sources
```

The RAG pipeline retrieves relevant document chunks, reranks them, and uses the selected context to generate an answer. It supports a no-answer response when the available context is insufficient.

## API Endpoints

### Job Analysis

#### `GET /jobs/analyze`

Retrieves job listings from the Himalayas Jobs API, analyzes them concurrently using Gemini, validates the structured results, and stores the analyses in PostgreSQL.

Example:

```text
GET /jobs/analyze?query=python
```

#### `GET /jobs/analyzed`

Retrieves previously analyzed jobs stored in PostgreSQL.

```text
GET /jobs/analyzed
```

### Health Check

#### `GET /health`

Returns the API's basic health status.

Example response:

```json
{
  "status": "healthy"
}
```

Docker Compose uses this endpoint for the API container's health check. A successful response confirms that the endpoint responds; it does not independently guarantee that the database or external APIs are available.

### RAG

#### `POST /rag/query`

Retrieves relevant document chunks using pgvector, reranks them with a cross-encoder, and generates a grounded answer using Gemini.

Example request:

```json
{
  "question": "How many days can employees work remotely?"
}
```

An optional source filter can restrict retrieval:

```json
{
  "question": "How many days can employees work remotely?",
  "source": "company_policies.pdf"
}
```

The response contains the generated answer and relevant source metadata. Exact response fields depend on the application's response model.

### Applications

| Method   | Endpoint             | Purpose                         |
| -------- | -------------------- | ------------------------------- |
| `POST`   | `/applications`      | Create an application           |
| `GET`    | `/applications`      | Retrieve applications           |
| `GET`    | `/applications/{id}` | Retrieve a specific application |
| `PUT`    | `/applications/{id}` | Replace an application          |
| `PATCH`  | `/applications/{id}` | Partially update an application |
| `DELETE` | `/applications/{id}` | Delete an application           |

Application endpoints that require API-key authentication expect the `X-API-Key` header.

### Webhooks

#### `POST /webhooks/application`

Processes an authenticated application webhook.

The endpoint validates the payload, checks for duplicate event IDs, creates the application, and records the processed event.

Duplicate event IDs are rejected with `409 Conflict`.

#### `POST /webhooks/application/analyze`

Processes an authenticated application webhook and analyzes the application using Gemini before storing the application and webhook event.

The response includes the structured analysis and created application ID.

Webhook requests require the `X-Webhook-Secret` header.

## RAG Document Processing

Documents follow a re-indexing workflow:

```text
Document Text
     ↓
Validation
     ↓
SHA-256 Content Hash
     ↓
Sentence-Aware Chunking
     ↓
Check Existing Hash
     ↓
Skip if Unchanged
     ↓
Generate Embeddings
     ↓
Replace Previous Chunks
     ↓
Store Chunks and Metadata
```

Document content is hashed to detect changes. Unchanged documents can skip unnecessary embedding generation.

When a document changes, its indexed chunks are replaced through a transaction-safe operation.

Stored metadata can include the source name, chunk identifier, page information, content hash, and vector embedding.

## Database

The project uses PostgreSQL and pgvector.

The database contains application and webhook data, analyzed jobs, and RAG document chunks.

| Table / Schema   | Purpose                                                                 |
| ---------------- | ----------------------------------------------------------------------- |
| `applications`   | Stores application records                                              |
| `webhook_events` | Tracks processed webhook event IDs                                      |
| `analyzed_jobs`  | Stores job listings and LLM-generated analyses                          |
| `rag.documents`  | Stores document chunks, embeddings, source metadata, and content hashes |

The RAG implementation uses 1,536-dimensional vectors and an HNSW index for vector retrieval.

Database initialization SQL is stored in `db_schema/`:

* `00_extensions.sql`
* `fast_api_schema.sql`

These scripts initialize a new PostgreSQL data directory. Docker's initialization mechanism does not automatically rerun them against an existing database volume.

## Getting Started

There are two primary ways to run the project:

1. **Local development:** clone the repository, provide your own credentials, and run the application with Docker Compose.
2. **Automated deployment:** reproduce the CI/CD pipeline using your own GitHub configuration, secrets, container package, and deployment environment.

You do not need to set up GitHub Actions or a self-hosted runner just to run the application locally.

### Requirements

For the Docker Compose approach:

* Git
* Docker Engine with the Docker Compose plugin, or Docker Desktop
* A Google Gemini API key
* Your own values for the application's API key and webhook secret

The application also requires PostgreSQL with pgvector, which is provided by the Compose configuration.

### 1. Clone the Repository

```bash
git clone https://github.com/EricVilla0896/fastapi-practice.git
cd fastapi-practice
```

### 2. Configure Environment Variables

Create a local `.env` file based on `.env.example`.

```bash
cp .env.example .env
```

On Windows, you can copy the file using File Explorer or PowerShell.

Set the values required by your Compose configuration:

```env
API_KEY=your_own_api_key
WEBHOOK_SECRET=your_own_webhook_secret
GEMINI_API_KEY=your_own_gemini_api_key
```

Use your own credentials. Do not copy credentials from another developer or commit your `.env` file to Git.

The deployment Compose configuration defines the API's database connection settings and the PostgreSQL service configuration. If you customize the database credentials or connection settings, update the corresponding configuration consistently.

### 3. Start the Services

```bash
docker compose up -d
```

This starts the FastAPI application and PostgreSQL using the tracked Compose configuration.

Check the service status:

```bash
docker compose ps
```

Follow the API logs:

```bash
docker compose logs -f api
```

Check the health endpoint:

```bash
curl http://localhost:8000/health
```

The API is available at:

```text
http://localhost:8000
```

Interactive API documentation:

```text
http://localhost:8000/docs
```

OpenAPI schema:

```text
http://localhost:8000/openapi.json
```

### 4. Stop the Services

```bash
docker compose down
```

This stops and removes the Compose containers and network while preserving the named database volume.

**Do not use `docker compose down -v` unless you intentionally want to delete the associated named volumes and their stored database data.**

### Database Initialization

The initialization scripts run when PostgreSQL initializes a new data directory. If you reuse an existing database volume, the scripts are not automatically reapplied.

For an existing database, apply schema changes through an appropriate database migration or manual update procedure. Do not delete an existing volume simply to rerun initialization scripts.

## Local Development Without Docker

For development directly on your machine, you need Python 3.12, PostgreSQL with pgvector, and the required environment variables.

Create and activate a virtual environment.

**Windows:**

```powershell
python -m venv .venv
.venv\Scripts\activate
```

**Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Configure the required environment variables and make sure the PostgreSQL database, extension, schema, and tables are available.

Start the development server:

```bash
uvicorn main:app --reload
```

The application entry point and database setup must match the repository's current implementation.

## Testing

The project uses pytest to test API behavior and error handling.

Test coverage includes areas such as:

* Successful API requests
* Request validation
* Authentication failures
* Webhook validation
* Duplicate webhook events
* External API and LLM failures
* RAG retrieval and response handling
* Insufficient-context handling

Run the test suite:

```bash
python -m pytest
```

External services are mocked where appropriate so tests can verify application behavior without depending on live upstream responses.

## Continuous Integration & Deployment

The repository includes a GitHub Actions workflow for testing, building, publishing, and deploying the application.

### Workflow

```text
GitHub Push / Pull Request
          ↓
   Run Automated Tests
          ↓
    PostgreSQL Test Service
          ↓
       Run Pytest
          ↓
Build and Publish Docker Image
     (main branch pushes)
          ↓
     Publish to GHCR
          ↓
    Self-Hosted Runner
          ↓
 Copy Deployment Configuration
          ↓
     Pull Latest Image
          ↓
      Deploy API
          ↓
  Display Service Status
```

### Continuous Integration

The CI job runs on GitHub-hosted infrastructure and initializes a PostgreSQL service for testing before running pytest.

### Image Publishing

After successful tests on a push to `main`, the workflow builds the Docker image and publishes it to GitHub Container Registry.

The current image is:

```text
ghcr.io/ericvilla0896/fastapi-practice:latest
```

The image uses CPU-only PyTorch to avoid unnecessary CUDA dependencies and reduce its size.

### Deployment

The deployment job uses a self-hosted runner registered with the repository or an organization that grants it access.

The workflow copies the tracked Compose configuration and database initialization scripts to the deployment directory, pulls the published image, and recreates the API container.

The current deployment uses GitHub Actions Secrets for:

* `API_KEY`
* `WEBHOOK_SECRET`
* `GEMINI_API_KEY`

These credentials are injected at runtime rather than committed to the repository.

The deployment preserves the existing PostgreSQL service and named volume by targeting the API service for recreation. Database data is not intentionally deleted as part of this deployment process.

The workflow displays the Compose service status. The API health check reports whether the health endpoint responds; displaying service status alone is not equivalent to a deployment assertion that fails the workflow when the service is unhealthy.

### Reproducing the CI/CD Pipeline

The workflow is configured for this repository and deployment environment. Cloning the repository does not grant access to the original owner's GitHub Secrets, self-hosted runner, or write access to the original GHCR package.

To reproduce the pipeline in another repository, a developer must configure their own:

1. GitHub Actions Secrets and repository permissions.
2. GHCR image name and package permissions.
3. Self-hosted runner or another suitable deployment target.
4. Deployment directory and environment configuration.
5. Runner access and security restrictions.

The workflow may need changes to reflect the new repository, image name, runner labels, and deployment target.

These steps are only required to reproduce automated deployment. They are not required for the local Docker Compose quick start.

## Security Considerations

* Never commit real API keys, passwords, or webhook secrets.
* Keep `.env` excluded from Git.
* Use GitHub Actions Secrets for deployment credentials.
* Use separate credentials for development and production.
* Restrict access to self-hosted runners and do not run untrusted workflows on machines that hold deployment credentials.
* Grant workflows only the GitHub permissions they need.
* Treat LLM-generated analyses as untrusted application data and validate structured outputs.
* Do not expose internal service ports unnecessarily in production.
* Use appropriate TLS termination, access controls, monitoring, and secret management when deploying to a publicly accessible environment.

The included deployment is a practical production-oriented learning setup, not a claim that every production requirement—such as high availability, centralized monitoring, automated database migrations, and managed secret rotation—is already implemented.

## What This Project Demonstrates

This project demonstrates hands-on work with:

* REST API development using FastAPI
* Request and response validation using Pydantic
* API-key and webhook authentication
* PostgreSQL CRUD operations
* Webhook processing and idempotency
* Asynchronous external API integration
* Concurrent request processing
* LLM integration and structured outputs
* Database persistence of LLM-generated results
* Vector embeddings and similarity search
* Document chunking and re-indexing
* RAG retrieval, metadata filtering, and reranking
* Pytest, mocking, and monkeypatching
* CI workflows using GitHub Actions
* Docker image optimization
* Docker Compose orchestration and persistent storage
* Container health checks
* GHCR image publishing
* Self-hosted runner configuration
* Automated deployment and environment-variable management
* Debugging integration and deployment failures

## Disclaimer

Job classifications and LLM-generated analyses are automated results and should not be treated as authoritative employment recommendations.