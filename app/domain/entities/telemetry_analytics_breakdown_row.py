from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TelemetryAnalyticsBreakdownRow:
    label: str
    count: int
