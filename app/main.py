from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger

SettingsDep = Annotated[Settings, Depends(get_settings)]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logger = get_logger().bind(
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )
    logger.info("application_startup")
    app.state.settings = settings
    yield
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/", tags=["meta"])
    def read_root(app_settings: SettingsDep) -> dict[str, str]:
        return {
            "service": app_settings.app_name,
            "version": app_settings.app_version,
            "docs": "/docs",
            "health": f"{app_settings.api_v1_prefix}/health",
        }

    @app.get("/upload", response_class=HTMLResponse, tags=["ui"])
    def read_upload_page(app_settings: SettingsDep) -> str:
        return f"""
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{app_settings.app_name} Upload</title>
    <style>
      :root {{
        color-scheme: light;
        --bg: #f4efe4;
        --panel: #fffaf0;
        --ink: #1f2a37;
        --muted: #52606d;
        --accent: #0f766e;
        --accent-dark: #115e59;
        --border: #d9cdb8;
        --error: #b42318;
      }}
      * {{
        box-sizing: border-box;
      }}
      body {{
        margin: 0;
        min-height: 100vh;
        font-family: Georgia, "Times New Roman", serif;
        background:
          radial-gradient(circle at top left, rgba(15, 118, 110, 0.14), transparent 30%),
          linear-gradient(180deg, #f6f1e8 0%, var(--bg) 100%);
        color: var(--ink);
        display: grid;
        place-items: center;
        padding: 24px;
      }}
      main {{
        width: min(720px, 100%);
        background: rgba(255, 250, 240, 0.94);
        border: 1px solid var(--border);
        border-radius: 24px;
        padding: 32px;
        box-shadow: 0 24px 48px rgba(31, 42, 55, 0.08);
      }}
      h1 {{
        margin: 0 0 12px;
        font-size: clamp(2rem, 5vw, 3.25rem);
        line-height: 1;
      }}
      p {{
        margin: 0 0 16px;
        color: var(--muted);
        font-size: 1rem;
        line-height: 1.6;
      }}
      form {{
        margin-top: 24px;
        display: grid;
        gap: 16px;
      }}
      .panel {{
        border: 1px dashed var(--border);
        border-radius: 18px;
        padding: 20px;
        background: rgba(255, 255, 255, 0.65);
      }}
      input[type="file"] {{
        width: 100%;
      }}
      button {{
        width: fit-content;
        border: 0;
        border-radius: 999px;
        background: var(--accent);
        color: white;
        padding: 12px 18px;
        font: inherit;
        cursor: pointer;
      }}
      button:hover {{
        background: var(--accent-dark);
      }}
      pre {{
        margin: 0;
        padding: 16px;
        border-radius: 16px;
        background: #12212b;
        color: #d7f9f5;
        overflow-x: auto;
        white-space: pre-wrap;
        word-break: break-word;
      }}
      .status {{
        font-weight: 700;
      }}
      .error {{
        color: var(--error);
      }}
    </style>
  </head>
  <body>
    <main>
      <p class="status">Telemetry Intake</p>
      <h1>Upload Trackzee CSV</h1>
      <p>
        Upload a Trackzee export as CSV. The file must be 2 MB or smaller and match the
        fixed column order used by the current ingestion contract.
      </p>
      <form id="upload-form">
        <div class="panel">
          <input id="telemetry-file" name="file" type="file" accept=".csv,text/csv" required />
        </div>
        <button type="submit">Upload telemetry</button>
      </form>
      <p id="message"></p>
      <pre id="result" hidden></pre>
    </main>
    <script>
      const form = document.getElementById("upload-form");
      const input = document.getElementById("telemetry-file");
      const message = document.getElementById("message");
      const result = document.getElementById("result");

      form.addEventListener("submit", async (event) => {{
        event.preventDefault();
        const file = input.files?.[0];
        if (!file) {{
          message.textContent = "Choose a CSV file first.";
          message.className = "error";
          result.hidden = true;
          return;
        }}

        const formData = new FormData();
        formData.append("file", file);

        message.textContent = "Uploading...";
        message.className = "status";
        result.hidden = true;

        const response = await fetch("{app_settings.api_v1_prefix}/uploads/telemetry", {{
          method: "POST",
          body: formData,
        }});
        const data = await response.json();

        if (!response.ok) {{
          message.textContent = data.detail ?? "Upload failed.";
          message.className = "error";
          result.hidden = true;
          return;
        }}

        message.textContent = "Upload completed.";
        message.className = "status";
        result.textContent = JSON.stringify(data, null, 2);
        result.hidden = false;
      }});
    </script>
  </body>
</html>
"""

    return app


app = create_app()
