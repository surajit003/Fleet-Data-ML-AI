from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

DuplicateStrategy = Literal["exact_event", "event_with_position"]
StorageBackend = Literal["local", "gcs"]
AnalyticsBackend = Literal["duckdb", "bigquery"]


class Settings(BaseSettings):
    app_name: str = "Fleet Data Platform"
    app_version: str = "0.1.0"
    environment: str = "local"
    api_v1_prefix: str = "/api/v1"
    api_key: str | None = None
    max_upload_size_bytes: int = 2 * 1024 * 1024
    storage_backend: StorageBackend = "local"
    analytics_backend: AnalyticsBackend = "duckdb"
    upload_storage_dir: Path = Path("data/raw/uploads")
    processed_storage_dir: Path = Path("data/processed/telemetry")
    upload_metadata_db_path: Path = Path("data/metadata/uploads.db")
    duplicate_strategy: DuplicateStrategy = "exact_event"
    gcp_project_id: str | None = None
    gcs_raw_bucket_name: str | None = None
    gcs_curated_bucket_name: str | None = None
    bigquery_dataset_id: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
