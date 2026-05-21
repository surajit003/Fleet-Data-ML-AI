from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DuplicateRowDiagnostic:
    row_number: int
    duplicate_of_row_number: int
    duplicate_key: str
    device_imei: str
    vehicle_registration: str
    recorded_at: str
    reason: str
