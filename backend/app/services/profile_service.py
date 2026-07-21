import json
from sqlalchemy.orm import Session
from ..models.profile import (
    Profile, WorkExperience, Skill, Certification,
    Achievement, Project, EvidenceItem, StylePreferences
)


def get_or_create_profile(db: Session) -> Profile:
    p = db.query(Profile).filter(Profile.id == 1).first()
    if not p:
        p = Profile(id=1)
        db.add(p)
        db.commit()
        db.refresh(p)
    return p


def get_banned_phrases_instruction(db: Session) -> str:
    """Return a formatted instruction block for AI prompts listing banned phrases."""
    style = get_or_create_style(db)
    phrases = json.loads(style.avoid_phrases or "[]")

    # Always-on base rules (user cannot override these)
    base = [
        "em dashes (use commas or restructure instead)",
        "excited to apply",
        "passionate about",
        "I am passionate",
        "results-driven",
        "team player",
        "fast-paced environment",
        "leverage",
        "synergy",
        "dynamic",
        "go-getter",
        "proactive",
        "innovative",
        "thought leader",
        "guru",
        "ninja",
        "rockstar",
    ]

    all_phrases = base + phrases

    lines = ["YOU MUST NOT USE any of the following words or phrases."]
    lines.append("If you would naturally write one of these, reword the sentence completely without it.\n")
    for phrase in all_phrases:
        lines.append(f'- "{phrase}"')

    if phrases:
        lines.append(f"\nThe user has also personally banned: {', '.join(repr(p) for p in phrases)}")

    return "\n".join(lines)


def get_or_create_style(db: Session) -> StylePreferences:
    s = db.query(StylePreferences).filter(StylePreferences.id == 1).first()
    if not s:
        s = StylePreferences(id=1)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def build_profile_summary(db: Session) -> dict:
    """Build a flat dict summary of the full profile for use in AI prompts."""
    profile = get_or_create_profile(db)
    experiences = db.query(WorkExperience).order_by(WorkExperience.order_index).all()
    skills = db.query(Skill).filter(Skill.confidence != "do_not_use").all()
    certs = db.query(Certification).all()
    achievements = db.query(Achievement).filter(Achievement.confidence != "do_not_use").all()
    projects = db.query(Project).filter(Project.confidence != "do_not_use").all()
    evidence = db.query(EvidenceItem).filter(EvidenceItem.confidence != "do_not_use").all()
    style = get_or_create_style(db)

    return {
        "personal": {
            "name": profile.full_name,
            "email": profile.email,
            "phone": profile.phone,
            "location": profile.location,
            "linkedin_url": profile.linkedin_url,
            "website": profile.website,
            "nz_work_rights": profile.nz_work_rights,
        },
        "professional_summary": profile.professional_summary,
        "target_roles": json.loads(profile.target_roles or "[]"),
        "work_experience": [
            {
                "company": e.company,
                "role": e.role,
                "start_date": e.start_date,
                "end_date": e.end_date,
                "is_current": e.is_current,
                "location": e.location,
                "description": e.description,
                "key_responsibilities": json.loads(e.key_responsibilities or "[]"),
                "technologies": json.loads(e.technologies or "[]"),
            }
            for e in experiences
        ],
        "skills": [
            {
                "name": s.name,
                "category": s.category,
                "proficiency": s.proficiency,
                "years_experience": s.years_experience,
                "confidence": s.confidence,
            }
            for s in skills
        ],
        "certifications": [
            {
                "name": c.name,
                "issuer": c.issuer,
                "date_obtained": c.date_obtained,
                "expiry_date": c.expiry_date,
                "in_progress": c.in_progress,
            }
            for c in certs
        ],
        "achievements": [
            {
                "title": a.title,
                "situation": a.situation,
                "action": a.action,
                "result": a.result,
                "tools_involved": json.loads(a.tools_involved or "[]"),
                "skills_demonstrated": json.loads(a.skills_demonstrated or "[]"),
                "measurable_outcome": a.measurable_outcome,
                "confidence": a.confidence,
                "bullet_strong": a.bullet_strong,
            }
            for a in achievements
        ],
        "projects": [
            {
                "name": p.name,
                "description": p.description,
                "role": p.role,
                "technologies": json.loads(p.technologies or "[]"),
                "outcomes": p.outcomes,
            }
            for p in projects
        ],
        "evidence": [
            {
                "title": ev.title,
                "description": ev.description,
                "tools_involved": json.loads(ev.tools_involved or "[]"),
                "skills_demonstrated": json.loads(ev.skills_demonstrated or "[]"),
                "outcome": ev.outcome,
                "confidence": ev.confidence,
            }
            for ev in evidence
        ],
        "style": {
            "bullet_style": style.bullet_style,
            "tone": style.tone,
            "preferred_cv_length": style.preferred_cv_length,
            "avoid_phrases": json.loads(style.avoid_phrases or "[]"),
            "preferred_phrases": json.loads(style.preferred_phrases or "[]"),
        },
    }
