import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.main import app
from app.core.database import get_db

client = TestClient(app)

def test_health_check_success() -> None:
    """Test health check returns HTTP 200 OK when database is responsive."""
    mock_db = AsyncMock()
    mock_db.execute.return_value = MagicMock()
    
    async def override_get_db():
        yield mock_db
        
    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "healthy"
    finally:
        app.dependency_overrides.clear()

def test_health_check_database_failure() -> None:
    """Test health check returns HTTP 503 Service Unavailable when database is unresponsive."""
    mock_db = AsyncMock()
    mock_db.execute.side_effect = SQLAlchemyError("Database connection failed")
    
    async def override_get_db():
        yield mock_db
        
    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.get("/api/v1/health")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "unavailable"
        # Ensure raw exceptions and sensitive database details are not leaked in the body
        assert "SQLAlchemyError" not in response.text
        assert "Database connection failed" not in response.text
    finally:
        app.dependency_overrides.clear()
