from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from pyiceberg.expressions import BooleanExpression, EqualTo

from app.core.config import Settings
from app.domain.repositories.telemetry_curated_artifact_repository import (
    TelemetryCuratedArtifactRepository,
)
from app.domain.repositories.upload_audit_repository import UploadAuditRepository
from app.infrastructure.iceberg.bootstrap import bootstrap_iceberg_table
from app.infrastructure.iceberg.catalog import load_iceberg_catalog, resolve_iceberg_identifier


class LocalTelemetryCuratedArtifactRepository(TelemetryCuratedArtifactRepository):
    def __init__(
        self,
        settings: Settings,
        upload_audit_repository: UploadAuditRepository | None = None,
    ) -> None:
        self._settings = settings
        self._upload_audit_repository = upload_audit_repository

    def publish_curated_artifact(
        self,
        stored_filename: str,
        processed_path: Path,
    ) -> None:
        if self._was_already_ingested(stored_filename):
            return

        bootstrap_iceberg_table(self._settings)
        table = load_iceberg_catalog(self._settings).load_table(
            resolve_iceberg_identifier(self._settings)
        )

        if table.scan(row_filter=self._stored_filename_expression(stored_filename)).count() > 0:
            return

        curated_table = pq.read_table(processed_path)  # type: ignore[no-untyped-call]
        curated_table = self._add_stored_filename_column(curated_table, stored_filename)
        table.append(curated_table)

    def _was_already_ingested(self, stored_filename: str) -> bool:
        if self._upload_audit_repository is None:
            return False
        detail = self._upload_audit_repository.get_upload_detail(stored_filename)
        return bool(
            detail
            and detail.upload.transformed_row_count is not None
            and detail.upload.processed_path
        )

    def _stored_filename_expression(self, stored_filename: str) -> BooleanExpression:
        return EqualTo("stored_filename", value=stored_filename)  # type: ignore[misc, arg-type]

    def _add_stored_filename_column(
        self,
        curated_table: pa.Table,
        stored_filename: str,
    ) -> pa.Table:
        stored_filename_values = pa.array(
            [stored_filename] * curated_table.num_rows,
            type=pa.string(),
        )
        curated_table = curated_table.append_column("stored_filename", stored_filename_values)
        ordered_columns = [
            "stored_filename",
            *[
                name
                for name in curated_table.column_names
                if name != "stored_filename"
            ],
        ]
        return curated_table.select(ordered_columns)
