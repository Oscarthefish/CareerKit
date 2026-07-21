from fastapi import APIRouter
from pydantic import BaseModel
from ..core.config import load_settings, save_settings
from ..ai.provider_factory import reset_provider

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    ollama_url: str | None = None
    ollama_model: str | None = None


@router.get("")
def get_settings():
    return load_settings()


@router.put("")
def update_settings(body: SettingsUpdate):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    save_settings(updates)
    reset_provider()
    return load_settings()
