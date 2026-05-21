# FastAPI Cloud Notes

## Local run

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
fastapi dev
```

The `pyproject.toml` file defines:

```toml
[tool.fastapi]
entrypoint = "app.main:app"
```

That allows both local development and cloud deploys to resolve the app without passing `app/main.py`.

## First deploy

Run the first deployment locally so the project is linked to a FastAPI Cloud app:

```bash
fastapi login
fastapi deploy
```

After the first deploy, FastAPI Cloud creates a local `.fastapicloud/` directory. This repository ignores that directory so CI/CD relies on secrets instead of local machine state.

## GitHub setup

Create the repository and push:

```bash
git init
git branch -M main
git add .
git commit -m "Initial FastAPI platform scaffold"
git remote add origin git@github.com:<your-user>/fleet-data-ml-ai.git
git push -u origin main
```

## CI/CD deploy

```bash
uv run fastapi deploy
```

GitHub Actions deployment requires these repository secrets:

- `FASTAPI_CLOUD_TOKEN`
- `FASTAPI_CLOUD_APP_ID`

Create them from FastAPI Cloud:

1. Open your app in FastAPI Cloud.
2. Create a deploy token in `Deploy Tokens`.
3. Copy the app ID from the app header.
4. Add both values in GitHub repository settings under `Secrets and variables` -> `Actions`.

This repository includes:

- `.github/workflows/ci.yml`
- `.github/workflows/deploy-fastapi-cloud.yml`

`ci.yml` runs test, lint, and type checks. `deploy-fastapi-cloud.yml` verifies the app and then deploys on pushes to `main` or by manual trigger.

FastAPI Cloud also has an official helper command that can set this up for you after the first deploy:

```bash
fastapi cloud setup-ci
```

According to the current FastAPI Cloud docs, that command can create a deploy token, set GitHub secrets, and write a workflow file if `gh` is installed and authenticated.

## Production checks

- `GET /`
- `GET /api/v1/health`
