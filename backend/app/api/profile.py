import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models.profile import (
    Profile, WorkExperience, Skill, Certification,
    Achievement, Project, EvidenceItem, StylePreferences
)
from ..services.profile_service import get_or_create_profile, get_or_create_style, get_banned_phrases_instruction
from ..ai.provider_factory import get_provider
from ..services.prompt_service import fill_prompt

router = APIRouter(prefix="/api/profile", tags=["profile"])


# ---------- Profile ----------

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    website: Optional[str] = None
    professional_summary: Optional[str] = None
    target_roles: Optional[List[str]] = None
    nz_work_rights: Optional[str] = None
    setup_complete: Optional[bool] = None


@router.get("")
def get_profile(db: Session = Depends(get_db)):
    p = get_or_create_profile(db)
    return {
        **{c.name: getattr(p, c.name) for c in Profile.__table__.columns},
        "target_roles": json.loads(p.target_roles or "[]"),
    }


@router.put("")
def update_profile(body: ProfileUpdate, db: Session = Depends(get_db)):
    p = get_or_create_profile(db)
    for key, value in body.model_dump(exclude_none=True).items():
        if key == "target_roles":
            setattr(p, key, json.dumps(value))
        else:
            setattr(p, key, value)
    db.commit()
    db.refresh(p)
    return {
        **{c.name: getattr(p, c.name) for c in Profile.__table__.columns},
        "target_roles": json.loads(p.target_roles or "[]"),
    }


# ---------- Work Experience ----------

class WorkExpCreate(BaseModel):
    company: str
    role: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    location: Optional[str] = None
    description: Optional[str] = None
    key_responsibilities: List[str] = []
    technologies: List[str] = []
    order_index: int = 0


@router.get("/work-experience")
def list_work_experience(db: Session = Depends(get_db)):
    rows = db.query(WorkExperience).order_by(WorkExperience.order_index, WorkExperience.id.desc()).all()
    return [_serialize_work_exp(r) for r in rows]


@router.post("/work-experience")
def create_work_experience(body: WorkExpCreate, db: Session = Depends(get_db)):
    row = WorkExperience(
        **{k: (json.dumps(v) if isinstance(v, list) else v) for k, v in body.model_dump().items()}
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_work_exp(row)


@router.put("/work-experience/{item_id}")
def update_work_experience(item_id: int, body: WorkExpCreate, db: Session = Depends(get_db)):
    row = db.query(WorkExperience).filter(WorkExperience.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in body.model_dump().items():
        setattr(row, k, json.dumps(v) if isinstance(v, list) else v)
    db.commit()
    db.refresh(row)
    return _serialize_work_exp(row)


@router.delete("/work-experience/{item_id}")
def delete_work_experience(item_id: int, db: Session = Depends(get_db)):
    row = db.query(WorkExperience).filter(WorkExperience.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


def _serialize_work_exp(row: WorkExperience) -> dict:
    return {
        "id": row.id,
        "company": row.company,
        "role": row.role,
        "start_date": row.start_date,
        "end_date": row.end_date,
        "is_current": row.is_current,
        "location": row.location,
        "description": row.description,
        "key_responsibilities": json.loads(row.key_responsibilities or "[]"),
        "technologies": json.loads(row.technologies or "[]"),
        "order_index": row.order_index,
    }


# ---------- Skills ----------

class SkillCreate(BaseModel):
    name: str
    category: Optional[str] = None
    proficiency: Optional[str] = None
    years_experience: Optional[float] = None
    confidence: str = "confirmed"
    notes: Optional[str] = None


@router.get("/skills")
def list_skills(db: Session = Depends(get_db)):
    return [
        {c.name: getattr(s, c.name) for c in Skill.__table__.columns}
        for s in db.query(Skill).all()
    ]


@router.post("/skills")
def create_skill(body: SkillCreate, db: Session = Depends(get_db)):
    row = Skill(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return {c.name: getattr(row, c.name) for c in Skill.__table__.columns}


@router.put("/skills/{item_id}")
def update_skill(item_id: int, body: SkillCreate, db: Session = Depends(get_db)):
    row = db.query(Skill).filter(Skill.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return {c.name: getattr(row, c.name) for c in Skill.__table__.columns}


@router.delete("/skills/{item_id}")
def delete_skill(item_id: int, db: Session = Depends(get_db)):
    row = db.query(Skill).filter(Skill.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


# ---------- Certifications ----------

class CertCreate(BaseModel):
    name: str
    issuer: Optional[str] = None
    date_obtained: Optional[str] = None
    expiry_date: Optional[str] = None
    credential_id: Optional[str] = None
    url: Optional[str] = None
    in_progress: bool = False


@router.get("/certifications")
def list_certifications(db: Session = Depends(get_db)):
    return [
        {c.name: getattr(cert, c.name) for c in Certification.__table__.columns}
        for cert in db.query(Certification).all()
    ]


@router.post("/certifications")
def create_certification(body: CertCreate, db: Session = Depends(get_db)):
    row = Certification(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return {c.name: getattr(row, c.name) for c in Certification.__table__.columns}


@router.put("/certifications/{item_id}")
def update_certification(item_id: int, body: CertCreate, db: Session = Depends(get_db)):
    row = db.query(Certification).filter(Certification.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return {c.name: getattr(row, c.name) for c in Certification.__table__.columns}


@router.delete("/certifications/{item_id}")
def delete_certification(item_id: int, db: Session = Depends(get_db)):
    row = db.query(Certification).filter(Certification.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


# ---------- Achievements ----------

class AchievementCreate(BaseModel):
    title: str
    situation: Optional[str] = None
    action: Optional[str] = None
    result: Optional[str] = None
    tools_involved: List[str] = []
    skills_demonstrated: List[str] = []
    who_benefited: Optional[str] = None
    measurable_outcome: Optional[str] = None
    confidence: str = "confirmed"
    source: Optional[str] = None
    notes: Optional[str] = None


class GenerateBulletsRequest(BaseModel):
    situation: Optional[str] = None
    action: Optional[str] = None
    tools: Optional[str] = None
    who_benefited: Optional[str] = None
    result: Optional[str] = None
    measurable: Optional[str] = None
    confidence: str = "confirmed"


@router.get("/achievements")
def list_achievements(db: Session = Depends(get_db)):
    rows = db.query(Achievement).all()
    return [_serialize_achievement(r) for r in rows]


@router.post("/achievements")
def create_achievement(body: AchievementCreate, db: Session = Depends(get_db)):
    row = Achievement(
        **{k: (json.dumps(v) if isinstance(v, list) else v) for k, v in body.model_dump().items()}
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_achievement(row)


@router.put("/achievements/{item_id}")
def update_achievement(item_id: int, body: AchievementCreate, db: Session = Depends(get_db)):
    row = db.query(Achievement).filter(Achievement.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in body.model_dump().items():
        setattr(row, k, json.dumps(v) if isinstance(v, list) else v)
    db.commit()
    db.refresh(row)
    return _serialize_achievement(row)


@router.delete("/achievements/{item_id}")
def delete_achievement(item_id: int, db: Session = Depends(get_db)):
    row = db.query(Achievement).filter(Achievement.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.post("/achievements/generate-bullets")
async def generate_bullets(body: GenerateBulletsRequest, db: Session = Depends(get_db)):
    banned = get_banned_phrases_instruction(db)
    prompt = fill_prompt(
        "achievement_bullets",
        SITUATION=body.situation or "Not provided",
        ACTION=body.action or "Not provided",
        TOOLS=body.tools or "Not provided",
        WHO_BENEFITED=body.who_benefited or "Not provided",
        RESULT=body.result or "Not provided",
        MEASURABLE=body.measurable or "Not provided",
        CONFIDENCE=body.confidence,
        BANNED_PHRASES=banned,
    )
    provider = get_provider()
    result = await provider.generate_json(prompt)
    return result


def _serialize_achievement(row: Achievement) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "situation": row.situation,
        "action": row.action,
        "result": row.result,
        "tools_involved": json.loads(row.tools_involved or "[]"),
        "skills_demonstrated": json.loads(row.skills_demonstrated or "[]"),
        "who_benefited": row.who_benefited,
        "measurable_outcome": row.measurable_outcome,
        "confidence": row.confidence,
        "bullet_plain": row.bullet_plain,
        "bullet_strong": row.bullet_strong,
        "bullet_senior": row.bullet_senior,
        "bullet_ats": row.bullet_ats,
        "source": row.source,
        "notes": row.notes,
    }


# ---------- Projects ----------

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    role: Optional[str] = None
    technologies: List[str] = []
    outcomes: Optional[str] = None
    url: Optional[str] = None
    date_range: Optional[str] = None
    confidence: str = "confirmed"


@router.get("/projects")
def list_projects(db: Session = Depends(get_db)):
    rows = db.query(Project).all()
    return [
        {**{c.name: getattr(r, c.name) for c in Project.__table__.columns},
         "technologies": json.loads(r.technologies or "[]")}
        for r in rows
    ]


@router.post("/projects")
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    row = Project(**{k: (json.dumps(v) if isinstance(v, list) else v) for k, v in body.model_dump().items()})
    db.add(row)
    db.commit()
    db.refresh(row)
    return {**{c.name: getattr(row, c.name) for c in Project.__table__.columns},
            "technologies": json.loads(row.technologies or "[]")}


@router.put("/projects/{item_id}")
def update_project(item_id: int, body: ProjectCreate, db: Session = Depends(get_db)):
    row = db.query(Project).filter(Project.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in body.model_dump().items():
        setattr(row, k, json.dumps(v) if isinstance(v, list) else v)
    db.commit()
    db.refresh(row)
    return {**{c.name: getattr(row, c.name) for c in Project.__table__.columns},
            "technologies": json.loads(row.technologies or "[]")}


@router.delete("/projects/{item_id}")
def delete_project(item_id: int, db: Session = Depends(get_db)):
    row = db.query(Project).filter(Project.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


# ---------- Evidence ----------

class EvidenceCreate(BaseModel):
    title: str
    description: Optional[str] = None
    tools_involved: List[str] = []
    skills_demonstrated: List[str] = []
    outcome: Optional[str] = None
    value: Optional[str] = None
    confidence: str = "confirmed"
    notes: Optional[str] = None
    source: Optional[str] = None


@router.get("/evidence")
def list_evidence(db: Session = Depends(get_db)):
    rows = db.query(EvidenceItem).all()
    return [_serialize_evidence(r) for r in rows]


@router.post("/evidence")
def create_evidence(body: EvidenceCreate, db: Session = Depends(get_db)):
    row = EvidenceItem(**{k: (json.dumps(v) if isinstance(v, list) else v) for k, v in body.model_dump().items()})
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_evidence(row)


@router.put("/evidence/{item_id}")
def update_evidence(item_id: int, body: EvidenceCreate, db: Session = Depends(get_db)):
    row = db.query(EvidenceItem).filter(EvidenceItem.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in body.model_dump().items():
        setattr(row, k, json.dumps(v) if isinstance(v, list) else v)
    db.commit()
    db.refresh(row)
    return _serialize_evidence(row)


@router.delete("/evidence/{item_id}")
def delete_evidence(item_id: int, db: Session = Depends(get_db)):
    row = db.query(EvidenceItem).filter(EvidenceItem.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


def _serialize_evidence(row: EvidenceItem) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "description": row.description,
        "tools_involved": json.loads(row.tools_involved or "[]"),
        "skills_demonstrated": json.loads(row.skills_demonstrated or "[]"),
        "outcome": row.outcome,
        "value": row.value,
        "confidence": row.confidence,
        "notes": row.notes,
        "source": row.source,
    }


# ---------- Style Preferences ----------

class StyleUpdate(BaseModel):
    bullet_style: Optional[str] = None
    tone: Optional[str] = None
    preferred_cv_length: Optional[str] = None
    avoid_phrases: Optional[List[str]] = None
    preferred_phrases: Optional[List[str]] = None
    example_bullets: Optional[List[str]] = None
    notes: Optional[str] = None


@router.get("/style")
def get_style(db: Session = Depends(get_db)):
    s = get_or_create_style(db)
    return {
        "bullet_style": s.bullet_style,
        "tone": s.tone,
        "preferred_cv_length": s.preferred_cv_length,
        "avoid_phrases": json.loads(s.avoid_phrases or "[]"),
        "preferred_phrases": json.loads(s.preferred_phrases or "[]"),
        "example_bullets": json.loads(s.example_bullets or "[]"),
        "notes": s.notes,
    }


@router.put("/style")
def update_style(body: StyleUpdate, db: Session = Depends(get_db)):
    s = get_or_create_style(db)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(s, k, json.dumps(v) if isinstance(v, list) else v)
    db.commit()
    db.refresh(s)
    return {
        "bullet_style": s.bullet_style,
        "tone": s.tone,
        "preferred_cv_length": s.preferred_cv_length,
        "avoid_phrases": json.loads(s.avoid_phrases or "[]"),
        "preferred_phrases": json.loads(s.preferred_phrases or "[]"),
        "example_bullets": json.loads(s.example_bullets or "[]"),
        "notes": s.notes,
    }
