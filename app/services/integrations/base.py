from abc import ABC, abstractmethod
from typing import Any

class BasePlatformClient(ABC):
    """
    Abstract base class defining the contract for all external developer platform clients.
    All platform integration clients (e.g. GitHubClient, LeetCodeClient) must inherit
    from this and implement the abstract methods to ensure consistency.
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """
        Return the unique name of the platform (e.g., 'github', 'leetcode').
        """
        pass

    @abstractmethod
    async def fetch_raw_data(self, username: str) -> dict[str, Any]:
        """
        Asynchronously fetch raw JSON/dictionary data from the third-party platform API for a given username.

        Args:
            username: The platform-specific username handle to fetch data for.

        Returns:
            A dictionary containing the raw, unparsed JSON payload fetched from the platform.
        """
        pass
