# Fleet Data ML AI

## Project goal

`fleet-data-ml-ai` is a production-style learning project for building a telemetry analytics platform in stages. The long-term direction includes big data processing, local analytics with DuckDB, and a cloud lakehouse path on Google Cloud with Cloud Storage, Iceberg, and BigQuery. The current milestone keeps the scope intentionally small.

## Current milestone

This first milestone sets up a clean FastAPI service skeleton with:

- clean architecture layering across API, application, domain, and infrastructure
- application factory and lifespan hooks
- health and root endpoints
- CSV telemetry upload with a fixed ingestion column schema
- opt-in storage and analytics backends for local DuckDB or Google Cloud
- Iceberg-backed curated storage and analytics adapters behind the same repository ports
- environment-based configuration with Pydantic Settings
- structured JSON logging with `structlog`
- tests, linting, and strict type checking
- Render deployment readiness

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
- `GET /upload`
- `POST /api/v1/uploads/telemetry`
- interactive docs at `GET /docs`

## Planned future milestones

- telemetry data anonymization
- Parquet conversion
- DuckDB local analytics
- cloud analytics on Google Cloud
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
- `render.yaml` for Render infrastructure-as-code deployment settings

## Render deployment

Render can auto-deploy directly from GitHub, so no custom deployment workflow is required.

One-time setup:

1. Create a Render account and connect your GitHub account.
2. In Render, create a new `Web Service` from this repository.
3. Let Render detect `render.yaml`, or enter the same settings manually.
4. Keep `main` as the auto-deploy branch.

Render uses:

```bash
uv sync
uv run fastapi run --host 0.0.0.0 --port $PORT
```

This repository pins Python with `.python-version` and `PYTHON_VERSION=3.14.3` in `render.yaml`.

Useful endpoints after deploy:

- `GET /`
- `GET /api/v1/health`
- `GET /upload`
- `POST /api/v1/uploads/telemetry`

## Telemetry upload contract

The telemetry upload endpoint currently accepts:

- CSV files only
- maximum file size of `2 MB`
- the exact telemetry ingestion header order defined in `app/domain/telemetry_schema.py`

The raw file is stored locally under `data/raw/uploads/` by default, and the application returns the internal domain field mapping used by later processing stages.

### Runtime backends

The repository supports two backend modes selected through environment variables:

- `STORAGE_BACKEND=local` with `ANALYTICS_BACKEND=duckdb`
- `STORAGE_BACKEND=gcs` with `ANALYTICS_BACKEND=bigquery`

The Iceberg layer is configured separately so the repository ports stay stable while the infrastructure changes underneath them. Relevant settings include:

- `ICEBERG_CATALOG_TYPE`
- `ICEBERG_CATALOG_URI`
- `ICEBERG_WAREHOUSE_URI`
- `ICEBERG_NAMESPACE`
- `ICEBERG_TABLE_NAME`
- `ICEBERG_PROJECT_ID`
- `ICEBERG_BUCKET_NAME`

Local development uses a SQL catalog and file-backed warehouse. GCP mode uses the BigLake Iceberg REST catalog with a `gs://` warehouse. The application still keeps the local DuckDB path working as the baseline.

There is also a small HTML upload page at `GET /upload` that posts to the same API endpoint.

## Scope guardrails

This repository does not yet include a general-purpose operational database, Docker setup, or machine learning components. Those will be added in later milestones.
