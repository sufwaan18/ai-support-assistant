# AI Support Assistant

A production-focused AI support application built with Python, FastAPI, Pydantic, and the OpenAI Responses API.

## Current features

- Health-check API endpoint
- Validated support-request endpoint
- AI-generated support-reply endpoint
- Typed environment configuration
- OpenAI service layer
- Automated API and service tests
- Mocked OpenAI tests that avoid network calls and API charges

## Project structure

```text
ai-support-assistant/
├── app/
│   ├── __init__.py
│   ├── ai_service.py
│   ├── config.py
│   ├── main.py
│   └── models.py
├── tests/
│   ├── __init__.py
│   ├── test_ai_service.py
│   ├── test_config.py
│   ├── test_health.py
│   └── test_support.py
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

## Requirements

- Python 3.11 or newer
- An OpenAI API key for real AI requests

## Local setup

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Environment configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Open `.env` and replace the placeholder API key:

```dotenv
ENVIRONMENT=development
OPENAI_API_KEY=replace-with-your-key
OPENAI_MODEL=gpt-5.6-luna
```

Never commit `.env` or expose a real API key in source code, screenshots, logs, or GitHub.

## Run locally

Start the development server:

```bash
python -m uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

## API endpoints

### Health check

```http
GET /health
```

Example response:

```json
{
  "status": "healthy"
}
```

### Submit a support request

```http
POST /support
```

Example request:

```json
{
  "subject": "Cannot reset password",
  "message": "The password reset email never arrives."
}
```

Example response:

```json
{
  "status": "received",
  "subject": "Cannot reset password"
}
```

### Generate an AI support reply

```http
POST /support/reply
```

Example request:

```json
{
  "subject": "Cannot reset password",
  "message": "The password reset email never arrives."
}
```

Example response:

```json
{
  "status": "completed",
  "subject": "Cannot reset password",
  "reply": "Please check your spam folder and request a new reset email."
}
```

This endpoint may use OpenAI API credits when called without a mocked client.

## Run tests

```bash
python -m pytest -v
```

The OpenAI integration is mocked during automated tests, so the test suite does not make real API calls.

## Technology stack

- Python
- FastAPI
- Pydantic
- pytest
- OpenAI Python SDK
- Uvicorn

## Planned additions

- Sentence Transformers
- ChromaDB
- LangChain
- Docker
- GitHub Actions
- AWS deployment