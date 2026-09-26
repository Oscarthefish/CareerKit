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
from ..services.profile_service import (
    build_profile_summary,
    compact_profile_for_prompt,
    former_employer_names,
    get_banned_phrases_instruction,
    get_banned_phrases_list,
    in_progress_cert_names,
)
from ..services.prompt_service import fill_prompt
from ..services.application_service import persist_application_files
from ..ai.provider_factory import get_provider
from ..ai.language import to_british
from ..parsers.router import extract_text, SUPPORTED_EXTENSIONS
from ..exporters import markdown_exporter, docx_exporter, pdf_exporter
from ..storage.file_storage import get_application_folder

router = APIRouter(prefix="/api/applications", tags=["applications"])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

_UNKNOWN_COMPANY_VALUES = {"unknown", "n/a", "na", "tbc", "tbd", "none", ""}


def _company_display(app: JobApplication) -> str:
    """The company field sometimes literally holds a placeholder like "Unknown"
    (e.g. from a scraped job listing with no employer named). Treating that as
    a real company name feeds it straight into prompts, and a model asked to
    write about "Unknown" will invent a plausible-sounding substitute (a vague
    location descriptor, etc.) rather than doing the sensible thing and just
    not naming a company at all."""
    company = (app.company or "").strip()
    if company.lower() in _UNKNOWN_COMPANY_VALUES:
        return "the company"
    return company


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
        "job_match_result": json.loads(app.job_match_result) if app.job_match_result else None,
        "cover_letter": app.cover_letter,
        "cv_adjustment_notes": app.cv_adjustment_notes,
        "tailored_cv": app.tailored_cv,
        "custom_cv": app.custom_cv,
        "custom_cv_fixes_applied": json.loads(app.custom_cv_fixes_applied) if app.custom_cv_fixes_applied else None,
        "interview_prep": json.loads(app.interview_prep) if app.interview_prep else None,
        "linkedin_angle": app.linkedin_angle,
        "recruiter_message": app.recruiter_message,
        "company_research": app.company_research,
        "session_notes": app.session_notes,
        "created_at": app.created_at.isoformat() if app.created_at else None,
        "updated_at": app.updated_at.isoformat() if app.updated_at else None,
    }


def _job_match_summary(job_match_result_json: Optional[str]) -> tuple[Optional[int], Optional[str]]:
    """(score, band) for the applications list view - cheap to compute
    (parsing already-stored JSON, no LLM call) so every row can show its Job
    Match at a glance without opening the application."""
    if not job_match_result_json:
        return None, None
    try:
        job_match = json.loads(job_match_result_json).get("job_match") or {}
    except (json.JSONDecodeError, AttributeError):
        return None, None
    return job_match.get("overall"), job_match.get("band")


@router.get("")
def list_applications(db: Session = Depends(get_db)):
    rows = db.query(JobApplication).order_by(JobApplication.id.desc()).all()
    result = []
    for r in rows:
        job_match_score, job_match_band = _job_match_summary(r.job_match_result)
        result.append({
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
            "has_job_match": r.job_match_result is not None,
            "has_custom_cv": r.custom_cv is not None,
            "has_cover_letter": r.cover_letter is not None,
            "has_interview_prep": r.interview_prep is not None,
            "job_match_score": job_match_score,
            "job_match_band": job_match_band,
        })
    return result


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
    tailored_cv: Optional[str] = None
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

    # Full mode: an honest internal self-assessment can draw on the whole record,
    # including recruiter/interview-only context, since this never leaves the app.
    profile = build_profile_summary(db, mode="full")
    prompt = fill_prompt(
        "match_scorecard",
        PROFILE_SUMMARY=json.dumps(profile, indent=2),
        JOB_ANALYSIS=app.job_analysis,
    )
    provider = get_provider()
    try:
        scorecard = await provider.generate_json(
            prompt,
            required_keys=["overall_fit", "strong_matches", "genuine_gaps", "do_not_claim"],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=502,
            detail=f"The local model returned an unusable response ({e}). Try regenerating, "
                   "or pick a larger model in Settings.",
        )
    from ..services.matching.evidence import sanitize_scorecard
    scorecard = sanitize_scorecard(scorecard, profile)
    app.match_scorecard = json.dumps(scorecard)
    db.commit()
    persist_application_files(db, app_id)
    return {"scorecard": scorecard}


@router.post("/{app_id}/job-match")
async def generate_job_match(app_id: int, db: Session = Depends(get_db)):
    """Explainable Job Match report: structured JD requirements, evidence
    matched deterministically-first against the candidate's Master CV, a
    deterministic score computed from that evidence, and recommendations
    gated by the Recommendation Safety Model. See services/matching/."""
    from ..models.analysis import AnalysisSnapshot
    from ..models.cv import CVVersion
    from ..services.ats.checks import run_ats_check
    from ..services.recruiter.scoring import get_or_compute_recruiter_readiness
    from ..services.matching.evidence import match_evidence
    from ..services.matching.recommendations import build_priority_fixes
    from ..services.matching.requirements import bucket_by_importance, extract_requirements
    from ..services.matching.scoring import compute_job_match, hard_skills_table, keyword_coverage, requirement_coverage_rows
    from ..services.matching.title_match import match_title

    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Not found")
    if not app.job_analysis:
        raise HTTPException(status_code=400, detail="Run job analysis first.")

    provider = get_provider()
    analysis = json.loads(app.job_analysis)

    # Requirement extraction is cached on the application: re-analysing a JD
    # you've already broken down costs an LLM call for no benefit.
    try:
        if app.job_requirements:
            requirements = json.loads(app.job_requirements)
        else:
            requirements = await extract_requirements(provider, analysis, app.job_description_raw or "")
            app.job_requirements = json.dumps(requirements)

        profile = build_profile_summary(db, mode="full")
        compact = compact_profile_for_prompt(profile)

        requirements_with_evidence = await match_evidence(provider, requirements, profile, compact)

        job_title = analysis.get("job_title") or app.role or ""
        title_match = await match_title(provider, job_title, profile)
        title_match["job_title"] = job_title
    except ValueError as e:
        raise HTTPException(
            status_code=502,
            detail=f"The local model returned an unusable response ({e}). Try again, "
                   "or pick a larger model in Settings.",
        )

    job_match = compute_job_match(requirements_with_evidence, title_match)
    master = db.query(CVVersion).order_by(CVVersion.id.desc()).first()
    # Deterministic, no LLM call - cheap enough to compute every time rather
    # than cache, so it's always current with the latest Master CV.
    ats_check = run_ats_check(master.content_markdown) if master and master.content_markdown else None

    # Recruiter Readiness is a property of the CV, not of this job, so it's
    # cached on the CV version (force=False) rather than re-run on every
    # Job Match generation.
    recruiter_review = await get_or_compute_recruiter_readiness(provider, db, master, force=False) if master else None
    recruiter_readiness = recruiter_review["readiness"] if recruiter_review else None

    result = {
        "job_match": job_match,
        "title_match": title_match,
        "ats_check": ats_check,
        "recruiter_readiness": recruiter_readiness,
        "requirement_coverage": requirement_coverage_rows(requirements_with_evidence),
        "hard_skills": hard_skills_table(requirements_with_evidence),
        "keyword_coverage": keyword_coverage(requirements_with_evidence),
        "priority_fixes": build_priority_fixes(requirements_with_evidence, title_match),
        "requirements_by_importance": {
            level: [r["name"] for r in reqs] for level, reqs in bucket_by_importance(requirements).items()
        },
    }
    app.job_match_result = json.dumps(result)
    db.commit()

    db.add(AnalysisSnapshot(
        application_id=app.id,
        cv_version_id=master.id if master else None,
        job_match_score=job_match["overall"],
        label="master_cv",
        summary_json=json.dumps(result),
    ))
    db.commit()

    persist_application_files(db, app_id)
    return {"job_match_result": result}


@router.post("/{app_id}/custom-cv")
async def generate_custom_cv(app_id: int, db: Session = Depends(get_db)):
    """Custom CV Creation + Rescan: generates a role-tailored CV by selecting
    the strongest real evidence for THIS job from the Job Match report already
    computed for the application (see services/matching/selection.py) -
    rather than the full Master CV with a few words patched in. Selection is
    deterministic, driven entirely by the evidence CareerKit already computed
    (see selection.py's docstring) - there is nothing for the user to pick,
    since nothing here can add unsupported content regardless of choice.
    Then re-scans the result so the improvement is measurable rather than
    asserted.

    Job Match is deliberately NOT recomputed here: it measures evidence
    against the candidate's structured profile data, which selecting a
    subset of that same data for display doesn't change - re-running it
    would just reproduce the same number at the cost of two more LLM calls.
    ATS Compatibility and Recruiter Readiness are text-driven and genuinely
    can (and should) move, so those are rescanned for real."""
    from ..models.analysis import AnalysisSnapshot
    from ..services.ats.checks import run_ats_check
    from ..services.matching.selection import select_evidence_for_cv
    from ..services.recruiter.scoring import _validate_review, compute_recruiter_readiness
    from .cv import apply_cv_safety_nets

    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Not found")
    if not app.job_match_result:
        raise HTTPException(status_code=400, detail="Generate a Job Match report first.")

    job_match_result = json.loads(app.job_match_result)
    requirement_coverage = job_match_result.get("requirement_coverage", [])

    # cv_safe, not "full": Job Match itself is allowed to match against
    # confidential/recruiter_only evidence to score accurately, but nothing
    # at that confidentiality level should ever be written onto an actual CV
    # going out to an employer - the same rule the Master CV generator
    # follows by using this mode as its own default.
    profile = build_profile_summary(db, mode="cv_safe")
    selected_profile = select_evidence_for_cv(profile, requirement_coverage)

    terminology = sorted({
        row["name"] for row in requirement_coverage
        if row.get("type") in ("hard_skill", "tool", "methodology", "certification")
    })

    banned = get_banned_phrases_instruction(db)
    prompt = fill_prompt(
        "custom_cv_generate",
        PROFILE_JSON=json.dumps(selected_profile, indent=2),
        ROLE_TITLE=app.role or "the role",
        COMPANY_NAME=_company_display(app),
        JD_TERMINOLOGY=", ".join(terminology) if terminology else "(none extracted)",
        BANNED_PHRASES=banned,
    )
    provider = get_provider()
    try:
        custom_cv = to_british(await provider.generate(
            prompt,
            banned_phrases=get_banned_phrases_list(db),
            flag_years_experience=True,
            in_progress_certs=in_progress_cert_names(profile),
            former_employers=former_employer_names(profile),
        ))
    except ValueError as e:
        raise HTTPException(
            status_code=502,
            detail=f"The local model returned an unusable response ({e}). Try again, "
                   "or pick a larger model in Settings.",
        )
    custom_cv = apply_cv_safety_nets(custom_cv, selected_profile)

    selection_summary = (
        f"Selected {len(selected_profile.get('achievements', []))} of {len(profile.get('achievements', []))} achievements "
        f"and {len(selected_profile.get('skills', []))} of {len(profile.get('skills', []))} skills as relevant to this role"
    )

    app.custom_cv = custom_cv
    app.custom_cv_fixes_applied = json.dumps([selection_summary])
    db.commit()

    ats_after = run_ats_check(custom_cv)
    try:
        review = await provider.generate_json(
            fill_prompt("brutal_review", CV_CONTENT=custom_cv),
            required_keys=["overall_verdict", "priority_fixes"],
            validate=_validate_review,
        )
        recruiter_after = compute_recruiter_readiness(review, custom_cv)
    except ValueError:
        recruiter_after = None

    def _score_of(key: str) -> Optional[int]:
        section = job_match_result.get(key)
        return section.get("score") if section else None

    before = {
        "job_match": job_match_result["job_match"]["overall"],
        "ats_check": _score_of("ats_check"),
        "recruiter_readiness": _score_of("recruiter_readiness"),
    }
    after = {
        "job_match": job_match_result["job_match"]["overall"],
        "ats_check": ats_after["score"],
        "recruiter_readiness": recruiter_after["score"] if recruiter_after else None,
    }

    db.add(AnalysisSnapshot(
        application_id=app.id,
        cv_version_id=None,  # a custom CV is a per-application rendering, not a new Master CV version
        job_match_score=after["job_match"],
        label="custom_cv",
        summary_json=json.dumps({"before": before, "after": after, "ats_check": ats_after, "recruiter_readiness": recruiter_after}),
    ))
    db.commit()

    persist_application_files(db, app_id)
    return {
        "custom_cv": custom_cv,
        "selection_summary": selection_summary,
        "before": before,
        "after": after,
        "ats_check": ats_after,
        "recruiter_readiness": recruiter_after,
    }


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
        COMPANY_NAME=_company_display(app),
        ROLE_TITLE=app.role or "the role",
        BANNED_PHRASES=banned,
    )
    provider = get_provider()
    letter = to_british(await provider.generate(
        prompt,
        banned_phrases=get_banned_phrases_list(db),
        flag_years_experience=True,
        in_progress_certs=in_progress_cert_names(profile),
        former_employers=former_employer_names(profile),
    ))
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

Write everything in British / New Zealand English. Never use American spelling.

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
    notes = to_british(await provider.generate(
        prompt,
        banned_phrases=get_banned_phrases_list(db),
        in_progress_certs=in_progress_cert_names(profile),
        former_employers=former_employer_names(profile),
    ))
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

    profile = compact_profile_for_prompt(build_profile_summary(db, mode="interview_prep"))
    banned = get_banned_phrases_instruction(db)
    common = dict(
        PROFILE_SUMMARY=json.dumps(profile, indent=2),
        JOB_ANALYSIS=app.job_analysis,
        MATCH_SCORECARD=app.match_scorecard or "{}",
        BANNED_PHRASES=banned,
    )
    provider = get_provider()

    # Two focused calls rather than one huge one: an 8B model produces far better
    # structured output on a smaller task, and the questions pack and the study
    # plan are independent.
    try:
        questions = await provider.generate_json(
            fill_prompt("interview_prep", **common),
            required_keys=["technical_questions", "behavioural_questions",
                           "scenario_questions", "gap_questions"],
        )
        study = await provider.generate_json(
            fill_prompt("interview_prep_study", **common),
            required_keys=["brush_up_topics", "preparation_plan"],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=502,
            detail=f"The local model returned an unusable response ({e}). Try regenerating, "
                   "or pick a larger model in Settings.",
        )

    prep = {**questions, **study}
    prep.setdefault("company_research_notes", "Placeholder - add your own research here")

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

Role: {app.role} at {_company_display(app)}
Required Skills: {', '.join(analysis.get('required_skills', [])[:10])}
Suggested Angle: {scorecard.get('suggested_angle', '')}

Format as markdown with clear headers.
"""
    provider = get_provider()
    angle = to_british(await provider.generate(prompt, banned_phrases=get_banned_phrases_list(db)))
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

    profile = build_profile_summary(db)
    banned = get_banned_phrases_instruction(db)
    job_analysis = app.job_analysis or "{}"
    prompt = fill_prompt(
        "tailored_cv",
        MASTER_CV=master.content_markdown,
        CV_NOTES=app.cv_adjustment_notes,
        JOB_ANALYSIS=job_analysis,
        ROLE_TITLE=app.role or "the role",
        COMPANY_NAME=_company_display(app),
        BANNED_PHRASES=banned,
    )
    provider = get_provider()
    content = to_british(await provider.generate(
        prompt,
        banned_phrases=get_banned_phrases_list(db),
        flag_years_experience=True,
        in_progress_certs=in_progress_cert_names(profile),
        former_employers=former_employer_names(profile),
    ))
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
        "custom-cv": app.custom_cv,
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
