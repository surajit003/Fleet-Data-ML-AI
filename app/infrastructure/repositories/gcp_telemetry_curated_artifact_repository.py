from pathlib import Path

from google.cloud import bigquery
from google.cloud.storage import Client as StorageClient

from app.domain.repositories.telemetry_curated_artifact_repository import (
    TelemetryCuratedArtifactRepository,
)


class GcpTelemetryCuratedArtifactRepository(TelemetryCuratedArtifactRepository):
    def __init__(
        self,
        project_id: str,
        curated_bucket_name: str,
        bigquery_dataset_id: str,
    ) -> None:
        self._project_id = project_id
        self._curated_bucket_name = curated_bucket_name
        self._bigquery_dataset_id = bigquery_dataset_id

    def publish_curated_artifact(
        self,
        stored_filename: str,
        processed_path: Path,
    ) -> None:
        curated_object_name = f"curated/{processed_path.name}"
        storage_client = StorageClient(project=self._project_id)
        bucket = storage_client.bucket(self._curated_bucket_name)
        blob = bucket.blob(curated_object_name)
        blob.upload_from_filename(str(processed_path), content_type="application/parquet")

        table_name = f"curated_{Path(stored_filename).stem}"
        table_id = f"{self._project_id}.{self._bigquery_dataset_id}.{table_name}"
        external_config = bigquery.ExternalConfig("PARQUET")
        external_config.source_uris = [f"gs://{self._curated_bucket_name}/{curated_object_name}"]

        table = bigquery.Table(table_id)
        table.external_data_configuration = external_config

        bigquery_client = bigquery.Client(project=self._project_id)
        bigquery_client.delete_table(table_id, not_found_ok=True)
        bigquery_client.create_table(table)
