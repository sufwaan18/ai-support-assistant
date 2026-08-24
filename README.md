# Tytus.ai - AI Support Assistant

I built this project to learn how a useful AI support tool works beyond a basic chat prompt. It takes a customer's question, finds similar complaints from the Consumer Financial Protection Bureau (CFPB), and uses that information to draft a response.

The answer includes the complaint records that were used as sources. The app also checks the citations before returning the answer, so the model cannot cite a complaint that was not found during the search.

The live browser version is called Tytus.ai and is available at
`https://sufwaan.shop`.

## What it can do

- Answer financial support questions through a simple chat page
- Search CFPB complaint data for useful context
- Show the complaint IDs and details used for an answer
- Check that citations match the retrieved records
- Accept voice input in supported browsers
- Protect the demo with short-lived access codes and sessions
- Limit AI requests to reduce misuse and unexpected API costs
- Measure retrieval and answer quality with local evaluation scripts
- Run locally, with Docker, or on an AWS EC2 instance

## How it works

When a user sends a question, Sentence Transformers turns the text into an embedding. ChromaDB compares that embedding with the saved complaint records and returns the closest matches. Those records are added to the prompt sent to OpenAI.

The model is told to use only the supplied records and to avoid making legal or financial claims. Before the API sends the response back, it checks that every complaint ID in the answer belongs to one of the retrieved records.

## Main tools

- Python and FastAPI for the API
- Pydantic for settings and request validation
- OpenAI Responses API for drafting replies
- Sentence Transformers for embeddings
- ChromaDB for local vector search
- HTML, CSS, and JavaScript for the browser interface
- pytest for testing
- Docker and Docker Compose for containers
- GitHub Actions for tests and deployment
- AWS EC2, ECR, S3, Systems Manager, IAM, and Parameter Store for the demo deployment

## Run the project locally

You need Python 3.11 or newer and an OpenAI API key.

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the packages:

```bash
python -m pip install -r requirements.txt
```

Copy the example settings file:

```bash
cp .env.example .env
```

Add your own values to `.env`:

```dotenv
APP_API_KEY=replace-with-a-long-random-value
OPENAI_API_KEY=replace-with-your-key
OPENAI_MODEL=gpt-5.6-luna
RAG_DATABASE_DIRECTORY=data/chroma
AI_RATE_LIMIT_REQUESTS=10
AI_RATE_LIMIT_WINDOW_SECONDS=60
```

Do not commit the `.env` file. It contains values that should stay private.

## Prepare the complaint data

Download and clean up to 5,000 CFPB complaints:

```bash
python -m app.ingestion.cli
```

Build the local ChromaDB index:

```bash
python -m app.index_cli
```

The first indexing run may take longer because the embedding model has to be downloaded.

## Start the app

Run the development server:

```bash
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` for the chat page or `http://127.0.0.1:8000/docs` for the API documentation.

The chat page uses a six-digit access code. Open `http://127.0.0.1:8000/admin`, enter the `APP_API_KEY` from your `.env` file, and generate a code. Each code can be used once and expires after five minutes.

## Run with Docker

After creating `.env`, run:

```bash
docker compose up --build
```

The app will be available at `http://127.0.0.1:8000`.

## API routes

The main routes are:

- `GET /health` checks whether the API is running
- `POST /access/codes` creates a demo access code
- `POST /access/verify` exchanges a code for a browser session
- `POST /access/logout` ends the current session
- `POST /support/reply` creates a regular AI reply
- `POST /rag/support` creates a reply based on CFPB complaint data

The reply routes can use OpenAI credits. They require a valid browser session and are rate limited.

## Check retrieval quality

This command tests whether the search returns the expected type of complaint. The report includes recall at K and mean reciprocal rank.

```bash
python -m app.evaluate_cli
```

The result is saved to `data/processed/retrieval_evaluation.json`.

## Check answer quality

This evaluation checks groundedness, citations, relevance, and safety. It uses saved examples and does not call OpenAI.

```bash
python -m app.answer_evaluate_cli
```

The result is saved to `data/processed/answer_quality_evaluation.json`.

## Run the tests

```bash
python -m pytest -v
```

OpenAI calls are mocked in the test suite, so running the tests does not use API credits.

## Live AWS deployment

The live version runs in a Docker container on EC2. Caddy handles HTTPS and sends requests to the FastAPI container. The application image is stored in ECR, and the ChromaDB snapshot is stored in a private S3 bucket. Secrets are read from Parameter Store instead of being saved in the repository or container image.

Deployment is started manually through GitHub Actions. It uses GitHub OIDC to connect to AWS, deploys through Systems Manager without SSH, checks the health route, and restores the previous image if the new version does not start correctly.

More setup and operating notes are in [the AWS deployment guide](docs/aws-deployment.md).

## Current limits

This is a portfolio project and not a replacement for a real customer support team. CFPB complaints are submitted by consumers and are not verified facts. The generated replies are for general information only and should not be treated as financial or legal advice.

The application has HTTPS and a custom domain. Longer-term monitoring and infrastructure as code would be useful additions before treating it as a larger public service.
