from fastapi import APIRouter
from ..ai.provider_factory import get_provider

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/health")
async def ai_health():
    provider = get_provider()
    return await provider.health_check()
