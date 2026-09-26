import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.job import JobApplication
from ..services.insights.skill_gaps import compute_skill_gaps

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("/skill-gaps")
def skill_gaps(db: Session = Depends(get_db)):
    """Master CV Feedback Loop: requirements that keep coming up across your
    target roles but are weakly evidenced in your Master CV. Built entirely
    from Job Match reports you've already generated - run Job Match on more
    applications to get a fuller picture."""
    rows = db.query(JobApplication).filter(JobApplication.job_match_result.isnot(None)).all()
    applications = []
    for r in rows:
        result = json.loads(r.job_match_result)
        applications.append({
            "role": r.role,
            "company": r.company,
            "requirement_coverage": result.get("requirement_coverage", []),
        })
    return {
        "skill_gaps": compute_skill_gaps(applications),
        "applications_considered": len(applications),
    }
