import json
from pathlib import Path
from sqlalchemy.orm import Session
from ..models.job import JobApplication
from ..storage.file_storage import (
    get_application_folder, save_application_file, save_application_json
)


def persist_application_files(db: Session, app_id: int) -> None:
    """Write all application content to the session folder on disk."""
    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        return

    folder = Path(app.session_folder)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "exports").mkdir(exist_ok=True)

    if app.job_description_raw:
        save_application_file(folder, "01-job-description.md", app.job_description_raw)

    if app.job_analysis:
        analysis = json.loads(app.job_analysis)
        md = _dict_to_md("Job Analysis", analysis)
        save_application_file(folder, "02-job-analysis.md", md)
        save_application_json(folder, "job-analysis.json", analysis)

    if app.match_scorecard:
        scorecard = json.loads(app.match_scorecard)
        md = _dict_to_md("Match Scorecard", scorecard)
        save_application_file(folder, "03-match-scorecard.md", md)
        save_application_json(folder, "match-scorecard.json", scorecard)

    if app.job_match_result:
        job_match = json.loads(app.job_match_result)
        md = _dict_to_md("Job Match Report", job_match)
        save_application_file(folder, "03b-job-match-report.md", md)
        save_application_json(folder, "job-match-report.json", job_match)

    if app.cover_letter:
        save_application_file(folder, "04-tailored-cover-letter.md", app.cover_letter)

    if app.cv_adjustment_notes:
        save_application_file(folder, "05-cv-adjustment-notes.md", app.cv_adjustment_notes)

    if app.tailored_cv:
        save_application_file(folder, "05b-tailored-cv.md", app.tailored_cv)

    if app.custom_cv:
        save_application_file(folder, "05c-custom-cv.md", app.custom_cv)

    if app.linkedin_angle:
        save_application_file(folder, "06-linkedin-angle.md", app.linkedin_angle)

    if app.recruiter_message:
        save_application_file(folder, "07-recruiter-message.md", app.recruiter_message)

    if app.interview_prep:
        prep = json.loads(app.interview_prep)
        md = _interview_prep_to_md(prep)
        save_application_file(folder, "08-interview-prep.md", md)

    if app.company_research:
        save_application_file(folder, "10-company-research.md", app.company_research)

    if app.session_notes:
        save_application_file(folder, "11-session-notes.md", app.session_notes)

    # Session metadata
    metadata = {
        "id": app.id,
        "company": app.company,
        "role": app.role,
        "location": app.location,
        "work_type": app.work_type,
        "status": app.status,
        "applied_date": app.applied_date,
        "created_at": app.created_at.isoformat() if app.created_at else None,
    }
    save_application_json(folder, "session-metadata.json", metadata)


def _dict_to_md(title: str, data: dict) -> str:
    lines = [f"# {title}", ""]
    for key, value in data.items():
        label = key.replace("_", " ").title()
        if isinstance(value, list):
            lines.append(f"## {label}")
            for item in value:
                if isinstance(item, dict):
                    lines.append("")
                    for k, v in item.items():
                        lines.append(f"**{k.replace('_', ' ').title()}:** {v}")
                else:
                    lines.append(f"- {item}")
            lines.append("")
        elif isinstance(value, dict):
            lines.append(f"## {label}")
            for k, v in value.items():
                lines.append(f"- **{k}:** {v}")
            lines.append("")
        else:
            lines.append(f"**{label}:** {value}")
            lines.append("")
    return "\n".join(lines)


def _interview_prep_to_md(prep: dict) -> str:
    sections = []
    sections.append("# Interview Preparation Pack\n")

    def add_questions(title: str, questions: list, fields: list):
        sections.append(f"## {title}\n")
        for q in questions:
            if isinstance(q, dict):
                sections.append(f"### {q.get('question', '')}\n")
                for field in fields:
                    if q.get(field):
                        label = field.replace("_", " ").title()
                        sections.append(f"**{label}:** {q[field]}\n")
                sections.append("")
            else:
                sections.append(f"- {q}\n")

    if "technical_questions" in prep:
        add_questions("Technical Questions", prep["technical_questions"],
                      ["why_likely", "star_prompt"])
    if "behavioural_questions" in prep:
        add_questions("Behavioural Questions", prep["behavioural_questions"],
                      ["why_likely", "star_prompt"])
    if "scenario_questions" in prep:
        add_questions("Scenario Questions", prep["scenario_questions"],
                      ["why_likely", "suggested_approach"])
    if "gap_questions" in prep:
        add_questions("Gap Questions", prep["gap_questions"], ["suggested_framing"])

    if "questions_to_ask_recruiter" in prep:
        sections.append("## Questions to Ask the Recruiter\n")
        for q in prep["questions_to_ask_recruiter"]:
            sections.append(f"- {q}\n")
        sections.append("")

    if "questions_to_ask_employer" in prep:
        sections.append("## Questions to Ask the Employer\n")
        for q in prep["questions_to_ask_employer"]:
            sections.append(f"- {q}\n")
        sections.append("")

    if "brush_up_topics" in prep:
        sections.append("## Brush-up Topics\n")
        for t in prep["brush_up_topics"]:
            if isinstance(t, dict):
                sections.append(f"### {t.get('topic', '')}\n")
                if t.get("what_it_covers"):
                    sections.append(f"{t['what_it_covers']}\n")
                if t.get("why"):
                    sections.append(f"**Why relevant:** {t['why']}\n")
                if t.get("key_areas"):
                    sections.append("**Key areas to study:**\n")
                    for area in t["key_areas"]:
                        sections.append(f"- {area}\n")
                if t.get("suggested_resources"):
                    sections.append(f"**Resources:** {t['suggested_resources']}\n")
                sections.append("")

    if "preparation_plan" in prep:
        sections.append("## Preparation Plan\n")
        for day in prep["preparation_plan"]:
            if isinstance(day, dict):
                sections.append(f"### {day.get('day', '')}\n")
                for task in day.get("tasks", []):
                    sections.append(f"- {task}\n")
                sections.append("")

    return "\n".join(sections)
