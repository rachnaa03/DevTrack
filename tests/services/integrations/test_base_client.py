import pytest
from typing import Any
from app.services.integrations.base import BasePlatformClient

def test_cannot_instantiate_abstract_base_client() -> None:
    """Verify that attempting to instantiate BasePlatformClient directly raises a TypeError."""
    with pytest.raises(TypeError) as excinfo:
        BasePlatformClient()
    assert "Can't instantiate abstract class" in str(excinfo.value)

class DummyPlatformClient(BasePlatformClient):
    """A minimal concrete implementation of BasePlatformClient for testing purposes."""
    
    @property
    def platform_name(self) -> str:
        return "dummy"

    async def fetch_raw_data(self, username: str) -> dict[str, Any]:
        return {"username": username, "status": "ok"}

@pytest.mark.asyncio
async def test_concrete_dummy_client_contract() -> None:
    """Verify that a subclass implementing the abstract methods executes successfully."""
    client = DummyPlatformClient()
    
    # Assert platform property
    assert client.platform_name == "dummy"
    
    # Assert async method execution
    result = await client.fetch_raw_data("test_user")
    assert result == {"username": "test_user", "status": "ok"}
