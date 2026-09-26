from pathlib import Path
from sqlalchemy.orm import Session
from ..models.reachout import ReachOut
from ..storage.file_storage import save_application_file, save_application_json


def persist_reachout_files(db: Session, reachout_id: int) -> None:
    """Write all reach-out content to the session folder on disk."""
    r = db.query(ReachOut).filter(ReachOut.id == reachout_id).first()
    if not r or not r.session_folder:
        return

    folder = Path(r.session_folder)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "exports").mkdir(exist_ok=True)

    research_parts = []
    if r.research_summary:
        research_parts.append(f"## Business Overview\n\n{r.research_summary}")
    if r.culture_notes:
        research_parts.append(f"## Culture\n\n{r.culture_notes}")
    if r.tech_security_notes:
        research_parts.append(f"## Tech / Security Posture\n\n{r.tech_security_notes}")
    if r.recent_news:
        research_parts.append(f"## Recent News\n\n{r.recent_news}")
    if r.angle:
        research_parts.append(f"## Angle\n\n{r.angle}")
    if research_parts:
        save_application_file(folder, "01-company-research.md", f"# {r.company_name}\n\n" + "\n\n".join(research_parts))

    if r.intro_letter:
        save_application_file(folder, "02-introduction-letter.md", r.intro_letter)

    if r.cv_notes:
        save_application_file(folder, "03-cv-notes.md", r.cv_notes)

    if r.notes:
        save_application_file(folder, "04-notes.md", r.notes)

    metadata = {
        "id": r.id,
        "company_name": r.company_name,
        "website_url": r.website_url,
        "linkedin_url": r.linkedin_url,
        "status": r.status,
        "date_identified": r.date_identified,
        "date_sent": r.date_sent,
        "follow_up_date": r.follow_up_date,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
    save_application_json(folder, "session-metadata.json", metadata)
