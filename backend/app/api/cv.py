import json
import re
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models.cv import CVVersion
from ..services.profile_service import build_profile_summary
from ..services.prompt_service import fill_prompt
from ..ai.provider_factory import get_provider
from ..exporters import markdown_exporter, docx_exporter, pdf_exporter
from ..storage.file_storage import get_exports_dir

router = APIRouter(prefix="/api/cv", tags=["cv"])

_STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "at",
    "as", "from", "by", "that", "this", "was", "were", "is", "are", "its",
    "it's", "successfully", "approximately", "into", "over", "out", "upon",
}


def _strip_trailing_line_commas(content: str) -> str:
    """Safety net: a Key Skills category line's content sometimes gets cut
    short with a dangling trailing comma right before the line break -
    cosmetic, but never correct in any line on this CV, so just strip it."""
    return re.sub(r",[ \t]*\n", "\n", content)


def _force_correct_certifications(content: str, certifications: list[dict]) -> str:
    """Safety net: cv_generation.md instructs every certification to use its
    "display_line" field verbatim - already exactly worded and correct - but
    the model has repeatedly retyped the abbreviation for one particular
    certification wrong anyway (e.g. "Practical Junior OSINT Researcher
    (PJOR)" typed out as "(PJR)"). Rather than chase that one recurring typo,
    force the whole section to the verbatim display_line list, the same way
    Platforms & Tools is force-corrected above."""
    lines = [c.get("display_line") for c in certifications if c.get("display_line")]
    if not lines:
        return content
    correct_block = "\n".join(f"- {l}" for l in lines)
    pattern = re.compile(r"(^## CERTIFICATIONS\s*\n)(.*?)(?=\n## |\Z)", re.MULTILINE | re.DOTALL)
    if not pattern.search(content):
        return content
    return pattern.sub(lambda m: m.group(1) + correct_block + "\n", content, count=1)


_DOMAIN_SKILL_NAMES = {
    "network security", "identity & access security", "email security",
    "osint & threat research", "digital forensics fundamentals",
}


def _force_correct_ops_skills_line(content: str, skills: list[dict]) -> str:
    """Safety net: cv_generation.md says this line's "content must be
    specific, real, and drawn from the candidate's actual data" - but the
    model has been observed inflating it into a long run of invented,
    paraphrased fragments ("Timeline reconstruction", "Senior technical
    judgement", "Gap analysis") instead of the candidate's actual named
    skills. Force it to the real "technical"/"process" category skill names
    (excluding the ones that belong under Security Domains instead), the same
    way Platforms & Tools is force-corrected below."""
    ops_names = [
        s.get("name") for s in skills
        if s.get("category") in ("technical", "process")
        and s.get("name")
        and s["name"].strip().lower() not in _DOMAIN_SKILL_NAMES
    ]
    if not ops_names:
        return content
    correct_line = "**Security Operations & Incident Response:** " + ", ".join(ops_names)
    pattern = re.compile(r"^\*\*Security Operations & Incident Response:\*\*.*$", re.MULTILINE)
    if not pattern.search(content):
        return content
    return pattern.sub(lambda m: correct_line, content, count=1)


def _force_correct_projects(content: str, projects: list[dict]) -> str:
    """Safety net: cv_generation.md asks for each project as "- **Name** —
    ...", with its url included and role/technologies mentioned where useful
    - but the model has been observed dropping the bold name and the
    labelled role/technologies/outcomes/url lines on some regenerations.
    Rebuild the section deterministically from the profile's project data
    instead of trusting free-text retyping."""
    if not projects:
        return content
    blocks = []
    for p in projects:
        name = (p.get("name") or "").strip()
        if not name:
            continue
        description = (p.get("description") or "").strip()
        block = f"- **{name}**" + (f" — {description}" if description else "")
        extra_lines = []
        role = (p.get("role") or "").strip()
        if role:
            extra_lines.append(f"  Role: {role}")
        technologies = [t for t in (p.get("technologies") or []) if t]
        if technologies:
            extra_lines.append(f"  Technologies: {', '.join(technologies)}")
        outcomes = (p.get("outcomes") or "").strip()
        if outcomes:
            extra_lines.append(f"  Outcomes: {outcomes}")
        url = (p.get("url") or "").strip()
        if url:
            extra_lines.append(f"  URL: {url}")
        blocks.append("\n".join([block] + extra_lines))
    if not blocks:
        return content
    correct_block = "\n".join(blocks)
    pattern = re.compile(r"(^## PROJECTS\s*\n)(.*?)(?=\n## |\Z)", re.MULTILINE | re.DOTALL)
    if not pattern.search(content):
        return content
    return pattern.sub(lambda m: m.group(1) + correct_block + "\n", content, count=1)


def _merge_key_skills_continuations(content: str) -> str:
    """Safety net: cv_generation.md is explicit that Platforms & Tools,
    Security Domains and Leadership & People must all stay under the single
    "## KEY SKILLS" heading, never split into their own heading - but the
    model has been observed splitting one or more of them out into a
    "## KEY SKILLS (continued)" section anyway, duplicating content that's
    already present (correctly, once the Platforms & Tools force-correction
    below has run) in the main section. Strip any such section entirely
    rather than let a duplicated, non-standard heading reach the CV."""
    pattern = re.compile(r"\n## KEY SKILLS[^\n]*continued[^\n]*\n.*?(?=\n## |\Z)", re.IGNORECASE | re.DOTALL)
    return pattern.sub("", content)


def _significant_words(text: str) -> set[str]:
    words = (raw.strip(".,;:()\"'").lower() for raw in (text or "").split())
    return {w for w in words if len(w) > 3 and w not in _STOPWORDS}


def _build_achievement_bullet(title: str, detail: str) -> str:
    """Combine an achievement's title with its result/action detail, but only
    when the detail adds real information beyond the title - several
    achievements' "result" field is close to a restatement of the title
    (e.g. title "Increased endpoint protection coverage from ~60% to 98%",
    result "Increased endpoint protection coverage from approximately 60% to
    98%..."), and concatenating those would just be duplication."""
    title = (title or "").strip()
    detail = (detail or "").strip()
    if not detail:
        return title
    title_words = _significant_words(title)
    detail_words = _significant_words(detail)
    if not detail_words:
        return title
    overlap = len(detail_words & title_words) / len(detail_words)
    if overlap > 0.6:
        return title
    sep = "" if title.endswith((".", "!", "?")) else "."
    return f"{title}{sep} {detail}"


def _enrich_achievement_bullets(content: str, achievements: list[dict]) -> str:
    """Safety net: cv_generation.md already instructs the model to write each
    achievement bullet from its situation/action/result detail, using "title"
    only as a label - but a local model routinely just echoes the title
    verbatim as the whole bullet, silently dropping the specific fact (a
    metric, a named detail) that made the achievement worth including in the
    first place. Rather than trust that instruction alone, check the
    "## SELECTED ACHIEVEMENTS" section after the fact and enrich any bullet
    that's still just the bare title."""
    section_match = re.search(r"(^## SELECTED ACHIEVEMENTS\s*\n)(.*?)(?=\n## |\Z)", content, re.MULTILINE | re.DOTALL)
    if not section_match:
        return content
    section_body = section_match.group(2)

    for a in achievements:
        title = (a.get("title") or "").strip()
        if not title:
            continue
        detail = a.get("result") or a.get("action") or ""

        def _replace_line(m, title=title, detail=detail):
            existing = m.group(1).strip()
            # If the model already wove in enough of the detail itself, leave
            # its wording alone rather than overwrite a perfectly good bullet.
            detail_words = _significant_words(detail)
            if detail_words:
                existing_overlap = len(detail_words & _significant_words(existing)) / len(detail_words)
                if existing_overlap >= 0.5:
                    return m.group(0)
            return f"- {_build_achievement_bullet(title, detail)}"

        line_pattern = re.compile(rf"^- +({re.escape(title)}.*)$", re.MULTILINE | re.IGNORECASE)
        section_body = line_pattern.sub(_replace_line, section_body, count=1)

    return content[:section_match.start(2)] + section_body + content[section_match.end(2):]


def _ensure_all_achievements_present(content: str, achievements: list[dict]) -> str:
    """Safety net: with a long achievement list, a local model doesn't just
    under-enrich a bullet (see _enrich_achievement_bullets above) - it
    sometimes drops whole achievements from "## SELECTED ACHIEVEMENTS"
    entirely, and empirically favours ones earlier in the list over ones
    added more recently. Detect any achievement whose title doesn't appear
    anywhere in that section at all and append it, properly enriched, rather
    than silently letting real achievements vanish from the CV."""
    section_match = re.search(r"(^## SELECTED ACHIEVEMENTS\s*\n)(.*?)(?=\n## |\Z)", content, re.MULTILINE | re.DOTALL)
    if not section_match:
        return content
    section_body = section_match.group(2)

    missing_lines = []
    for a in achievements:
        title = (a.get("title") or "").strip()
        if not title or title.lower() in section_body.lower():
            continue
        detail = a.get("result") or a.get("action") or ""
        missing_lines.append(f"- {_build_achievement_bullet(title, detail)}")

    if missing_lines:
        section_body = section_body.rstrip("\n") + "\n" + "\n".join(missing_lines) + "\n"

    return content[:section_match.start(2)] + section_body + content[section_match.end(2):]


def _dedupe_achievement_bullets(content: str, achievements: list[dict]) -> str:
    """Safety net: rather than just under- or over-including achievements (see
    the two functions above), a local model has also been observed emitting
    the whole "## SELECTED ACHIEVEMENTS" section twice in one generation - a
    first pass of bare, untitled result-only bullets, followed by a second,
    correct pass of "Title. Result" bullets - doubling the section's length
    with no new information. Run this AFTER enrichment and the
    missing-achievement check above, so every achievement's titled bullet is
    guaranteed to exist first; then drop any bullet that (a) isn't itself
    prefixed by a known achievement title and (b) substantially restates one
    that is."""
    section_match = re.search(r"(^## SELECTED ACHIEVEMENTS\s*\n)(.*?)(?=\n## |\Z)", content, re.MULTILINE | re.DOTALL)
    if not section_match:
        return content
    section_body = section_match.group(2)
    lines = section_body.split("\n")

    titles_lower = [(a.get("title") or "").strip().lower() for a in achievements if (a.get("title") or "").strip()]

    def _starts_with_a_title(line: str) -> bool:
        text = line.lstrip("-").strip().lower()
        return any(text.startswith(t) for t in titles_lower)

    titled_lines = [l for l in lines if l.strip().startswith("-") and _starts_with_a_title(l)]

    kept = []
    for line in lines:
        if not line.strip().startswith("-") or _starts_with_a_title(line):
            kept.append(line)
            continue
        words = _significant_words(line)
        is_dup = False
        for t_line in titled_lines:
            t_words = _significant_words(t_line)
            if not words or not t_words:
                continue
            # Divide by the smaller word set rather than always the candidate
            # line's own: the bare duplicate often carries a few extra words
            # the titled version doesn't (e.g. "Project Manager"), which would
            # otherwise dilute the ratio below threshold on a real duplicate.
            overlap = len(words & t_words) / min(len(words), len(t_words))
            if overlap > 0.5:
                is_dup = True
                break
        if not is_dup:
            kept.append(line)

    new_body = "\n".join(kept)
    return content[:section_match.start(2)] + new_body + content[section_match.end(2):]


_MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _format_role_date(value: str) -> str:
    """Profile dates are stored as "YYYY-MM"; cv_generation.md has the model
    write these out as "Mon YYYY" itself, so a heading built in code needs the
    same conversion to match. Falls back to the raw value unchanged for
    anything that isn't the expected shape rather than risk mangling it."""
    if not value:
        return ""
    m = re.match(r"^(\d{4})-(\d{1,2})$", value.strip())
    if not m:
        return value
    year, month = m.groups()
    idx = int(month) - 1
    return f"{_MONTH_ABBR[idx]} {year}" if 0 <= idx < 12 else value


def _ensure_all_roles_present(content: str, work_experience: list[dict]) -> str:
    """Safety net: mirrors _ensure_all_achievements_present above, but for
    Professional Experience roles. cv_generation.md already instructs that a
    role with no description or key_responsibilities still gets its "###"
    heading line with no bullets under it, specifically so the career
    timeline never shows an unexplained gap - but a local model has been
    observed dropping such a role's heading entirely anyway (in practice, the
    oldest, least-detailed one), silently opening exactly the gap that rule
    exists to prevent. Detect any role whose company+role combination isn't
    present as a "###" heading anywhere in the section and insert it."""
    section_match = re.search(r"(^## PROFESSIONAL EXPERIENCE\s*\n)(.*?)(?=\n## |\Z)", content, re.MULTILINE | re.DOTALL)
    if not section_match:
        return content
    section_body = section_match.group(2)

    heading_lines = re.findall(r"^### .*$", section_body, re.MULTILINE)

    def _is_present(role: str, company: str) -> bool:
        role_l, company_l = role.lower(), company.lower()
        return any(role_l in h.lower() and company_l in h.lower() for h in heading_lines)

    # work_experience arrives ordered most-recent-first (order_index), so
    # walking it in that order and appending keeps any missing role(s) - in
    # practice the oldest, trailing entries - in correct chronological
    # position at the end of the section without needing general mid-list
    # insertion logic.
    missing_blocks = []
    for e in work_experience:
        role = (e.get("role") or "").strip()
        company = (e.get("company") or "").strip()
        if not role or not company or _is_present(role, company):
            continue
        start = _format_role_date(e.get("start_date") or "")
        end = "Present" if e.get("is_current") else _format_role_date(e.get("end_date") or "")
        date_range = " - ".join(p for p in (start, end) if p)
        heading = f"### {role} | {company}" + (f" | {date_range}" if date_range else "")
        lines = [heading]
        description = (e.get("description") or "").strip()
        if description:
            lines.append(f"- {description}")
        for r in e.get("key_responsibilities") or []:
            if r and r.strip():
                lines.append(f"- {r.strip()}")
        missing_blocks.append("\n".join(lines))

    if not missing_blocks:
        return content

    section_body = section_body.rstrip("\n") + "\n\n" + "\n\n".join(missing_blocks) + "\n"
    return content[:section_match.start(2)] + section_body + content[section_match.end(2):]


@router.get("/current")
def get_current_cv(db: Session = Depends(get_db)):
    row = db.query(CVVersion).order_by(CVVersion.id.desc()).first()
    if not row:
        return {"content_markdown": None, "id": None}
    return {
        "id": row.id,
        "version_name": row.version_name,
        "content_markdown": row.content_markdown,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/versions")
def list_cv_versions(db: Session = Depends(get_db)):
    rows = db.query(CVVersion).order_by(CVVersion.id.desc()).all()
    return [
        {
            "id": r.id,
            "version_name": r.version_name,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/versions/{version_id}")
def get_cv_version(version_id: int, db: Session = Depends(get_db)):
    row = db.query(CVVersion).filter(CVVersion.id == version_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "id": row.id,
        "version_name": row.version_name,
        "content_markdown": row.content_markdown,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


class CVSaveRequest(BaseModel):
    content_markdown: str
    version_name: str = "Manual save"


@router.post("/save")
def save_cv(body: CVSaveRequest, db: Session = Depends(get_db)):
    row = CVVersion(
        version_name=body.version_name,
        content_markdown=body.content_markdown,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "version_name": row.version_name}


@router.post("/generate")
async def generate_cv(mode: str = "cv_safe", db: Session = Depends(get_db)):
    from ..models.profile import ExampleCV
    profile = build_profile_summary(db, mode=mode)

    # Gather style insights from uploaded example CVs
    examples = db.query(ExampleCV).all()
    style_guidance = ""
    if examples:
        insights = []
        all_layout_ideas = []
        all_strengths = []
        for ex in examples:
            layout = json.loads(ex.layout_ideas or "[]")
            strengths = json.loads(ex.strengths or "[]")
            all_layout_ideas.extend(layout)
            all_strengths.extend(strengths)
            if ex.formatting_notes:
                insights.append(f"- {ex.original_filename}: {ex.formatting_notes}")
        if all_layout_ideas or all_strengths or insights:
            style_guidance = "\n\nSTYLE GUIDANCE FROM EXAMPLE CVs:\n"
            if all_layout_ideas:
                style_guidance += "Layout ideas worth applying:\n"
                for idea in all_layout_ideas[:6]:
                    style_guidance += f"- {idea}\n"
            if all_strengths:
                style_guidance += "Strengths to emulate:\n"
                for s in all_strengths[:5]:
                    style_guidance += f"- {s}\n"
            if insights:
                style_guidance += "Formatting notes from examples:\n"
                style_guidance += "\n".join(insights[:4])

    from ..services.profile_service import get_banned_phrases_instruction, get_banned_phrases_list
    banned = get_banned_phrases_instruction(db)
    banned_list = get_banned_phrases_list(db)
    prompt = fill_prompt(
        "cv_generation",
        PROFILE_JSON=json.dumps(profile, indent=2),
        STYLE_GUIDANCE=style_guidance,
        BANNED_PHRASES=banned,
    )
    provider = get_provider()
    content = await provider.generate(prompt, banned_phrases=banned_list, flag_years_experience=True)
    # Safety net: the local model occasionally emits a bare "-" bullet for a
    # role with no recorded detail. Strip it in code rather than trusting the
    # model to always follow the "no data, no bullet" instruction.
    content = re.sub(r"\n[ \t]*-[ \t]*\n", "\n", content)
    content = _strip_trailing_line_commas(content)
    content = _merge_key_skills_continuations(content)
    content = _force_correct_ops_skills_line(content, profile.get("skills", []))

    # Safety net: Platforms & Tools is meant to be copied verbatim from
    # platforms_and_tools_display (built deterministically so it can't
    # fabricate or drop a tool), but a long list occasionally gets truncated,
    # merged into the previous line, or dropped by the model anyway. Force the
    # block to the correct value after the fact rather than trust the copy.
    # Laid out as one category per line (the user's preferred layout) rather
    # than a single packed paragraph.
    tools_lines = profile.get("platforms_and_tools_display", [])
    if tools_lines:
        # The model sometimes also leaks the same tool list into the previous
        # ("Security Operations & Incident Response") line before (or instead
        # of) placing it correctly. Strip that leak using the known category
        # names, since the correct copy is guaranteed to exist below regardless.
        categories = [line.split(":", 1)[0].strip() for line in tools_lines]
        cat_pattern = "|".join(re.escape(c) for c in categories if c)
        if cat_pattern:
            leak_pattern = re.compile(
                rf"(\*\*Security Operations & Incident Response:\*\*.*?),?\s*(?:{cat_pattern}):.*$",
                re.MULTILINE,
            )
            content = leak_pattern.sub(lambda m: m.group(1), content, count=1)

        correct_block = "**Platforms & Tools:**\n" + "\n".join(tools_lines)
        # Matches the "**Platforms & Tools:**" line plus every line straight
        # after it that isn't itself a bold label or a heading — covers both
        # the old single-paragraph layout and this new multi-line one.
        pattern = re.compile(r"^\*\*Platforms & Tools:\*\*.*(?:\n(?!\*\*|##).*)*", re.MULTILINE)
        if pattern.search(content):
            content = pattern.sub(lambda m: correct_block, content, count=1)
        else:
            ops_pattern = re.compile(r"^\*\*Security Operations & Incident Response:\*\*.*$", re.MULTILINE)
            if ops_pattern.search(content):
                content = ops_pattern.sub(lambda m: m.group(0) + "\n" + correct_block, content, count=1)
            else:
                heading_pattern = re.compile(r"^## KEY SKILLS\s*$", re.MULTILINE)
                content = heading_pattern.sub(lambda m: m.group(0) + "\n" + correct_block, content, count=1)

    content = _force_correct_projects(content, profile.get("projects", []))
    content = _ensure_all_roles_present(content, profile.get("work_experience", []))
    content = _enrich_achievement_bullets(content, profile.get("achievements", []))
    content = _ensure_all_achievements_present(content, profile.get("achievements", []))
    content = _dedupe_achievement_bullets(content, profile.get("achievements", []))
    content = _force_correct_certifications(content, profile.get("certifications", []))

    row = CVVersion(version_name=f"AI Generated ({mode})", content_markdown=content)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "version_name": row.version_name,
        "content_markdown": content,
    }


@router.post("/review")
async def brutal_review(db: Session = Depends(get_db)):
    from ..services.recruiter.scoring import get_or_compute_recruiter_readiness

    latest = db.query(CVVersion).order_by(CVVersion.id.desc()).first()
    if not latest or not latest.content_markdown:
        raise HTTPException(status_code=400, detail="No CV found. Generate your CV first.")
    provider = get_provider()
    # force=True: this is an explicit user action, so always get a fresh take
    # rather than the cached score from a previous click.
    result = await get_or_compute_recruiter_readiness(provider, db, latest, force=True)
    if result is None:
        raise HTTPException(
            status_code=502,
            detail="The local model returned an unusable response. Try again, or pick a larger model in Settings.",
        )
    return result


@router.post("/ats-check")
def ats_health_check(db: Session = Depends(get_db)):
    """Master CV Health Check: ATS Compatibility only, no job description
    needed. Fully deterministic (see services/ats) - the same CV content
    always produces the same result."""
    from ..services.ats.checks import run_ats_check
    from ..services.ats.render import render_ats_view

    latest = db.query(CVVersion).order_by(CVVersion.id.desc()).first()
    if not latest or not latest.content_markdown:
        raise HTTPException(status_code=400, detail="No CV found. Generate your CV first.")

    result = run_ats_check(latest.content_markdown)
    result["ats_parsed_view"] = render_ats_view(latest.content_markdown)
    return result


@router.get("/export/{fmt}")
def export_cv(fmt: str, db: Session = Depends(get_db)):
    latest = db.query(CVVersion).order_by(CVVersion.id.desc()).first()
    if not latest or not latest.content_markdown:
        raise HTTPException(status_code=400, detail="No CV to export.")

    exports_dir = get_exports_dir()
    content = latest.content_markdown

    if fmt == "md":
        path = markdown_exporter.export(content, exports_dir / "master-cv.md")
        return FileResponse(str(path), filename="master-cv.md", media_type="text/markdown")
    elif fmt == "docx":
        path = docx_exporter.export(content, exports_dir / "master-cv.docx")
        return FileResponse(
            str(path),
            filename="master-cv.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    elif fmt == "pdf":
        path = pdf_exporter.export(content, exports_dir / "master-cv.pdf")
        return FileResponse(str(path), filename="master-cv.pdf", media_type="application/pdf")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {fmt}. Use md, docx, or pdf.")
