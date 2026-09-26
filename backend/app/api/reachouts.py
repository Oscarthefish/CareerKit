from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models.reachout import ReachOut
from ..services.profile_service import build_profile_summary, get_banned_phrases_instruction, get_banned_phrases_list
from ..services.prompt_service import fill_prompt
from ..services.reachout_service import persist_reachout_files
from ..ai.provider_factory import get_provider
from ..exporters import markdown_exporter, docx_exporter, pdf_exporter
from ..storage.file_storage import get_reachout_folder
import json

router = APIRouter(prefix="/api/reachouts", tags=["reachouts"])


def _serialize(r: ReachOut) -> dict:
    return {
        "id": r.id,
        "company_name": r.company_name,
        "website_url": r.website_url,
        "linkedin_url": r.linkedin_url,
        "industry": r.industry,
        "location": r.location,
        "company_size": r.company_size,
        "research_summary": r.research_summary,
        "culture_notes": r.culture_notes,
        "tech_security_notes": r.tech_security_notes,
        "recent_news": r.recent_news,
        "angle": r.angle,
        "contact_name": r.contact_name,
        "contact_role": r.contact_role,
        "contact_email": r.contact_email,
        "status": r.status,
        "date_identified": r.date_identified,
        "date_sent": r.date_sent,
        "follow_up_date": r.follow_up_date,
        "intro_letter": r.intro_letter,
        "cv_notes": r.cv_notes,
        "notes": r.notes,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


@router.get("")
def list_reachouts(db: Session = Depends(get_db)):
    rows = db.query(ReachOut).order_by(ReachOut.id.desc()).all()
    return [
        {
            "id": r.id,
            "company_name": r.company_name,
            "industry": r.industry,
            "location": r.location,
            "status": r.status,
            "date_identified": r.date_identified,
            "date_sent": r.date_sent,
            "follow_up_date": r.follow_up_date,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "has_research": bool(r.research_summary),
            "has_letter": bool(r.intro_letter),
        }
        for r in rows
    ]


class ReachOutCreate(BaseModel):
    company_name: str
    website_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    date_identified: Optional[str] = None


@router.post("")
def create_reachout(body: ReachOutCreate, db: Session = Depends(get_db)):
    folder = get_reachout_folder(body.company_name)
    r = ReachOut(session_folder=str(folder), **body.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return _serialize(r)


@router.get("/{reachout_id}")
def get_reachout(reachout_id: int, db: Session = Depends(get_db)):
    r = db.query(ReachOut).filter(ReachOut.id == reachout_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    return _serialize(r)


class ReachOutUpdate(BaseModel):
    company_name: Optional[str] = None
    website_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    company_size: Optional[str] = None
    research_summary: Optional[str] = None
    culture_notes: Optional[str] = None
    tech_security_notes: Optional[str] = None
    recent_news: Optional[str] = None
    angle: Optional[str] = None
    contact_name: Optional[str] = None
    contact_role: Optional[str] = None
    contact_email: Optional[str] = None
    status: Optional[str] = None
    date_identified: Optional[str] = None
    date_sent: Optional[str] = None
    follow_up_date: Optional[str] = None
    intro_letter: Optional[str] = None
    cv_notes: Optional[str] = None
    notes: Optional[str] = None


@router.put("/{reachout_id}")
def update_reachout(reachout_id: int, body: ReachOutUpdate, db: Session = Depends(get_db)):
    r = db.query(ReachOut).filter(ReachOut.id == reachout_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(r, k, v)
    db.commit()
    db.refresh(r)
    persist_reachout_files(db, reachout_id)
    return _serialize(r)


@router.delete("/{reachout_id}")
def delete_reachout(reachout_id: int, db: Session = Depends(get_db)):
    r = db.query(ReachOut).filter(ReachOut.id == reachout_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(r)
    db.commit()
    return {"ok": True}


@router.post("/{reachout_id}/generate-letter")
async def generate_letter(reachout_id: int, db: Session = Depends(get_db)):
    """Draft an introduction letter with the local AI, from research already on file.

    Ollama has no internet access, so this only works well once research_summary
    (and ideally culture_notes / angle) has already been filled in - either
    manually or by an assistant that did the actual web research.
    """
    r = db.query(ReachOut).filter(ReachOut.id == reachout_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    if not r.research_summary:
        raise HTTPException(status_code=400, detail="Add company research first (research_summary is empty).")

    research_parts = [f"Business overview: {r.research_summary}"]
    if r.culture_notes:
        research_parts.append(f"Culture: {r.culture_notes}")
    if r.tech_security_notes:
        research_parts.append(f"Tech/security posture: {r.tech_security_notes}")
    if r.recent_news:
        research_parts.append(f"Recent news: {r.recent_news}")
    if r.angle:
        research_parts.append(f"Suggested angle: {r.angle}")

    profile = build_profile_summary(db)
    banned = get_banned_phrases_instruction(db)
    prompt = fill_prompt(
        "intro_letter",
        PROFILE_SUMMARY=json.dumps(profile, indent=2),
        COMPANY_NAME=r.company_name,
        CONTACT_NAME=r.contact_name or "",
        COMPANY_RESEARCH="\n".join(research_parts),
        BANNED_PHRASES=banned,
    )
    provider = get_provider()
    letter = await provider.generate(prompt, banned_phrases=get_banned_phrases_list(db))
    r.intro_letter = letter
    if r.status == "identified":
        r.status = "researched"
    db.commit()
    persist_reachout_files(db, reachout_id)
    return {"intro_letter": letter}


@router.get("/{reachout_id}/export/{fmt}")
def export_reachout(reachout_id: int, fmt: str, section: str = "intro-letter", db: Session = Depends(get_db)):
    r = db.query(ReachOut).filter(ReachOut.id == reachout_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Not found")

    content_map = {
        "intro-letter": r.intro_letter,
        "cv-notes": r.cv_notes,
    }
    content = content_map.get(section)
    if not content:
        raise HTTPException(status_code=400, detail=f"No content for section: {section}")

    folder = Path(r.session_folder) / "exports"
    folder.mkdir(parents=True, exist_ok=True)
    safe_section = section.replace("/", "-")

    if fmt == "md":
        path = markdown_exporter.export(content, folder / f"{safe_section}.md")
        return FileResponse(str(path), filename=f"{safe_section}.md", media_type="text/markdown")
    elif fmt == "docx":
        path = docx_exporter.export(content, folder / f"{safe_section}.docx")
        return FileResponse(
            str(path), filename=f"{safe_section}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    elif fmt == "pdf":
        path = pdf_exporter.export(content, folder / f"{safe_section}.pdf")
        return FileResponse(str(path), filename=f"{safe_section}.pdf", media_type="application/pdf")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {fmt}")
