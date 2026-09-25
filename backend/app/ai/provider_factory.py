from ..core.config import get_setting
from .ollama_provider import OllamaProvider
from .base import AIProvider

_provider: AIProvider | None = None


def get_provider() -> AIProvider:
    global _provider
    if _provider is None:
        _provider = OllamaProvider(
            base_url=get_setting("ollama_url", "http://localhost:11434"),
            model=get_setting("ollama_model", "llama3.1"),
            num_ctx=int(get_setting("ollama_num_ctx", 16384)),
        )
    return _provider


def reset_provider():
    """Call this after updating settings so the provider is rebuilt."""
    global _provider
    _provider = None
