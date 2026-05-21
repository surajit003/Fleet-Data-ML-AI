import json
import sqlite3
from collections.abc import Sequence
from pathlib import Path

from app.domain.entities.duplicate_row_diagnostic import DuplicateRowDiagnostic
from app.domain.entities.telemetry_upload import TelemetryUpload
from app.domain.entities.upload_audit_detail import UploadAuditDetail
from app.domain.entities.upload_audit_record import UploadAuditRecord
from app.domain.entities.upload_sanity_summary import (
    ColumnIssue,
    PreviewRow,
    UploadSanitySummary,
)
from app.domain.repositories.upload_audit_repository import UploadAuditRepository
from app.domain.upload_status import derive_validation_status

UPLOADS_SCHEMA = """
CREATE TABLE IF NOT EXISTS uploads (
    stored_filename TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'validated',
    original_filename TEXT NOT NULL,
    content_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    row_count INTEGER NOT NULL,
    stored_path TEXT NOT NULL,
    unique_vehicle_count INTEGER NOT NULL,
    warning_count INTEGER NOT NULL,
    warnings_json TEXT NOT NULL,
    preview_columns_json TEXT NOT NULL,
    preview_rows_json TEXT NOT NULL,
    required_value_issues_json TEXT NOT NULL,
    first_recorded_at TEXT,
    last_recorded_at TEXT,
    processed_path TEXT,
    transformed_row_count INTEGER,
    duplicate_row_count INTEGER,
    duplicate_rows_json TEXT NOT NULL DEFAULT '[]',
    transformed_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

def initialize_upload_metadata_database(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute(UPLOADS_SCHEMA)
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(uploads)").fetchall()
        }
        if "status" not in columns:
            connection.execute(
                "ALTER TABLE uploads ADD COLUMN status TEXT NOT NULL DEFAULT 'validated'"
            )
        if "processed_path" not in columns:
            connection.execute("ALTER TABLE uploads ADD COLUMN processed_path TEXT")
        if "transformed_row_count" not in columns:
            connection.execute("ALTER TABLE uploads ADD COLUMN transformed_row_count INTEGER")
        if "duplicate_row_count" not in columns:
            connection.execute("ALTER TABLE uploads ADD COLUMN duplicate_row_count INTEGER")
        if "duplicate_rows_json" not in columns:
            connection.execute(
                "ALTER TABLE uploads ADD COLUMN duplicate_rows_json TEXT NOT NULL DEFAULT '[]'"
            )
        if "transformed_at" not in columns:
            connection.execute("ALTER TABLE uploads ADD COLUMN transformed_at TEXT")
        connection.commit()


class SqliteUploadAuditRepository(UploadAuditRepository):
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        initialize_upload_metadata_database(database_path)

    def save_upload_audit(
        self,
        upload: TelemetryUpload,
        sanity_summary: UploadSanitySummary,
    ) -> None:
        with sqlite3.connect(self._database_path) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO uploads (
                    stored_filename,
                    status,
                    original_filename,
                    content_type,
                    size_bytes,
                    row_count,
                    stored_path,
                    unique_vehicle_count,
                    warning_count,
                    warnings_json,
                    preview_columns_json,
                    preview_rows_json,
                    required_value_issues_json,
                    first_recorded_at,
                    last_recorded_at,
                    processed_path,
                    transformed_row_count,
                    duplicate_row_count,
                    duplicate_rows_json,
                    transformed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    upload.stored_filename,
                    derive_validation_status(sanity_summary),
                    upload.original_filename,
                    upload.content_type,
                    upload.size_bytes,
                    upload.row_count,
                    str(upload.stored_path),
                    sanity_summary.unique_vehicle_count,
                    len(sanity_summary.warnings),
                    json.dumps(list(sanity_summary.warnings)),
                    json.dumps(list(sanity_summary.preview_columns)),
                    json.dumps(
                        [
                            {
                                "row_number": row.row_number,
                                "values": row.values,
                            }
                            for row in sanity_summary.preview_rows
                        ]
                    ),
                    json.dumps(
                        [
                            {
                                "column": issue.column,
                                "issue": issue.issue,
                                "affected_rows": issue.affected_rows,
                            }
                            for issue in sanity_summary.required_value_issues
                        ]
                    ),
                    sanity_summary.first_recorded_at,
                    sanity_summary.last_recorded_at,
                    None,
                    None,
                    None,
                    json.dumps([]),
                    None,
                ),
            )
            connection.commit()

    def list_recent_uploads(self, limit: int = 10) -> Sequence[UploadAuditRecord]:
        with sqlite3.connect(self._database_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT
                    stored_filename,
                    status,
                    original_filename,
                    content_type,
                    size_bytes,
                    row_count,
                    unique_vehicle_count,
                    warning_count,
                    warnings_json,
                    first_recorded_at,
                    last_recorded_at,
                    processed_path,
                    transformed_row_count,
                    duplicate_row_count,
                    duplicate_rows_json,
                    transformed_at,
                    created_at
                FROM uploads
                ORDER BY created_at DESC, stored_filename DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return tuple(
            UploadAuditRecord(
                status=row["status"],
                stored_filename=row["stored_filename"],
                original_filename=row["original_filename"],
                content_type=row["content_type"],
                size_bytes=row["size_bytes"],
                row_count=row["row_count"],
                unique_vehicle_count=row["unique_vehicle_count"],
                warning_count=row["warning_count"],
                warnings=tuple(json.loads(row["warnings_json"])),
                first_recorded_at=row["first_recorded_at"],
                last_recorded_at=row["last_recorded_at"],
                processed_path=row["processed_path"],
                transformed_row_count=row["transformed_row_count"],
                duplicate_row_count=row["duplicate_row_count"],
                transformed_at=row["transformed_at"],
                created_at=row["created_at"],
            )
            for row in rows
        )

    def get_upload_detail(self, stored_filename: str) -> UploadAuditDetail | None:
        with sqlite3.connect(self._database_path) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                SELECT
                    stored_filename,
                    status,
                    original_filename,
                    content_type,
                    size_bytes,
                    row_count,
                    unique_vehicle_count,
                    warning_count,
                    warnings_json,
                    preview_columns_json,
                    preview_rows_json,
                    required_value_issues_json,
                    first_recorded_at,
                    last_recorded_at,
                    processed_path,
                    transformed_row_count,
                    duplicate_row_count,
                    duplicate_rows_json,
                    transformed_at,
                    created_at
                FROM uploads
                WHERE stored_filename = ?
                """,
                (stored_filename,),
            ).fetchone()

        if row is None:
            return None

        upload_record = UploadAuditRecord(
            status=row["status"],
            stored_filename=row["stored_filename"],
            original_filename=row["original_filename"],
            content_type=row["content_type"],
            size_bytes=row["size_bytes"],
            row_count=row["row_count"],
            unique_vehicle_count=row["unique_vehicle_count"],
            warning_count=row["warning_count"],
            warnings=tuple(json.loads(row["warnings_json"])),
            first_recorded_at=row["first_recorded_at"],
            last_recorded_at=row["last_recorded_at"],
            processed_path=row["processed_path"],
            transformed_row_count=row["transformed_row_count"],
            duplicate_row_count=row["duplicate_row_count"],
            transformed_at=row["transformed_at"],
            created_at=row["created_at"],
        )
        sanity_summary = UploadSanitySummary(
            preview_columns=tuple(json.loads(row["preview_columns_json"])),
            preview_rows=tuple(
                PreviewRow(
                    row_number=item["row_number"],
                    values=item["values"],
                )
                for item in json.loads(row["preview_rows_json"])
            ),
            warnings=tuple(json.loads(row["warnings_json"])),
            required_value_issues=tuple(
                ColumnIssue(
                    column=item["column"],
                    issue=item["issue"],
                    affected_rows=item["affected_rows"],
                )
                for item in json.loads(row["required_value_issues_json"])
            ),
            unique_vehicle_count=row["unique_vehicle_count"],
            first_recorded_at=row["first_recorded_at"],
            last_recorded_at=row["last_recorded_at"],
        )
        return UploadAuditDetail(
            upload=upload_record,
            sanity_summary=sanity_summary,
            duplicate_diagnostics=tuple(
                DuplicateRowDiagnostic(
                    row_number=item["row_number"],
                    duplicate_of_row_number=item["duplicate_of_row_number"],
                    duplicate_key=item["duplicate_key"],
                    device_imei=item["device_imei"],
                    vehicle_registration=item["vehicle_registration"],
                    recorded_at=item["recorded_at"],
                    reason=item["reason"],
                )
                for item in json.loads(row["duplicate_rows_json"])
            ),
        )

    def update_upload_status(
        self,
        stored_filename: str,
        status: str,
    ) -> UploadAuditDetail | None:
        with sqlite3.connect(self._database_path) as connection:
            cursor = connection.execute(
                "UPDATE uploads SET status = ? WHERE stored_filename = ?",
                (status, stored_filename),
            )
            connection.commit()

        if cursor.rowcount == 0:
            return None
        return self.get_upload_detail(stored_filename)

    def mark_upload_transformed(
        self,
        stored_filename: str,
        processed_path: Path,
        transformed_row_count: int,
        duplicate_row_count: int,
        duplicate_diagnostics: tuple[DuplicateRowDiagnostic, ...],
    ) -> UploadAuditDetail | None:
        with sqlite3.connect(self._database_path) as connection:
            cursor = connection.execute(
                """
                UPDATE uploads
                SET status = 'transformed',
                    processed_path = ?,
                    transformed_row_count = ?,
                    duplicate_row_count = ?,
                    duplicate_rows_json = ?,
                    transformed_at = CURRENT_TIMESTAMP
                WHERE stored_filename = ?
                """,
                (
                    str(processed_path),
                    transformed_row_count,
                    duplicate_row_count,
                    json.dumps(
                        [
                            {
                                "row_number": item.row_number,
                                "duplicate_of_row_number": item.duplicate_of_row_number,
                                "duplicate_key": item.duplicate_key,
                                "device_imei": item.device_imei,
                                "vehicle_registration": item.vehicle_registration,
                                "recorded_at": item.recorded_at,
                                "reason": item.reason,
                            }
                            for item in duplicate_diagnostics
                        ]
                    ),
                    stored_filename,
                ),
            )
            connection.commit()

        if cursor.rowcount == 0:
            return None
        return self.get_upload_detail(stored_filename)
