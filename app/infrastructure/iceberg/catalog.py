from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pyiceberg.catalog import Catalog, load_catalog
from sqlalchemy.engine import make_url

from app.core.config import Settings

LOCAL_ICEBERG_CATALOG_NAME = "fleet_data_platform_local_iceberg"
GCP_ICEBERG_CATALOG_NAME = "fleet_data_platform_gcp_iceberg"


def resolve_iceberg_namespace(settings: Settings) -> tuple[str, ...]:
    namespace = tuple(
        part.strip()
        for part in settings.iceberg_namespace.split(".")
        if part.strip()
    )
    if not namespace:
        raise ValueError("Iceberg namespace cannot be empty.")
    return namespace


def resolve_iceberg_identifier(settings: Settings) -> tuple[str, ...]:
    return (*resolve_iceberg_namespace(settings), settings.iceberg_table_name)


def resolve_iceberg_warehouse_uri(settings: Settings) -> str:
    if settings.storage_backend == "gcs":
        return settings.iceberg_warehouse_uri
    return settings.iceberg_warehouse_uri


def resolve_iceberg_project_id(settings: Settings) -> str | None:
    return settings.iceberg_project_id or settings.gcp_project_id


def resolve_iceberg_bucket_name(settings: Settings) -> str | None:
    return settings.iceberg_bucket_name or settings.gcs_curated_bucket_name


@lru_cache(maxsize=4)
def load_local_iceberg_catalog(catalog_uri: str, warehouse_uri: str) -> Catalog:
    database_path = make_url(catalog_uri).database
    if database_path is None:
        raise ValueError("SQLite Iceberg catalog URI must include a database path.")
    catalog_path = Path(database_path)
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    return load_catalog(
        LOCAL_ICEBERG_CATALOG_NAME,
        type="sql",
        uri=catalog_uri,
        warehouse=warehouse_uri,
    )


@lru_cache(maxsize=4)
def load_gcp_iceberg_catalog(
    catalog_uri: str,
    warehouse_uri: str,
    project_id: str,
) -> Catalog:
    properties: dict[str, Any] = {
        "type": "rest",
        "uri": catalog_uri,
        "warehouse": warehouse_uri,
        "auth": {"type": "google", "google": {}},
        "header.x-goog-user-project": project_id,
    }
    return load_catalog(
        GCP_ICEBERG_CATALOG_NAME,
        **properties,
    )


def load_iceberg_catalog(settings: Settings) -> Catalog:
    if settings.storage_backend == "gcs":
        if settings.iceberg_catalog_type != "rest":
            raise ValueError("GCP mode requires an Iceberg REST catalog.")
        project_id = resolve_iceberg_project_id(settings)
        if project_id is None:
            raise ValueError("GCP Iceberg access requires a project id.")
        return load_gcp_iceberg_catalog(
            settings.iceberg_catalog_uri,
            resolve_iceberg_warehouse_uri(settings),
            project_id,
        )

    if settings.iceberg_catalog_type != "sql":
        raise ValueError("Local mode requires an Iceberg SQL catalog.")
    return load_local_iceberg_catalog(
        settings.iceberg_catalog_uri,
        resolve_iceberg_warehouse_uri(settings),
    )
