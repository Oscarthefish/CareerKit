import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..services.profile_service import build_profile_summary, get_banned_phrases_instruction
from ..services.prompt_service import fill_prompt
from ..ai.provider_factory import get_provider

router = APIRouter(prefix="/api/linkedin", tags=["linkedin"])


@router.post("/generate")
async def generate_linkedin(db: Session = Depends(get_db)):
    profile = build_profile_summary(db)
    banned = get_banned_phrases_instruction(db)
    prompt = fill_prompt("linkedin_generation", PROFILE_JSON=json.dumps(profile, indent=2), BANNED_PHRASES=banned)
    provider = get_provider()
    result = await provider.generate_json(prompt)
    return result
