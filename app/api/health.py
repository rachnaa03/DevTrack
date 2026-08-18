import logging
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.health import HealthResponse

logger = logging.getLogger("devtrack.api")

router = APIRouter()

@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check(response: Response, db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Verify application liveness and check PostgreSQL database readiness."""
    try:
        # Perform a lightweight query to check connectivity
        await db.execute(text("SELECT 1"))
        return HealthResponse(status="healthy", database="healthy")
    except Exception as exc:
        logger.exception("Database connectivity check failed during health check")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="unhealthy", database="unavailable")
