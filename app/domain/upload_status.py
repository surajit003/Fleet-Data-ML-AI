from app.domain.entities.upload_sanity_summary import UploadSanitySummary

STATUS_VALIDATED = "validated"
STATUS_VALIDATED_WITH_WARNINGS = "validated_with_warnings"
STATUS_READY_FOR_TRANSFORM = "ready_for_transform"
STATUS_TRANSFORMED = "transformed"


def derive_validation_status(sanity_summary: UploadSanitySummary) -> str:
    if sanity_summary.required_value_issues or sanity_summary.warnings:
        return STATUS_VALIDATED_WITH_WARNINGS
    return STATUS_VALIDATED


def can_prepare_for_transform(status: str) -> bool:
    return status in {STATUS_VALIDATED, STATUS_VALIDATED_WITH_WARNINGS}


def can_run_transform(status: str) -> bool:
    return status == STATUS_READY_FOR_TRANSFORM
