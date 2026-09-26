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


def _force_correct_key_skills_category_line(content: str, label: str, names: list[str]) -> str:
    """Shared logic for the three inline-labelled Key Skills categories
    (Security Operations & Incident Response, Security Domains, Leadership &
    People): force the line to the candidate's real skill names for that
    category. Handles three cases seen in practice from a local model: the
    line present but inflated with invented, paraphrased fragments instead of
    real skill names (corrected in place); the line entirely absent even
    though real data exists for it (inserted at the end of the KEY SKILLS
    section - exact position among the other categories doesn't matter as
    much as the content being complete and correct); and nothing real to
    show for the category at all (any existing empty/wrong line removed
    rather than left dangling)."""
    pattern = re.compile(rf"^\*\*{re.escape(label)}:\*\*.*$", re.MULTILINE)
    if not names:
        return re.sub(rf"^\*\*{re.escape(label)}:\*\*.*\n?", "", content, count=1, flags=re.MULTILINE)

    correct_line = f"**{label}:** " + ", ".join(names)
    if pattern.search(content):
        return pattern.sub(lambda m: correct_line, content, count=1)

    section_pattern = re.compile(r"(^## KEY SKILLS\s*\n)(.*?)(?=\n## |\Z)", re.MULTILINE | re.DOTALL)
    section = section_pattern.search(content)
    if not section:
        return content
    new_section_body = section.group(2).rstrip("\n") + "\n" + correct_line + "\n"
    return content[:section.start(2)] + new_section_body + content[section.end(2):]


def _force_correct_ops_skills_line(content: str, skills: list[dict]) -> str:
    """Safety net: cv_generation.md says this line's "content must be
    specific, real, and drawn from the candidate's actual data" - but the
    model has been observed inflating it into a long run of invented,
    paraphrased fragments ("Timeline reconstruction", "Senior technical
    judgement", "Gap analysis") instead of the candidate's actual named
    skills. Force it to the real "technical"/"process" category skill names
    (excluding the ones that belong under Security Domains instead)."""
    ops_names = [
        s.get("name") for s in skills
        if s.get("category") in ("technical", "process")
        and s.get("name")
        and s["name"].strip().lower() not in _DOMAIN_SKILL_NAMES
    ]
    return _force_correct_key_skills_category_line(content, "Security Operations & Incident Response", ops_names)


def _force_correct_domains_line(content: str, skills: list[dict]) -> str:
    """Safety net: mirrors _force_correct_ops_skills_line, but the failure
    mode observed for this line is different - a local model has been
    observed omitting it from the CV entirely, even for a candidate with
    real, selected domain skills to show (see selection.py; domain skills
    survive selection independently of whether the model remembers to
    render this specific line)."""
    domain_names = [
        s.get("name") for s in skills
        if s.get("category") == "technical" and s.get("name") and s["name"].strip().lower() in _DOMAIN_SKILL_NAMES
    ]
    return _force_correct_key_skills_category_line(content, "Security Domains", domain_names)


def _force_correct_leadership_line(content: str, skills: list[dict]) -> str:
    """Safety net: mirrors _force_correct_domains_line, for the "Leadership &
    People" line and the candidate's "soft" category skills."""
    leadership_names = [s.get("name") for s in skills if s.get("category") == "soft" and s.get("name")]
    return _force_correct_key_skills_category_line(content, "Leadership & People", leadership_names)


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


_INLINE_KEY_SKILLS_LABELS = ("Security Operations & Incident Response", "Security Domains", "Leadership & People")


def _strip_empty_key_skills_lines(content: str) -> str:
    """Safety net: a Key Skills category can legitimately end up with nothing
    to say for it - e.g. every "Leadership & People" skill got filtered out
    of a Custom CV for a role that doesn't call for any of them - but the
    model still prints the bold label with nothing after it rather than
    omitting the line, leaving a visible "**Leadership & People:**" dangling
    with no content. Strip any of the three inline-labelled category lines
    (never "Platforms & Tools", whose content legitimately lives on the
    following lines instead) when it's empty."""
    pattern = re.compile(
        r"^\*\*(?:" + "|".join(re.escape(label) for label in _INLINE_KEY_SKILLS_LABELS) + r"):\*\*[ \t]*\n",
        re.MULTILINE,
    )
    return pattern.sub("", content)


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


_KEY_SKILLS_ALL_LABELS = ("Security Operations & Incident Response", "Platforms & Tools", "Security Domains", "Leadership & People")


def _strip_unbolded_key_skills_duplicate_lines(content: str) -> str:
    """Safety net: rather than the doubled "## KEY SKILLS (continued)"
    heading _merge_key_skills_continuations catches above, the model has also
    been observed writing the entire Key Skills block twice a different way -
    once as plain, unbolded "Label: content" text, immediately followed by
    the correct "**Label:** content" version - under the SAME single "##
    KEY SKILLS" heading. The four category labels are distinctive enough that
    a bare, unbolded line starting with one is never legitimate content in
    its own right, so it's always the discardable duplicate; the anchored
    "^" plus requiring the label as the line's literal first characters means
    this can never match the real "**Label:**" line, which starts with "*"."""
    pattern = re.compile(
        r"^(?:" + "|".join(re.escape(label) for label in _KEY_SKILLS_ALL_LABELS) + r"):.*\n?",
        re.MULTILINE,
    )
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


def _role_blocks(section_body: str) -> tuple[list[int], list[int]]:
    """Shared helper: the start offsets of every "### " heading in a
    Professional Experience section body, plus the same list with the
    section's end appended - so section_body[starts[i]:ends[i]] is exactly
    one role's heading line plus everything under it up to the next role (or
    the end of the section)."""
    starts = [m.start() for m in re.finditer(r"^### .*$", section_body, re.MULTILINE)]
    return starts, starts[1:] + [len(section_body)]


def _remove_fabricated_role_headings(content: str, work_experience: list[dict]) -> str:
    """Safety net: over a long structured generation, a local model has been
    observed inventing a role heading that pairs a real role title with the
    WRONG real employer (e.g. "IT Team Leader | The Workshop | ..." when the
    real IT Team Leader role was at Momentum Worldwide) - effectively
    fabricating an employment history entry that never happened, alongside
    the real one elsewhere in the same CV. Remove any "###" block whose
    heading doesn't match a real role AND company together on the SAME
    work_experience entry; _ensure_all_roles_present (below) adds the real
    heading back if this removal left it missing."""
    section_match = re.search(r"(^## PROFESSIONAL EXPERIENCE\s*\n)(.*?)(?=\n## |\Z)", content, re.MULTILINE | re.DOTALL)
    if not section_match:
        return content
    section_body = section_match.group(2)

    real_pairs = [
        ((e.get("role") or "").strip().lower(), (e.get("company") or "").strip().lower())
        for e in work_experience
    ]
    real_pairs = [(r, c) for r, c in real_pairs if r and c]
    starts, ends = _role_blocks(section_body)
    if not real_pairs or not starts:
        return content

    kept = [section_body[:starts[0]]]  # preamble before the first heading, untouched
    for start, end in zip(starts, ends):
        block = section_body[start:end]
        heading_l = block.split("\n", 1)[0].lower()
        if any(r in heading_l and c in heading_l for r, c in real_pairs):
            kept.append(block)
        # else: fabricated/mismatched heading - drop the whole block

    new_body = re.sub(r"\n{3,}", "\n\n", "".join(kept))
    return content[:section_match.start(2)] + new_body + content[section_match.end(2):]


def _strip_bullets_for_dataless_roles(content: str, work_experience: list[dict]) -> str:
    """Safety net: cv_generation.md is explicit that a role with no
    description and no key_responsibilities gets its heading line only, no
    bullets at all - but a model has been observed inventing a bullet for
    such a role anyway (in practice: bleed-over from an adjacent role late in
    a long generation, once bullets have already been trimmed down elsewhere
    for a tailored Custom CV). Strip any bullets under a heading matching a
    role we know has no real underlying data to write from."""
    section_match = re.search(r"(^## PROFESSIONAL EXPERIENCE\s*\n)(.*?)(?=\n## |\Z)", content, re.MULTILINE | re.DOTALL)
    if not section_match:
        return content
    section_body = section_match.group(2)

    dataless_pairs = [
        ((e.get("role") or "").strip().lower(), (e.get("company") or "").strip().lower())
        for e in work_experience
        if not (e.get("description") or "").strip() and not (e.get("key_responsibilities") or [])
    ]
    dataless_pairs = [(r, c) for r, c in dataless_pairs if r and c]
    starts, ends = _role_blocks(section_body)
    if not dataless_pairs or not starts:
        return content

    parts = [section_body[:starts[0]]]
    for start, end in zip(starts, ends):
        block = section_body[start:end]
        newline_idx = block.find("\n")
        heading_line = block if newline_idx == -1 else block[:newline_idx]
        if any(r in heading_line.lower() and c in heading_line.lower() for r, c in dataless_pairs):
            parts.append(heading_line + "\n")
        else:
            parts.append(block)

    return content[:section_match.start(2)] + "".join(parts) + content[section_match.end(2):]


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


def _force_correct_platforms_and_tools(content: str, tools_lines: list[str]) -> str:
    """Safety net: Platforms & Tools is meant to be copied verbatim from
    platforms_and_tools_display (built deterministically so it can't
    fabricate or drop a tool), but a long list occasionally gets truncated,
    merged into the previous line, or dropped by the model anyway. Force the
    block to the correct value after the fact rather than trust the copy.
    Laid out as one category per line (the user's preferred layout) rather
    than a single packed paragraph."""
    if not tools_lines:
        return content

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
        return pattern.sub(lambda m: correct_block, content, count=1)

    ops_pattern = re.compile(r"^\*\*Security Operations & Incident Response:\*\*.*$", re.MULTILINE)
    if ops_pattern.search(content):
        return ops_pattern.sub(lambda m: m.group(0) + "\n" + correct_block, content, count=1)

    heading_pattern = re.compile(r"^## KEY SKILLS\s*$", re.MULTILINE)
    return heading_pattern.sub(lambda m: m.group(0) + "\n" + correct_block, content, count=1)


def apply_cv_safety_nets(content: str, profile: dict) -> str:
    """The full set of deterministic post-generation corrections, applied in
    order, to any CV rendered from a profile dict - the Master CV and a
    per-application Custom CV alike. Each individual function above documents
    the specific local-model failure it exists to catch; this just runs them
    in the order that makes each one's precondition hold (e.g. dedup only
    works once every real achievement is guaranteed present)."""
    content = re.sub(r"\n[ \t]*-[ \t]*\n", "\n", content)
    content = _strip_trailing_line_commas(content)
    content = _merge_key_skills_continuations(content)
    content = _strip_unbolded_key_skills_duplicate_lines(content)
    content = _force_correct_ops_skills_line(content, profile.get("skills", []))
    content = _force_correct_domains_line(content, profile.get("skills", []))
    content = _force_correct_leadership_line(content, profile.get("skills", []))
    content = _strip_empty_key_skills_lines(content)
    content = _force_correct_platforms_and_tools(content, profile.get("platforms_and_tools_display", []))
    content = _force_correct_projects(content, profile.get("projects", []))
    content = _remove_fabricated_role_headings(content, profile.get("work_experience", []))
    content = _strip_bullets_for_dataless_roles(content, profile.get("work_experience", []))
    content = _ensure_all_roles_present(content, profile.get("work_experience", []))
    content = _enrich_achievement_bullets(content, profile.get("achievements", []))
    content = _ensure_all_achievements_present(content, profile.get("achievements", []))
    content = _dedupe_achievement_bullets(content, profile.get("achievements", []))
    content = _force_correct_certifications(content, profile.get("certifications", []))
    return content


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
    content = apply_cv_safety_nets(content, profile)

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
