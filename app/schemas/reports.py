"""
Pydantic schemas for Weekly Retrospective Reports.
Defines data structures for weekly reports, subscores, report data payloads,
and index/detail response objects adhering to API_SPECIFICATION.md Section 7.
"""

from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class WeeklySubscoresSchema(BaseModel):
    """
    Subscores breakdown for the weekly report.
    Maps to consistency, depth (problem solving), and impact (open source).
    """
    consistency: int = Field(ge=0, description="Consistency subscore (0-300)")
    depth: int = Field(ge=0, description="Depth / Problem-solving subscore (0-350)")
    impact: int = Field(ge=0, description="Impact / Open-source subscore (0-350)")


class WeeklyReportDataSchema(BaseModel):
    """
    Structured payload stored within the weekly_reports JSONB column.
    """
    commits_count: int = Field(ge=0, description="Total GitHub commits during the week")
    problems_solved: int = Field(ge=0, description="Total LeetCode problems solved during the week")
    score_delta: int = Field(description="Change in Developer Score over the week")
    summary: str = Field(description="Deterministic qualitative retrospective text")
    weekly_subscores: WeeklySubscoresSchema = Field(description="Breakdown of subscores at week end")
    weak_topics: list[str] = Field(default_factory=list, description="Identified weak topics for practice")


class WeeklyReportListItemSchema(BaseModel):
    """
    Summary item for weekly reports index listing (API_SPECIFICATION.md Section 7.1).
    """
    id: UUID
    week_start: date
    week_end: date
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WeeklyReportResponseSchema(BaseModel):
    """
    Complete detailed response for a weekly report (API_SPECIFICATION.md Section 7.2).
    """
    id: UUID
    week_start: date
    week_end: date
    report_data: WeeklyReportDataSchema
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WeeklyReportsIndexResponse(BaseModel):
    """
    Listing response containing chronological weekly reports.
    """
    reports: list[WeeklyReportListItemSchema]
