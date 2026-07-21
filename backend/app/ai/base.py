from abc import ABC, abstractmethod
from typing import Optional


class AIProvider(ABC):

    @abstractmethod
    async def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """Generate text from a prompt."""

    @abstractmethod
    async def generate_json(self, prompt: str, system: Optional[str] = None) -> dict:
        """Generate and parse a JSON response."""

    @abstractmethod
    async def health_check(self) -> dict:
        """Return health status of the provider."""
