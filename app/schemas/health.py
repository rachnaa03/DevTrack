from pydantic import BaseModel

class HealthResponse(BaseModel):
    """Pydantic schema representing the health status response."""
    status: str
    database: str
