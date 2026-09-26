import json
import asyncio
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.scanner import ScanSearch, ScannedJob
from ..models.job import JobApplication
from ..scrapers import seek, absoluteit, hays, potentia, trademe
from ..storage.file_storage import get_application_folder

router = APIRouter(prefix="/api/scanner", tags=["scanner"])

SCRAPERS = {
    "seek": seek.scrape,
    "absoluteit": absoluteit.scrape,
    "hays": hays.scrape,
    "potentia": potentia.scrape,
    "trademe": trademe.scrape,
}

SITE_NAMES = {
    "seek": "Seek NZ",
    "absoluteit": "Absolute IT",
    "hays": "Hays NZ",
    "potentia": "Potentia",
    "trademe": "Trade Me Jobs",
}

ALL_SITES = list(SCRAPERS.keys())


# ---------- Searches ----------

class SearchCreate(BaseModel):
    name: str
    keywords: str
    sites: List[str] = ALL_SITES


@router.get("/searches")
def list_searches(db: Session = Depends(get_db)):
    rows = db.query(ScanSearch).order_by(ScanSearch.id.desc()).all()
    return [_ser_search(r) for r in rows]


@router.post("/searches")
def create_search(body: SearchCreate, db: Session = Depends(get_db)):
    row = ScanSearch(
        name=body.name,
        keywords=body.keywords,
        sites=json.dumps(body.sites),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _ser_search(row)


@router.delete("/searches/{search_id}")
def delete_search(search_id: int, db: Session = Depends(get_db)):
    row = db.query(ScanSearch).filter(ScanSearch.id == search_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


# ---------- Scan ----------

class ScanRequest(BaseModel):
    search_id: int


@router.post("/scan")
async def run_scan(body: ScanRequest, db: Session = Depends(get_db)):
    search = db.query(ScanSearch).filter(ScanSearch.id == body.search_id).first()
    if not search:
        raise HTTPException(status_code=404, detail="Search not found")

    keywords = search.keywords or "cyber security"
    sites = json.loads(search.sites or "[]") or ALL_SITES

    # Run all scrapers concurrently
    tasks = [SCRAPERS[site](keywords) for site in sites if site in SCRAPERS]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    new_count = 0
    site_statuses = {}
    seen_keys: set = set()  # dedup within this scan batch

    for result in results:
        if isinstance(result, Exception):
            continue
        site_statuses[result.source] = {
            "display_name": result.display_name,
            "count": len(result.jobs),
            "error": result.error,
            "search_url": result.search_url,
        }
        for job in result.jobs:
            if job.job_key in seen_keys:
                continue
            # Skip obviously malformed titles (nav links, button text, etc.)
            if not job.title or len(job.title) < 5 or job.title.lower().startswith("apply now"):
                continue
            seen_keys.add(job.job_key)
            existing = db.query(ScannedJob).filter(ScannedJob.job_key == job.job_key).first()
            if not existing:
                row = ScannedJob(
                    job_key=job.job_key,
                    title=job.title,
                    company=job.company,
                    location=job.location,
                    url=job.url,
                    description_snippet=job.description_snippet,
                    date_posted=job.date_posted,
                    source=job.source,
                    status="new",
                    search_keywords=keywords,
                )
                db.add(row)
                new_count += 1

    search.last_scanned = datetime.utcnow()
    db.commit()

    return {
        "new_jobs": new_count,
        "sites": site_statuses,
        "scanned_at": search.last_scanned.isoformat(),
    }


# ---------- Jobs ----------

@router.get("/jobs")
def list_jobs(
    status: Optional[str] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(ScannedJob).order_by(ScannedJob.first_seen.desc())
    if status:
        q = q.filter(ScannedJob.status == status)
    if source:
        q = q.filter(ScannedJob.source == source)
    return [_ser_job(r) for r in q.limit(200).all()]


class StatusUpdate(BaseModel):
    status: str  # new | seen | dismissed


@router.put("/jobs/{job_id}/status")
def update_job_status(job_id: int, body: StatusUpdate, db: Session = Depends(get_db)):
    row = db.query(ScannedJob).filter(ScannedJob.id == job_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    if body.status not in ("new", "seen", "dismissed"):
        raise HTTPException(status_code=400, detail="Invalid status")
    row.status = body.status
    db.commit()
    return {"ok": True}


@router.post("/jobs/{job_id}/apply")
def start_application(job_id: int, db: Session = Depends(get_db)):
    """Create a new JobApplication pre-filled from a scanned job listing."""
    job = db.query(ScannedJob).filter(ScannedJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Not found")

    folder = get_application_folder(job.company or "unknown", job.title or "role")
    notes = f"Job found via {SITE_NAMES.get(job.source, job.source)}\nURL: {job.url}"
    description = job.description_snippet or ""

    app = JobApplication(
        session_folder=str(folder),
        company=job.company,
        role=job.title,
        location=job.location,
        job_description_raw=description,
        company_research=notes,
        status="draft",
    )
    db.add(app)
    job.status = "seen"
    db.commit()
    db.refresh(app)
    return {"application_id": app.id}


# ---------- Helpers ----------

def _ser_search(r: ScanSearch) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "keywords": r.keywords,
        "sites": json.loads(r.sites or "[]"),
        "last_scanned": r.last_scanned.isoformat() if r.last_scanned else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _ser_job(r: ScannedJob) -> dict:
    return {
        "id": r.id,
        "title": r.title,
        "company": r.company,
        "location": r.location,
        "url": r.url,
        "description_snippet": r.description_snippet,
        "date_posted": r.date_posted,
        "source": r.source,
        "source_name": SITE_NAMES.get(r.source, r.source),
        "status": r.status,
        "search_keywords": r.search_keywords,
        "first_seen": r.first_seen.isoformat() if r.first_seen else None,
    }
