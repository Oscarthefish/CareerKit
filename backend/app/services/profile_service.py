import json
from sqlalchemy.orm import Session
from ..models.profile import (
    Profile, WorkExperience, Skill, Certification,
    Achievement, Project, EvidenceItem, StylePreferences,
    Training, CommunityInvolvement
)
from ..core.vocab import (
    normalise_confidence, EXCLUDED_TIERS, CONFIDENTIALITY_MODE_ALLOWLIST, DEFAULT_MODE
)

# Local models are unreliable at turning internal tracking fields (status,
# completion_status, in_progress) into natural CV wording, and at deduplicating
# a formal qualification between EDUCATION and PROFESSIONAL TRAINING. Both are
# deterministic, so we compute them here rather than leaving it to the model.
_EDUCATION_KEYWORDS = ("diploma", "degree", "bachelor", "master", "phd", "certificate iv", "certificate iii")


def _is_education(title: str) -> bool:
    t = (title or "").lower()
    return any(k in t for k in _EDUCATION_KEYWORDS)


def _platforms_and_tools_lines(tool_skills: list["Skill"]) -> list[str]:
    """Group category="tool" skills by their tool_category into one deterministic
    "Category: Product A, Product B" line per category, sorted for stable output.
    Built in code rather than left to the model — it kept fabricating a plausible
    second vendor (e.g. adding "Cisco ASA" next to Palo Alto), dropping real
    categories (Nessus, Maltego), and duplicating entries when asked to assemble
    this itself. The caller force-inserts these lines verbatim after generation
    rather than trusting the model to reproduce the layout, so the list form here
    (one category per line, as the user prefers) is safe regardless of whether
    the model itself could reliably lay it out that way."""
    grouped: dict[str, list[str]] = {}
    for s in tool_skills:
        cat = s.tool_category or "Other Tools"
        grouped.setdefault(cat, []).append(s.name)
    return [f"{cat}: {', '.join(sorted(names))}" for cat, names in sorted(grouped.items())]


def _cert_display(c: "Certification") -> str:
    issuer = f", {c.issuer}" if c.issuer else ""
    if c.in_progress:
        return f"{c.name}{issuer} (In Progress)"
    suffix = ""
    if c.status == "expired":
        suffix = " (expired)"
    elif c.status == "retired_legacy":
        suffix = " (retired)"
    year = f", {c.date_obtained}" if c.date_obtained else ""
    return f"{c.name}{issuer}{year}{suffix}"


def _training_display(t: "Training") -> str:
    provider = f", {t.provider}" if t.provider else ""
    date = f", {t.date}" if t.date else ""
    suffix = " (In Progress)" if t.completion_status in ("in_progress", "enrolled") else ""
    return f"{t.title}{provider}{date}{suffix}"


def get_or_create_profile(db: Session) -> Profile:
    p = db.query(Profile).filter(Profile.id == 1).first()
    if not p:
        p = Profile(id=1)
        db.add(p)
        db.commit()
        db.refresh(p)
    return p


_BASE_BANNED_PHRASES = [
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
        "dynamic professional",
        "go-getter",
        "proactive",
        "innovative",
        "thought leader",
        "guru",
        "ninja",
        "cyber ninja",
        "rockstar",
        "ever-evolving threat landscape",
        "digital guardian",
        "seasoned expert",
        "cutting-edge",
        "spearheaded (unless the record specifically supports leading the work)",
        "proven track record (unless immediately followed by specific evidence)",
        "hacker mindset",
        "highly motivated self-starter",
        "responsible for safeguarding the organisation from all threats",
        "seasoned professional",
        "seasoned security operations professional",
        "I am particularly drawn to this role",
        "drawn to this role",
        "drawn to this opportunity",
        "I am excited about the opportunity",
        "excited about the opportunity to contribute",
        "I believe I would be an excellent fit",
        "an excellent fit for this position",
        "valuable asset to your team",
        "I am confident that my skills and experience",
        "strong track record (unless immediately followed by specific evidence)",
        "proven ability",
        "I am impressed by",
        "impressed by the company's commitment",
        "explain in greater detail why",
        "discuss this further and explain",
]


def get_banned_phrases_list(db: Session) -> list[str]:
    """The full banned-phrase list (shared base rules plus the user's own),
    as plain strings — used both to build the prompt instruction and to check
    a model's output for violations after the fact."""
    style = get_or_create_style(db)
    phrases = json.loads(style.avoid_phrases or "[]")
    return _BASE_BANNED_PHRASES + phrases


def get_banned_phrases_instruction(db: Session) -> str:
    """Return a formatted instruction block for AI prompts listing banned phrases."""
    style = get_or_create_style(db)
    phrases = json.loads(style.avoid_phrases or "[]")
    all_phrases = get_banned_phrases_list(db)

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


def _confidence_ok(raw_confidence: str | None) -> bool:
    return normalise_confidence(raw_confidence) not in EXCLUDED_TIERS


def compact_profile_for_prompt(summary: dict) -> dict:
    """Strip a profile summary down to what an interview-prep / scorecard prompt
    actually needs, so the prompt stays well inside the model context window.

    Drops contact details, the style block, evidence and community lists, and
    the null-heavy metadata fields on skills and training.
    """
    def _skill(s: dict) -> dict:
        out = {"name": s.get("name"), "category": s.get("category"),
               "proficiency": s.get("proficiency"), "confidence": s.get("confidence")}
        if s.get("years_experience"):
            out["years_experience"] = s["years_experience"]
        return out

    def _exp(e: dict) -> dict:
        return {
            "company": e.get("company"),
            "role": e.get("role"),
            "start_date": e.get("start_date"),
            "end_date": e.get("end_date"),
            "is_current": e.get("is_current"),
            "description": e.get("description"),
            "key_responsibilities": e.get("key_responsibilities", []),
            "technologies": e.get("technologies", []),
        }

    def _training(t: dict) -> dict:
        return {"title": t.get("title"), "provider": t.get("provider"),
                "skills": t.get("skills", []), "tools": t.get("tools", []),
                "completion_status": t.get("completion_status"),
                "confidence": t.get("confidence")}

    def _ach(a: dict) -> dict:
        return {"title": a.get("title"), "situation": a.get("situation"),
                "action": a.get("action"), "result": a.get("result"),
                "tools_involved": a.get("tools_involved", []),
                "skills_demonstrated": a.get("skills_demonstrated", []),
                "confidence": a.get("confidence")}

    return {
        "professional_summary": summary.get("professional_summary"),
        "target_roles": summary.get("target_roles", []),
        "work_experience": [_exp(e) for e in summary.get("work_experience", [])],
        "skills": [_skill(s) for s in summary.get("skills", [])],
        "certifications": [
            {"name": c.get("name"), "issuer": c.get("issuer"),
             "status": c.get("status"), "in_progress": c.get("in_progress")}
            for c in summary.get("certifications", [])
        ],
        "training": [_training(t) for t in summary.get("training", [])],
        "achievements": [_ach(a) for a in summary.get("achievements", [])],
        "projects": summary.get("projects", []),
    }


def in_progress_cert_names(profile: dict) -> list[str]:
    """Certification names with in_progress=True, for the generator's post-hoc
    check that a model hasn't stated one as held (see ollama_provider)."""
    return [c["name"] for c in profile.get("certifications", []) if c.get("in_progress") and c.get("name")]


def former_employer_names(profile: dict) -> list[str]:
    """Company names where is_current is False, for the generator's post-hoc
    check that a model hasn't described a former role as the candidate's
    current one (e.g. after a redundancy)."""
    seen: list[str] = []
    for e in profile.get("work_experience", []):
        company = e.get("company")
        if company and not e.get("is_current") and company not in seen:
            seen.append(company)
    return seen


def build_profile_summary(db: Session, mode: str = DEFAULT_MODE) -> dict:
    """Build a flat dict summary of the profile for use in AI prompts.

    `mode` controls which confidentiality_level items are allowed through:
    full, cv_safe, recruiter, linkedin, interview_prep. See core/vocab.py.
    Every item's confidence tier is also normalised and excluded tiers
    (unverified, do_not_include) are always dropped regardless of mode.
    """
    allowed_confidentiality = CONFIDENTIALITY_MODE_ALLOWLIST.get(mode, CONFIDENTIALITY_MODE_ALLOWLIST[DEFAULT_MODE])

    profile = get_or_create_profile(db)
    experiences = [
        e for e in db.query(WorkExperience).order_by(WorkExperience.order_index).all()
        if (e.confidentiality_level or "cv_safe") in allowed_confidentiality
    ]
    skills = [s for s in db.query(Skill).all() if _confidence_ok(s.confidence)]
    certs = db.query(Certification).all()
    achievements = [
        a for a in db.query(Achievement).all()
        if _confidence_ok(a.confidence) and (a.confidentiality_level or "cv_safe") in allowed_confidentiality
    ]
    projects = [
        p for p in db.query(Project).all()
        if _confidence_ok(p.confidence) and (p.confidentiality_level or "cv_safe") in allowed_confidentiality
    ]
    evidence = [
        ev for ev in db.query(EvidenceItem).all()
        if _confidence_ok(ev.confidence) and (ev.confidentiality_level or "cv_safe") in allowed_confidentiality
    ]
    all_training = [t for t in db.query(Training).all() if _confidence_ok(t.confidence)]
    training = [t for t in all_training if not _is_education(t.title)]
    education = [t for t in all_training if _is_education(t.title)]
    community_field = "include_on_linkedin" if mode == "linkedin" else "include_on_cv"
    community = [
        c for c in db.query(CommunityInvolvement).all()
        if mode == "full" or getattr(c, community_field)
    ]
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
                "company": e.employer_public_name if mode in ("public", "linkedin") and e.employer_public_name else e.company,
                "role": e.role,
                "alternative_titles": json.loads(e.alternative_titles or "[]"),
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
                "aliases": json.loads(s.aliases or "[]"),
                "category": s.category,
                "proficiency": s.proficiency,
                "years_experience": s.years_experience,
                "last_used": s.last_used,
                "production_experience": s.production_experience,
                "confidence": normalise_confidence(s.confidence),
            }
            for s in skills
        ],
        "platforms_and_tools_display": _platforms_and_tools_lines(
            [s for s in skills if s.category == "tool" and s.include_on_cv]
        ),
        "certifications": [
            {
                "name": c.name,
                "issuer": c.issuer,
                "date_obtained": c.date_obtained,
                "expiry_date": c.expiry_date,
                "in_progress": c.in_progress,
                "status": c.status,
                "display_line": _cert_display(c),
            }
            for c in certs
        ],
        "training": [
            {
                "title": t.title,
                "provider": t.provider,
                "date": t.date,
                "delivery_type": t.delivery_type,
                "duration": t.duration,
                "completion_status": t.completion_status,
                "related_certification": t.related_certification,
                "tools": json.loads(t.tools or "[]"),
                "skills": json.loads(t.skills or "[]"),
                "include_by_default": t.include_by_default,
                "confidence": normalise_confidence(t.confidence),
                "display_line": _training_display(t),
            }
            for t in training
        ],
        "education": [
            {
                "title": t.title,
                "provider": t.provider,
                "date": t.date,
                "display_line": _training_display(t),
            }
            for t in education
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
                "confidence": normalise_confidence(a.confidence),
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
                "url": p.url,
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
                "confidence": normalise_confidence(ev.confidence),
            }
            for ev in evidence
        ],
        "community_involvement": [
            {
                "event": c.event,
                "location": c.location,
                "date": c.date,
                "participation_type": c.participation_type,
            }
            for c in community
        ],
        "style": {
            "bullet_style": style.bullet_style,
            "tone": style.tone,
            "preferred_cv_length": style.preferred_cv_length,
            "avoid_phrases": json.loads(style.avoid_phrases or "[]"),
            "preferred_phrases": json.loads(style.preferred_phrases or "[]"),
        },
    }
