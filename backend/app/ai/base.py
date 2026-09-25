from abc import ABC, abstractmethod
from typing import Optional


class AIProvider(ABC):

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        banned_phrases: Optional[list[str]] = None,
        flag_years_experience: bool = False,
        in_progress_certs: Optional[list[str]] = None,
        former_employers: Optional[list[str]] = None,
    ) -> str:
        """Generate text from a prompt. If banned_phrases is given, the
        implementation should check the result for violations and attempt at
        least one corrective retry rather than relying solely on the prompt
        instruction — small local models routinely ignore negative-constraint
        wording in free-form prose. If flag_years_experience is True, a fixed
        "X years of experience" claim should trigger the same corrective retry,
        since the profile asks for anchor dates (e.g. "since 2014") instead.
        If in_progress_certs is given, a claim that states one of these
        certifications as already held should trigger the same retry. If
        former_employers is given, describing one of them as the candidate's
        current role should trigger the same retry."""

    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        required_keys: Optional[list[str]] = None,
    ) -> dict:
        """Generate and parse a JSON response.

        If ``required_keys`` is given, the response must contain at least one of
        them or the provider retries once and then raises ``ValueError``.
        """

    @abstractmethod
    async def health_check(self) -> dict:
        """Return health status of the provider."""
