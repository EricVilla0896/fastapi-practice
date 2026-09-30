# FastAPI LLM Job Analyzer

A FastAPI backend project that integrates a remote jobs API, asynchronous LLM processing, structured Pydantic validation, PostgreSQL persistence, authentication, and webhook processing.

The project retrieves remote job listings, analyzes them against a target entry-level/junior technical profile using Gemini, and stores the structured results in PostgreSQL.

## Features

* FastAPI REST API
* Pydantic request and response validation
* PostgreSQL integration with psycopg
* API-key authentication
* Webhook-secret authentication
* Webhook event validation and duplicate-event protection
* Asynchronous external API requests with `httpx`
* Himalayas Jobs API integration
* Concurrent LLM processing with `asyncio.gather()`
* Async Google Gemini API integration
* Structured LLM output validated with Pydantic
* PostgreSQL persistence of analyzed jobs
* Request timeouts and external API error handling
* Automatic OpenAPI/Swagger documentation

## Architecture

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

## Technologies

* Python
* FastAPI
* Pydantic
* PostgreSQL
* psycopg
* httpx
* Google Gemini API
* asyncio
* uvicorn
* python-dotenv

## API Endpoints

### Job Analysis

#### `GET /jobs/analyze`

Searches the Himalayas Jobs API, analyzes up to four returned jobs concurrently with Gemini, stores the results in PostgreSQL, and returns the analyses.

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

The project uses PostgreSQL with the `api_practice_schema` schema.

### Tables

* `applications` — stores job applications
* `webhook_events` — tracks processed webhook event IDs
* `analyzed_jobs` — stores job listings and their LLM-generated analysis

The `webhook_events` table is used to prevent duplicate webhook processing.

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

## Running the API

Start the development server:

```bash
uvicorn app:app --reload
```

FastAPI provides interactive API documentation at:

```text
/docs
```

The OpenAPI schema is available at:

```text
/openapi.json
```

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

External service failures are converted into appropriate HTTP responses instead of exposing raw upstream responses.

## What This Project Demonstrates

This project demonstrates practical backend integration involving:

* Building REST APIs with FastAPI
* Dependency-based authentication
* Request validation with Pydantic
* PostgreSQL CRUD operations
* Webhook processing and idempotency
* Consuming external REST APIs asynchronously
* Concurrent asynchronous processing
* Integrating an LLM into an application workflow
* Generating structured LLM output
* Validating LLM responses with Pydantic
* Persisting LLM-generated results
* Handling external-service failures and timeouts

## Disclaimer

Job classifications are generated by an LLM and should be treated as automated analysis rather than authoritative employment recommendations.