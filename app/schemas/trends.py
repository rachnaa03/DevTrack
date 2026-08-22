from datetime import date
from typing import Literal
from uuid import UUID
from pydantic import BaseModel

class MetricTrendResult(BaseModel):
    """Result model representing the trend direction and absolute difference for a specific metric."""
    metric_name: str
    latest_value: int | None = None
    previous_value: int | None = None
    absolute_change: int | None = None
    direction: Literal["up", "down", "unchanged", "insufficient_data"]
    latest_date: date | None = None
    previous_date: date | None = None

class PlatformTrendSummary(BaseModel):
    """Aggregated trend summary results for a specific platform."""
    platform: str
    user_id: UUID
    trends: dict[str, MetricTrendResult]
