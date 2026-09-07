import uuid
from datetime import date, datetime, timezone
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.user import User
from app.models.weekly_report import WeeklyReport


def test_weekly_report_model_attributes() -> None:
    """Verify that WeeklyReport database model attributes and table constraints are defined correctly."""
    assert WeeklyReport.__tablename__ == "weekly_reports"

    # Verify expected columns are present
    assert hasattr(WeeklyReport, "id")
    assert hasattr(WeeklyReport, "user_id")
    assert hasattr(WeeklyReport, "week_start")
    assert hasattr(WeeklyReport, "week_end")
    assert hasattr(WeeklyReport, "report_data")
    assert hasattr(WeeklyReport, "created_at")

    # Verify column specifications
    table = WeeklyReport.__table__
    assert table.c.id.primary_key is True
    assert table.c.user_id.nullable is False
    assert table.c.week_start.nullable is False
    assert table.c.week_end.nullable is False
    assert table.c.report_data.nullable is False
    assert table.c.created_at.nullable is False

    # Verify unique constraint on (user_id, week_start)
    unique_constraints = [
        c for c in table.constraints if getattr(c, "name", None) == "uq_weekly_reports_user_week_start"
    ]
    assert len(unique_constraints) == 1
    uc = unique_constraints[0]
    col_names = [col.name for col in uc.columns]
    assert "user_id" in col_names
    assert "week_start" in col_names


def test_user_weekly_report_relationship() -> None:
    """Verify SQLAlchemy 1:N relationship configuration between User and WeeklyReport."""
    assert hasattr(User, "weekly_reports")
    assert hasattr(WeeklyReport, "user")

    user_rel = User.weekly_reports.property
    assert user_rel.uselist is True
    assert user_rel.back_populates == "user"
    assert "delete" in user_rel.cascade
    assert "delete-orphan" in user_rel.cascade

    report_rel = WeeklyReport.user.property
    assert report_rel.uselist is False
    assert report_rel.back_populates == "weekly_reports"


def test_weekly_report_instantiation() -> None:
    """Verify WeeklyReport instance creation with expected fields."""
    user_id = uuid.uuid4()
    report_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    start = date(2026, 8, 3)
    end = date(2026, 8, 9)
    sample_data = {
        "commits_count": 25,
        "problems_solved": 8,
        "score_delta": 15,
        "summary": "Solid progress in Dynamic Programming.",
        "weekly_subscores": {
            "consistency": 180,
            "depth": 270,
            "impact": 270,
        },
    }

    report = WeeklyReport(
        id=report_id,
        user_id=user_id,
        week_start=start,
        week_end=end,
        report_data=sample_data,
        created_at=now,
    )

    assert report.id == report_id
    assert report.user_id == user_id
    assert report.week_start == start
    assert report.week_end == end
    assert report.report_data["commits_count"] == 25
    assert report.report_data["problems_solved"] == 8
    assert report.report_data["score_delta"] == 15
    assert report.created_at == now
