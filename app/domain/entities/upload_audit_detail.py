from dataclasses import dataclass

from app.domain.entities.duplicate_row_diagnostic import DuplicateRowDiagnostic
from app.domain.entities.upload_audit_record import UploadAuditRecord
from app.domain.entities.upload_sanity_summary import UploadSanitySummary


@dataclass(frozen=True, slots=True)
class UploadAuditDetail:
    upload: UploadAuditRecord
    sanity_summary: UploadSanitySummary
    duplicate_diagnostics: tuple[DuplicateRowDiagnostic, ...] = ()
