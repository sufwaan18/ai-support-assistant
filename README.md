# AI Support Assistant

A production-focused AI support application built with Python and FastAPI.

## Current features

- Health-check API endpoint
- Validated support-request endpoint
- Automated API tests

## Run locally

Activate the virtual environment:

```bash
source .venv/bin/activate

## Run tests

```bash
python -m pytest -v
```

## Environment configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Replace placeholder values in `.env` with local secrets. Never commit `.env`.