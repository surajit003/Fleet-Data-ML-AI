# Fleet Data ML AI

## Project goal

`fleet-data-ml-ai` is a production-style learning project for building a telemetry analytics platform in stages. The long-term direction includes big data processing, local analytics with DuckDB, AWS Athena querying, and MLOps workflows, but the current milestone keeps the scope intentionally small.

## Current milestone

This first milestone sets up a clean FastAPI service skeleton with:

- clean architecture layering across API, application, domain, and infrastructure
- application factory and lifespan hooks
- health and root endpoints
- environment-based configuration with Pydantic Settings
- structured JSON logging with `structlog`
- tests, linting, and strict type checking
- FastAPI Cloud deployment readiness

## Tech stack

- Python 3.14
- FastAPI
- Pydantic Settings
- structlog
- pytest
- Ruff
- MyPy

## Local setup

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Copy `.env.example` to `.env` if you want to override defaults locally.

## Run tests

```bash
pytest
ruff check .
mypy app tests
```

## Run the API locally

```bash
fastapi dev app/main.py
```

Because `pyproject.toml` now defines the FastAPI entrypoint, you can also run:

```bash
fastapi dev
```

The service exposes:

- `GET /`
- `GET /api/v1/health`
- interactive docs at `GET /docs`

## Planned future milestones

- file upload
- telemetry data anonymization
- Parquet conversion
- DuckDB local analytics
- S3 data lake
- AWS Athena analytics
- MLOps

## GitHub workflow

Initialize git, create the first commit, and push to GitHub:

```bash
git init
git branch -M main
git add .
git commit -m "Initial FastAPI platform scaffold"
git remote add origin git@github.com:<your-user>/fleet-data-ml-ai.git
git push -u origin main
```

This project includes:

- `.github/workflows/ci.yml` for tests, Ruff, and MyPy on push and pull request
- `.github/workflows/deploy-fastapi-cloud.yml` for FastAPI Cloud deployment on `main` and manual dispatch

## FastAPI Cloud CI/CD

One-time bootstrap:

1. Run a first local deploy with `fastapi deploy` to create and link the FastAPI Cloud app.
2. In FastAPI Cloud, create a deploy token for the app.
3. In GitHub repository secrets, add `FASTAPI_CLOUD_TOKEN` and `FASTAPI_CLOUD_APP_ID`.
4. Push to `main` or trigger the deploy workflow manually.

FastAPI Cloud deploys with:

```bash
uv run fastapi deploy
```

The workflow uses the official token-based CI/CD pattern for FastAPI Cloud.

## Scope guardrails

This repository does not yet include a database, Docker setup, file ingestion pipeline, AWS integrations, DuckDB analytics, Athena queries, or machine learning components. Those will be added in later milestones.
