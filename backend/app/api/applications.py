import json
import tempfile
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models.job import JobApplication
from ..services.profile_service import build_profile_summary, get_banned_phrases_instruction
from ..services.prompt_service import fill_prompt
from ..services.application_service import persist_application_files
from ..ai.provider_factory import get_provider
from ..parsers.router import extract_text, SUPPORTED_EXTENSIONS
from ..exporters import markdown_exporter, docx_exporter, pdf_exporter
from ..storage.file_storage import get_application_folder

router = APIRouter(prefix="/api/applications", tags=["applications"])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _serialize(app: JobApplication) -> dict:
    return {
        "id": app.id,
        "company": app.company,
        "role": app.role,
        "recruiter_name": app.recruiter_name,
        "location": app.location,
        "work_type": app.work_type,
        "salary_range": app.salary_range,
        "status": app.status,
        "applied_date": app.applied_date,
        "session_folder": app.session_folder,
        "job_description_raw": app.job_description_raw,
        "job_analysis": json.loads(app.job_analysis) if app.job_analysis else None,
        "match_scorecard": json.loads(app.match_scorecard) if app.match_scorecard else None,
        "cover_letter": app.cover_letter,
        "cv_adjustment_notes": app.cv_adjustment_notes,
        "tailored_cv": app.tailored_cv,
        "interview_prep": json.loads(app.interview_prep) if app.interview_prep else None,
        "linkedin_angle": app.linkedin_angle,
        "recruiter_message": app.recruiter_message,
        "company_research": app.company_research,
        "session_notes": app.session_notes,
        "created_at": app.created_at.isoformat() if app.created_at else None,
        "updated_at": app.updated_at.isoformat() if app.updated_at else None,
    }


@router.get("")
def list_applications(db: Session = Depends(get_db)):
    rows = db.query(JobApplication).order_by(JobApplication.id.desc()).all()
    return [
        {
            "id": r.id,
            "company": r.company,
            "role": r.role,
            "location": r.location,
            "work_type": r.work_type,
            "status": r.status,
            "applied_date": r.applied_date,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "has_analysis": r.job_analysis is not None,
            "has_scorecard": r.match_scorecard is not None,
            "has_cover_letter": r.cover_letter is not None,
            "has_interview_prep": r.interview_prep is not None,
        }
        for r in rows
    ]


class ApplicationCreate(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    recruiter_name: Optional[str] = None
    location: Optional[str] = None
    work_type: Optional[str] = None
    salary_range: Optional[str] = None
    job_description_raw: Optional[str] = None


@router.post("")
def create_application(body: ApplicationCreate, db: Session = Depends(get_db)):
    folder = get_application_folder(body.company or "unknown", body.role or "role")
    app = JobApplication(
        session_folder=str(folder),
        **body.model_dump()
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return _serialize(app)


@router.get("/{app_id}")
def get_application(app_id: int, db: Session = Depends(get_db)):
    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Not found")
    return _serialize(app)


class ApplicationUpdate(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    recruiter_name: Optional[str] = None
    location: Optional[str] = None
    work_type: Optional[str] = None
    salary_range: Optional[str] = None
    status: Optional[str] = None
    applied_date: Optional[str] = None
    job_description_raw: Optional[str] = None
    company_research: Optional[str] = None
    session_notes: Optional[str] = None
    cover_letter: Optional[str] = None
    cv_adjustment_notes: Optional[str] = None
    linkedin_angle: Optional[str] = None
    recruiter_message: Optional[str] = None


@router.put("/{app_id}")
def update_application(app_id: int, body: ApplicationUpdate, db: Session = Depends(get_db)):
    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(app, k, v)
    db.commit()
    db.refresh(app)
    persist_application_files(db, app_id)
    return _serialize(app)


@router.delete("/{app_id}")
def delete_application(app_id: int, db: Session = Depends(get_db)):
    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(app)
    db.commit()
    return {"ok": True}


@router.post("/{app_id}/upload-jd")
async def upload_job_description(
    app_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Not found")

    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is larger than the 10 MB upload limit")

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        text = extract_text(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    app.job_description_raw = text
    db.commit()
    return {"ok": True, "characters": len(text)}


@router.post("/{app_id}/analyze")
async def analyze_job(app_id: int, db: Session = Depends(get_db)):
    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Not found")
    if not app.job_description_raw:
        raise HTTPException(status_code=400, detail="No job description found.")

    prompt = fill_prompt("job_analysis", JOB_DESCRIPTION=app.job_description_raw)
    provider = get_provider()
    analysis = await provider.generate_json(prompt)

    app.job_analysis = json.dumps(analysis)
    if not app.company and analysis.get("company"):
        app.company = analysis["company"]
    if not app.role and analysis.get("job_title"):
        app.role = analysis["job_title"]
    if not app.location and analysis.get("location"):
        app.location = analysis["location"]
    if not app.work_type and analysis.get("work_type"):
        app.work_type = analysis["work_type"]
    if not app.salary_range and analysis.get("salary_range"):
        app.salary_range = analysis["salary_range"]
    if not app.recruiter_name and analysis.get("recruiter_name"):
        app.recruiter_name = analysis["recruiter_name"]

    db.commit()
    persist_application_files(db, app_id)
    return {"analysis": analysis}


@router.post("/{app_id}/scorecard")
async def generate_scorecard(app_id: int, db: Session = Depends(get_db)):
    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Not found")
    if not app.job_analysis:
        raise HTTPException(status_code=400, detail="Run job analysis first.")

    profile = build_profile_summary(db)
    prompt = fill_prompt(
        "match_scorecard",
        PROFILE_SUMMARY=json.dumps(profile, indent=2),
        JOB_ANALYSIS=app.job_analysis,
    )
    provider = get_provider()
    scorecard = await provider.generate_json(prompt)
    app.match_scorecard = json.dumps(scorecard)
    db.commit()
    persist_application_files(db, app_id)
    return {"scorecard": scorecard}


@router.post("/{app_id}/cover-letter")
async def generate_cover_letter(app_id: int, db: Session = Depends(get_db)):
    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Not found")
    if not app.job_analysis:
        raise HTTPException(status_code=400, detail="Run job analysis first.")

    profile = build_profile_summary(db)
    banned = get_banned_phrases_instruction(db)
    prompt = fill_prompt(
        "cover_letter",
        PROFILE_SUMMARY=json.dumps(profile, indent=2),
        JOB_ANALYSIS=app.job_analysis,
        MATCH_SCORECARD=app.match_scorecard or "{}",
        RECRUITER_NAME=app.recruiter_name or "Hiring Manager",
        COMPANY_NAME=app.company or "the company",
        ROLE_TITLE=app.role or "the role",
        BANNED_PHRASES=banned,
    )
    provider = get_provider()
    letter = await provider.generate(prompt)
    app.cover_letter = letter
    db.commit()
    persist_application_files(db, app_id)
    return {"cover_letter": letter}


class CVNotesRequest(BaseModel):
    pass


@router.post("/{app_id}/cv-notes")
async def generate_cv_notes(app_id: int, db: Session = Depends(get_db)):
    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Not found")
    if not app.job_analysis or not app.match_scorecard:
        raise HTTPException(status_code=400, detail="Run job analysis and scorecard first.")

    profile = build_profile_summary(db)
    banned = get_banned_phrases_instruction(db)
    analysis = json.loads(app.job_analysis)
    scorecard = json.loads(app.match_scorecard)

    prompt = f"""You are a CV advisor helping a New Zealand cyber security professional tailor their CV for a specific role.

{banned}


Do not rewrite the full CV. Instead, produce specific, actionable advice.

Return markdown with these sections:
## Keywords to Weave In Naturally
## Achievements to Move Higher
## Skills to Emphasise
## Sections to Adjust
## What NOT to Change
## Risks or Gaps to be Aware Of

Job Role: {app.role} at {app.company}
Target Keywords: {', '.join(analysis.get('repeated_keywords', [])[:15])}
Strong Matches: {', '.join([m.get('skill', '') for m in scorecard.get('strong_matches', [])[:8]])}
Genuine Gaps: {', '.join([g.get('skill', '') for g in scorecard.get('genuine_gaps', [])[:5]])}
ATS Keywords: {', '.join(scorecard.get('ats_keywords_to_include', [])[:12])}
Candidate Profile Summary: {profile.get('professional_summary', '')}
"""
    provider = get_provider()
    notes = await provider.generate(prompt)
    app.cv_adjustment_notes = notes
    db.commit()
    persist_application_files(db, app_id)
    return {"cv_adjustment_notes": notes}


@router.post("/{app_id}/interview-prep")
async def generate_interview_prep(app_id: int, db: Session = Depends(get_db)):
    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Not found")
    if not app.job_analysis:
        raise HTTPException(status_code=400, detail="Run job analysis first.")

    profile = build_profile_summary(db)
    banned = get_banned_phrases_instruction(db)
    prompt = fill_prompt(
        "interview_prep",
        PROFILE_SUMMARY=json.dumps(profile, indent=2),
        JOB_ANALYSIS=app.job_analysis,
        MATCH_SCORECARD=app.match_scorecard or "{}",
        BANNED_PHRASES=banned,
    )
    provider = get_provider()
    prep = await provider.generate_json(prompt)
    app.interview_prep = json.dumps(prep)
    db.commit()
    persist_application_files(db, app_id)
    return {"interview_prep": prep}


@router.post("/{app_id}/linkedin")
async def generate_linkedin_angle(app_id: int, db: Session = Depends(get_db)):
    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Not found")
    if not app.job_analysis:
        raise HTTPException(status_code=400, detail="Run job analysis first.")

    banned = get_banned_phrases_instruction(db)
    analysis = json.loads(app.job_analysis)
    scorecard = json.loads(app.match_scorecard) if app.match_scorecard else {}

    prompt = f"""You are helping a cyber security professional position themselves on LinkedIn for a specific role.

{banned}


Write:
1. A suggested update to their LinkedIn headline (max 220 chars)
2. A 2-3 sentence note to update their About section opening for this role type
3. A short recruiter intro message (max 300 chars) they can send on LinkedIn
4. 3-5 skills to pin on their LinkedIn profile for this role

Role: {app.role} at {app.company or 'the company'}
Required Skills: {', '.join(analysis.get('required_skills', [])[:10])}
Suggested Angle: {scorecard.get('suggested_angle', '')}

Format as markdown with clear headers.
"""
    provider = get_provider()
    angle = await provider.generate(prompt)
    app.linkedin_angle = angle
    db.commit()
    persist_application_files(db, app_id)
    return {"linkedin_angle": angle}


@router.post("/{app_id}/tailored-cv")
async def generate_tailored_cv(app_id: int, db: Session = Depends(get_db)):
    from ..models.cv import CVVersion
    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Not found")
    if not app.cv_adjustment_notes:
        raise HTTPException(status_code=400, detail="Generate CV adjustment notes first.")

    master = db.query(CVVersion).order_by(CVVersion.id.desc()).first()
    if not master or not master.content_markdown:
        raise HTTPException(status_code=400, detail="No master CV found. Generate your master CV first.")

    banned = get_banned_phrases_instruction(db)
    job_analysis = app.job_analysis or "{}"
    prompt = fill_prompt(
        "tailored_cv",
        MASTER_CV=master.content_markdown,
        CV_NOTES=app.cv_adjustment_notes,
        JOB_ANALYSIS=job_analysis,
        ROLE_TITLE=app.role or "the role",
        COMPANY_NAME=app.company or "the company",
        BANNED_PHRASES=banned,
    )
    provider = get_provider()
    content = await provider.generate(prompt)
    app.tailored_cv = content
    db.commit()
    persist_application_files(db, app_id)
    return {"tailored_cv": content}


@router.get("/{app_id}/export/{fmt}")
def export_application(app_id: int, fmt: str, section: str = "cover-letter", db: Session = Depends(get_db)):
    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Not found")

    content_map = {
        "cover-letter": app.cover_letter,
        "cv-notes": app.cv_adjustment_notes,
        "tailored-cv": app.tailored_cv,
        "linkedin": app.linkedin_angle,
        "scorecard": json.dumps(json.loads(app.match_scorecard), indent=2) if app.match_scorecard else None,
    }
    content = content_map.get(section)
    if not content:
        raise HTTPException(status_code=400, detail=f"No content for section: {section}")

    folder = Path(app.session_folder) / "exports"
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
