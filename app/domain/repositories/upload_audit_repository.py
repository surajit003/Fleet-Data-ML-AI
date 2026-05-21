from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path

from app.domain.entities.duplicate_row_diagnostic import DuplicateRowDiagnostic
from app.domain.entities.telemetry_upload import TelemetryUpload
from app.domain.entities.upload_audit_detail import UploadAuditDetail
from app.domain.entities.upload_audit_record import UploadAuditRecord
from app.domain.entities.upload_sanity_summary import UploadSanitySummary


class UploadAuditRepository(ABC):
    @abstractmethod
    def save_upload_audit(
        self,
        upload: TelemetryUpload,
        sanity_summary: UploadSanitySummary,
    ) -> None:
        """Persist upload metadata and sanity-check results."""

    @abstractmethod
    def list_recent_uploads(self, limit: int = 10) -> Sequence[UploadAuditRecord]:
        """Return recent upload audit records, newest first."""

    @abstractmethod
    def get_upload_detail(self, stored_filename: str) -> UploadAuditDetail | None:
        """Return a single upload audit detail record when available."""

    @abstractmethod
    def update_upload_status(
        self,
        stored_filename: str,
        status: str,
    ) -> UploadAuditDetail | None:
        """Update upload status and return the refreshed detail when available."""

    @abstractmethod
    def mark_upload_transformed(
        self,
        stored_filename: str,
        processed_path: Path,
        transformed_row_count: int,
        duplicate_row_count: int,
        duplicate_diagnostics: tuple[DuplicateRowDiagnostic, ...],
    ) -> UploadAuditDetail | None:
        """Persist transform output metadata and return the refreshed detail."""
