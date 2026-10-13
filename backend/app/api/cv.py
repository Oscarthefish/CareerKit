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
    title_word_sets = [_significant_words(t) for t in titles_lower]

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
        # A paraphrase can drift far enough from an achievement's enriched
        # bullet (different verbs, different supporting detail) to dodge the
        # check above while still clearly restating the achievement itself -
        # e.g. "Contributed to building a global 24/7 SOC across three
        # locations, helping to grow the local SOC team from 2 to 6 people..."
        # vs. the titled bullet "Helped build a global 24/7 SOC across three
        # locations. Successfully built out the 6-person local SOC team..."
        # scores exactly 0.5 against the full enriched bullet (missed, the
        # check above requires > 0.5) because the extra detail on both sides
        # dilutes the overlap - but scores 0.86 against the achievement's own
        # title alone, a short and specific enough string that a high match
        # there is a strong signal by itself. Use a higher bar here (0.75)
        # than the 0.5 above, since a short title has less room to absorb an
        # incidental, non-duplicate overlap.
        if not is_dup and words:
            for t_words in title_word_sets:
                if not t_words:
                    continue
                overlap = len(words & t_words) / min(len(words), len(t_words))
                if overlap >= 0.75:
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
    observed dropping a role's heading entirely anyway, silently opening
    exactly the gap that rule exists to prevent.

    Rebuilds the whole section in true work_experience order (most-recent-
    first, via order_index), carrying over each role's existing block
    verbatim where the model wrote one and inserting a freshly-built block
    where it didn't - rather than leaving the model's own ordering alone and
    appending anything missing at the very end. An earlier version did the
    latter and assumed a dropped role is always the single oldest one; in
    practice the model can drop any role, and appending a dropped
    second-oldest role after a genuinely older one the model DID keep
    silently broke chronological order. Rebuilding from the real order
    every time makes that impossible regardless of which role(s) got
    dropped."""
    section_match = re.search(r"(^## PROFESSIONAL EXPERIENCE\s*\n)(.*?)(?=\n## |\Z)", content, re.MULTILINE | re.DOTALL)
    if not section_match:
        return content
    section_body = section_match.group(2)

    starts, ends = _role_blocks(section_body)
    # No "### " heading at all is the same degenerate case the original
    # version of this function handled gracefully - treat the whole section
    # as preamble and every role as missing, rather than giving up.
    preamble = section_body[:starts[0]] if starts else section_body
    existing_blocks = [section_body[s:e].rstrip("\n") for s, e in zip(starts, ends)]

    def _heading_role(block: str) -> str:
        heading_line = block.split("\n", 1)[0].lstrip("#").strip()
        return heading_line.split("|", 1)[0].strip().lower()

    used_blocks: set[int] = set()

    def _find_existing(role: str, company: str) -> str | None:
        role_l, company_l = role.lower(), company.lower()
        # Exact role-title match first: two real roles at the same company
        # can have one title be a plain substring of the other (e.g.
        # "Security Operations Analyst" vs "Senior Security Operations
        # Analyst") - matching by substring alone grabbed the wrong block
        # for the shorter title and silently dropped the real one for it.
        for idx, block in enumerate(existing_blocks):
            if idx in used_blocks:
                continue
            heading_line = block.split("\n", 1)[0].lower()
            if _heading_role(block) == role_l and company_l in heading_line:
                used_blocks.add(idx)
                return block
        # Fall back to substring matching - tolerates the model adding a
        # bracketed target-title alongside the real one, which
        # custom_cv_generate.md explicitly allows (e.g. "Senior Security
        # Operations Analyst (Senior SOC Analyst)").
        for idx, block in enumerate(existing_blocks):
            if idx in used_blocks:
                continue
            heading_line = block.split("\n", 1)[0].lower()
            if role_l in heading_line and company_l in heading_line:
                used_blocks.add(idx)
                return block
        return None

    rebuilt_blocks = []
    for e in work_experience:
        role = (e.get("role") or "").strip()
        company = (e.get("company") or "").strip()
        if not role or not company:
            continue
        existing = _find_existing(role, company)
        if existing is not None:
            rebuilt_blocks.append(existing)
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
        rebuilt_blocks.append("\n".join(lines))

    if not rebuilt_blocks:
        return content

    preamble_prefix = (preamble.rstrip("\n") + "\n\n") if preamble.strip() else ""
    new_body = preamble_prefix + "\n\n".join(rebuilt_blocks) + "\n"
    return content[:section_match.start(2)] + new_body + content[section_match.end(2):]


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

    # Ensure a single, correctly-ordered, correctly-valued "**Platforms &
    # Tools:**" block exists - whatever was actually under that label
    # (right, wrong, truncated, merged) gets replaced wholesale, matching
    # the label line plus every line straight after it that isn't itself a
    # bold label or a heading (covers both the old single-paragraph layout
    # and this new multi-line one).
    pattern = re.compile(r"^\*\*Platforms & Tools:\*\*.*(?:\n(?!\*\*|##).*)*", re.MULTILINE)
    ops_pattern = re.compile(r"^\*\*Security Operations & Incident Response:\*\*.*$", re.MULTILINE)
    heading_pattern = re.compile(r"^## KEY SKILLS\s*$", re.MULTILINE)
    if pattern.search(content):
        content = pattern.sub(lambda m: correct_block, content, count=1)
    elif ops_pattern.search(content):
        content = ops_pattern.sub(lambda m: m.group(0) + "\n" + correct_block, content, count=1)
    else:
        content = heading_pattern.sub(lambda m: m.group(0) + "\n" + correct_block, content, count=1)

    # The model has also been observed dumping the whole tool list a SECOND
    # time, unlabelled, elsewhere in KEY SKILLS - in practice straight after
    # the "## KEY SKILLS" heading, before anything else - in addition to the
    # correctly labelled copy just ensured above, and NOT necessarily in the
    # same internal order (two different passes over the same category
    # list, each ordered differently - a single contiguous same-order block
    # match would miss it). Strip every standalone occurrence of each
    # individual line, regardless of order or position - protecting the one
    # correct copy just inserted with a placeholder first, since its lines
    # are themselves exact matches and would otherwise be stripped right
    # back out along with the stray ones.
    sentinel = "\x00PLATFORMS_AND_TOOLS_BLOCK\x00"
    content = content.replace(correct_block, sentinel, 1)
    for line in tools_lines:
        content = re.sub(r"\n" + re.escape(line) + r"(?=\n|\Z)", "", content)
    content = re.sub(r"\n\*\*Platforms & Tools:\*\*(?=\n|\Z)", "", content)
    return content.replace(sentinel, correct_block, 1)


_TERMINOLOGY_PAREN_PATTERN = re.compile(r"\(([^)]+)\)")
_CONSECUTIVE_CAPS_PATTERN = re.compile(r"\b[A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*)+\b")


def _candidate_product_names(jd_terminology: list[str]) -> list[str]:
    """Pulls likely specific product/platform names out of JD requirement
    strings. Two patterns, both observed causing a real hallucination:
    - A parenthetical alongside a general capability, e.g. "Experience
      Building Automations in a SOAR Platform (Tines)" - the parenthetical
      is almost always the actual product name. Short/trivial fragments are
      dropped to avoid flagging something like "(NZ)" or "(e.g.)".
    - A multi-word Title Case product name named directly in the text with
      no parentheses, e.g. "Advanced experience with SIEM platforms such as
      Microsoft Sentinel or Splunk" - "Microsoft Sentinel" was hallucinated
      into a real CV's Professional Profile ("well-versed in... Microsoft
      Sentinel") despite the candidate having zero evidence for it, because
      the parenthetical-only check above never looked at this phrasing.
      Requiring 2+ consecutive capitalised words (not just one) keeps this
      safe against flagging an ordinary capitalised word at the start of a
      sentence (e.g. "Advanced") as a false candidate."""
    names: list[str] = []
    for term in jd_terminology or []:
        for match in _TERMINOLOGY_PAREN_PATTERN.findall(term):
            for part in match.split("/"):
                for piece in part.split(","):
                    piece = piece.strip()
                    if len(piece) > 2 and not piece.lower().startswith("e.g"):
                        names.append(piece)
        names.extend(_CONSECUTIVE_CAPS_PATTERN.findall(term))
    return names


def _strip_unsupported_profile_claims(content: str, profile: dict, jd_terminology: list[str]) -> str:
    """Safety net: custom_cv_generate.md shows the model JD_TERMINOLOGY to
    use "where the candidate's evidence genuinely supports it" and tells it
    never to invent a tool - but a local model has been observed ignoring
    that qualifier and writing a specific named product it was only shown
    as JD vocabulary directly into the PROFESSIONAL PROFILE paragraph as if
    the candidate had used it (e.g. claiming "experience building
    Automations in a SOAR Platform (Tines)" when nothing in the selected
    profile data mentions Tines or SOAR at all). Key Skills prose is already
    fully force-replaced by the _force_correct_*_line functions above, so
    the free-text Professional Profile paragraph is the one place this can
    still slip through.

    Checks each candidate product name named in the JD against the full
    selected-profile data actually given to the model; if a name the
    candidate doesn't have anywhere in their real data appears in a
    Professional Profile sentence, drops that whole sentence rather than
    surgically cutting a clause out of a flowing paragraph, which risks
    leaving broken grammar behind."""
    candidates = _candidate_product_names(jd_terminology)
    if not candidates:
        return content

    profile_blob = json.dumps(profile).lower()
    unsupported = [c for c in candidates if c.lower() not in profile_blob]
    if not unsupported:
        return content

    section_match = re.search(r"(^## PROFESSIONAL PROFILE\s*\n)(.*?)(?=\n## |\Z)", content, re.MULTILINE | re.DOTALL)
    if not section_match:
        return content
    section_body = section_match.group(2)

    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", section_body)
    kept = [
        s for s in sentences
        if not any(re.search(rf"\b{re.escape(term)}\b", s, re.IGNORECASE) for term in unsupported)
    ]
    new_body = " ".join(kept).strip()
    if not new_body:
        return content  # dropping every sentence would leave no profile at all - leave as-is rather than blank it

    return content[:section_match.start(2)] + new_body + "\n" + content[section_match.end(2):]


def _ensure_two_paragraph_profile(content: str) -> str:
    """Safety net: custom_cv_generate.md asks for PROFESSIONAL PROFILE as two
    short paragraphs (identity/seniority/strongest matches, then working
    style/collaboration/personal interest) - but a local model has been
    observed writing the whole thing as one continuous block with no
    paragraph break at all, or occasionally three or more. Never drops or
    rewrites a word - reflows whatever sentences are there (across however
    many paragraphs the model used) into exactly two, split at the sentence
    boundary closest to the halfway point by word count, so the section
    always renders as two paragraphs regardless of how the model structured
    it. Runs after _strip_unsupported_profile_claims above, which already
    flattens the section to one block when it removes a sentence - this
    reflows the result (unsupported-claim-free either way) into shape."""
    section_match = re.search(r"(^## PROFESSIONAL PROFILE\s*\n)(.*?)(?=\n## |\Z)", content, re.MULTILINE | re.DOTALL)
    if not section_match:
        return content
    section_body = section_match.group(2)

    flat = re.sub(r"\n+", " ", section_body).strip()
    if not flat:
        return content
    sentences = [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", flat) if s.strip()]
    if len(sentences) < 2:
        return content  # a single sentence stays a single paragraph

    total_words = len(flat.split())
    half = total_words / 2
    cum = 0
    split_idx = None
    for i, s in enumerate(sentences[:-1]):
        cum += len(s.split())
        if cum >= half:
            split_idx = i + 1
            break
    if split_idx is None:
        split_idx = len(sentences) - 1  # fallback: keep at least the last sentence in paragraph two

    first = " ".join(sentences[:split_idx]).strip()
    second = " ".join(sentences[split_idx:]).strip()
    if not first or not second:
        return content

    new_body = first + "\n\n" + second + "\n"
    return content[:section_match.start(2)] + new_body + content[section_match.end(2):]


def _strip_unsupported_claims_by_line(
    content: str, profile: dict, jd_terminology: list[str], section_heading: str
) -> str:
    """Line-granularity sibling of _strip_unsupported_profile_claims, for a
    multi-line section where each line is its own self-contained claim (e.g.
    custom_cv_generate.md's "## CORE CAPABILITIES", one bold-labelled
    capability per line) rather than a single flowing paragraph. Joining
    surviving SENTENCES back together across the whole section body, the way
    the paragraph version does, would merge separate capability lines into
    one and destroy the section's line-per-group structure - dropping the
    whole offending LINE instead preserves it."""
    candidates = _candidate_product_names(jd_terminology)
    if not candidates:
        return content

    profile_blob = json.dumps(profile).lower()
    unsupported = [c for c in candidates if c.lower() not in profile_blob]
    if not unsupported:
        return content

    pattern = re.compile(rf"(^## {re.escape(section_heading)}\s*\n)(.*?)(?=\n## |\Z)", re.MULTILINE | re.DOTALL)
    section_match = pattern.search(content)
    if not section_match:
        return content
    section_body = section_match.group(2)

    lines = section_body.split("\n")
    kept = [
        line for line in lines
        if not any(re.search(rf"\b{re.escape(term)}\b", line, re.IGNORECASE) for term in unsupported)
    ]
    new_body = "\n".join(kept)
    if not new_body.strip():
        return content  # dropping every line would leave the section blank - leave as-is rather than blank it

    return content[:section_match.start(2)] + new_body + content[section_match.end(2):]


def _non_dataless_roles(work_experience: list[dict]) -> list[dict]:
    """custom_cv_generate.md's PROFESSIONAL EXPERIENCE excludes a role with no
    description and no key_responsibilities entirely - it belongs in
    ADDITIONAL BACKGROUND instead (see _force_additional_background below),
    unlike the Master CV format which keeps a heading-only block for it (see
    _strip_bullets_for_dataless_roles). Filtering the role list down to this
    before running the shared _remove_fabricated_role_headings/
    _ensure_all_roles_present safety nets below makes them remove any
    dataless role block the model wrote and rebuild only the roles that
    belong in this section, with no new matching logic needed."""
    return [
        e for e in work_experience
        if (e.get("description") or "").strip() or (e.get("key_responsibilities") or [])
    ]


def _normalize_core_capabilities(content: str, tools_lines: list[str]) -> str:
    """Safety net: custom_cv_generate.md asks for CORE CAPABILITIES as 4-6
    one-line "**Label:** sentence" groups under the single "## CORE
    CAPABILITIES" heading - but a local model has been observed instead
    giving each group its own "### Label:" sub-heading, followed by several
    separate bullet lines rather than one sentence, with some of those
    bullets splicing in a literal, correctly-formatted SELECTED TECHNOLOGIES
    line verbatim (e.g. "SIEM & Investigation: Jira", sometimes run together
    with real capability content in the same comma-separated bullet, e.g.
    "Incident Response, Maltego, SIEM & Investigation: Jira, Endpoint &
    Detection: Cisco AMP") rather than real prose - that content already has
    its own correctly-labelled home under SELECTED TECHNOLOGIES and has no
    business being restated here. Strips any such leaked line as a literal
    substring wherever it appears, demotes any "###" sub-heading back to the
    required bold-inline form, and folds whatever real content remains under
    each label into that label's own single comma-joined line - dropping a
    group entirely if nothing but a tech-list leak was left under it, rather
    than keep an empty, padding-only group."""
    section_match = re.search(r"(^## CORE CAPABILITIES\s*\n)(.*?)(?=\n## |\Z)", content, re.MULTILINE | re.DOTALL)
    if not section_match:
        return content
    section_body = section_match.group(2)

    for line in tools_lines:
        section_body = section_body.replace(line, "")
    # Clean up the punctuation a removed line leaves dangling behind it -
    # runs of now-empty ", , ," separators and a trailing comma at end of
    # line. A label's own trailing colon (e.g. "### Global SOC Operations: "
    # with nothing real left after it) is deliberately left alone - the
    # label_pattern matching below needs that colon to recognise the line as
    # a label at all; an empty "rest" after it is handled there instead.
    section_body = re.sub(r"[ \t]*,[ \t,]*", ", ", section_body)
    section_body = re.sub(r",\s*$", "", section_body, flags=re.MULTILINE)
    section_body = re.sub(r":\s*,\s*", ": ", section_body)

    label_pattern = re.compile(r"^(?:#{2,3}\s*|\*\*)(.+?):(?:\*\*)?\s*(.*)$")
    groups: list[list] = []
    for raw_line in section_body.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        m = label_pattern.match(line) if line.startswith(("#", "*")) else None
        if m:
            label, rest = m.group(1).strip(), m.group(2).strip()
            groups.append([label, [rest] if rest else []])
            continue
        bullet = line.lstrip("-").strip()
        if bullet and groups:
            groups[-1][1].append(bullet)

    if not groups:
        return content

    new_lines = [f"**{label}:** " + ", ".join(parts) for label, parts in groups if parts]
    if not new_lines:
        return content
    new_body = "\n".join(new_lines) + "\n"
    return content[:section_match.start(2)] + new_body + content[section_match.end(2):]


def _force_selected_technologies(content: str, tools_lines: list[str]) -> str:
    """Safety net: custom_cv_generate.md's "## SELECTED TECHNOLOGIES" section
    is meant to be a verbatim copy of platforms_and_tools_display (already
    grouped into functional categories and filtered for relevance - see
    selection.py/profile_service.py), the same way the Master CV's Platforms &
    Tools line is - but, mirroring _force_correct_platforms_and_tools above, a
    long list can get truncated, reordered or dropped by a local model. Force
    the section to the correct value after the fact rather than trust the
    copy."""
    if not tools_lines:
        return content

    correct_block = "\n".join(tools_lines)
    body_pattern = re.compile(r"(^## SELECTED TECHNOLOGIES\s*\n)(.*?)(?=\n## |\Z)", re.MULTILINE | re.DOTALL)
    if body_pattern.search(content):
        content = body_pattern.sub(lambda m: m.group(1) + correct_block + "\n", content, count=1)
    else:
        # Section missing entirely - insert it directly before PROFESSIONAL
        # EXPERIENCE, a heading guaranteed to exist in valid output, rather
        # than lose the section; exact position among sections is cosmetic.
        exp_pattern = re.compile(r"^## PROFESSIONAL EXPERIENCE\s*$", re.MULTILINE)
        new_section = f"## SELECTED TECHNOLOGIES\n{correct_block}\n\n"
        if exp_pattern.search(content):
            content = exp_pattern.sub(lambda m: new_section + m.group(0), content, count=1)
        else:
            content = content.rstrip("\n") + "\n\n" + new_section

    # Guard against the model also leaking the same lines unlabelled
    # elsewhere - same sentinel-protection pattern
    # _force_correct_platforms_and_tools uses for the equivalent failure.
    sentinel = "\x00SELECTED_TECHNOLOGIES_BLOCK\x00"
    content = content.replace(correct_block, sentinel, 1)
    for line in tools_lines:
        content = re.sub(r"\n" + re.escape(line) + r"(?=\n|\Z)", "", content)
    return content.replace(sentinel, correct_block, 1)


def _force_certifications_and_training(content: str, certifications: list[dict], training: list[dict]) -> str:
    """Safety net: custom_cv_generate.md merges certifications and training
    into one "## CERTIFICATIONS & TRAINING" section (unlike the Master CV's
    separate "## CERTIFICATIONS" heading) - a pipe-separated certifications
    line, plus a "Relevant training:" line underneath when there's any
    training data. Force both to the verbatim display_line values, the same
    verbatim-force-copy discipline _force_correct_certifications uses for the
    Master CV, rather than trust free retyping of either list."""
    cert_lines = [c.get("display_line") for c in certifications if c.get("display_line")]
    training_lines = [t.get("display_line") for t in training if t.get("display_line")]
    if not cert_lines and not training_lines:
        return content

    body_parts = []
    if cert_lines:
        body_parts.append(" | ".join(cert_lines))
    if training_lines:
        body_parts.append("Relevant training: " + "; ".join(training_lines))
    correct_block = "\n".join(body_parts)

    pattern = re.compile(r"(^## CERTIFICATIONS & TRAINING\s*\n)(.*?)(?=\n## |\Z)", re.MULTILINE | re.DOTALL)
    if pattern.search(content):
        return pattern.sub(lambda m: m.group(1) + correct_block + "\n", content, count=1)

    # Missing entirely - insert directly after PROFESSIONAL EXPERIENCE, which
    # is always present, rather than lose the section.
    exp_pattern = re.compile(r"(^## PROFESSIONAL EXPERIENCE\s*\n)(.*?)(?=\n## |\Z)", re.MULTILINE | re.DOTALL)
    exp_match = exp_pattern.search(content)
    new_section = f"## CERTIFICATIONS & TRAINING\n{correct_block}\n"
    if exp_match:
        return content[:exp_match.end(2)] + "\n" + new_section + content[exp_match.end(2):]
    return content.rstrip("\n") + "\n\n" + new_section


def _force_additional_background(content: str, work_experience: list[dict], education: list[dict]) -> str:
    """Safety net: custom_cv_generate.md compresses any dataless role (no
    description, no key_responsibilities - already excluded from
    PROFESSIONAL EXPERIENCE itself, see _non_dataless_roles above) plus
    education into one short "## ADDITIONAL BACKGROUND" paragraph, rather
    than lose them from the CV entirely or give them their own full
    role/education headings the way the Master CV does. Built
    deterministically from the same display_line / role+company+date fields
    used elsewhere, rather than trust free retyping of dates and
    qualification names."""
    dataless = [
        e for e in work_experience
        if not (e.get("description") or "").strip() and not (e.get("key_responsibilities") or [])
    ]

    def _role_line(e: dict) -> str:
        role = (e.get("role") or "").strip()
        company = (e.get("company") or "").strip()
        start = _format_role_date(e.get("start_date") or "")
        end = "Present" if e.get("is_current") else _format_role_date(e.get("end_date") or "")
        date_range = " - ".join(p for p in (start, end) if p)
        label = f"{role}, {company}" if role and company else (role or company)
        return f"{label} ({date_range})" if date_range else label

    role_lines = [_role_line(e) for e in dataless if (e.get("role") or "").strip() or (e.get("company") or "").strip()]
    edu_lines = [e.get("display_line") for e in education if e.get("display_line")]

    parts = []
    if role_lines:
        parts.append("Earlier roles: " + "; ".join(role_lines) + ".")
    if edu_lines:
        parts.append("Education: " + "; ".join(edu_lines) + ".")
    if not parts:
        return content
    correct_block = " ".join(parts)

    pattern = re.compile(r"(^## ADDITIONAL BACKGROUND\s*\n)(.*?)(?=\n## |\Z)", re.MULTILINE | re.DOTALL)
    if pattern.search(content):
        return pattern.sub(lambda m: m.group(1) + correct_block + "\n", content, count=1)

    # Missing entirely - this is meant to sit just before COMMUNITY
    # INVOLVEMENT, which has its own append-at-end safety net (see
    # _ensure_community_involvement_present below) - appending here too means
    # a COMMUNITY INVOLVEMENT section the model already wrote could end up
    # before this one, but that ordering mismatch is purely cosmetic and
    # never loses data.
    return content.rstrip("\n") + "\n\n## ADDITIONAL BACKGROUND\n" + correct_block + "\n"


def _ensure_community_involvement_present(content: str, community_involvement: list[dict]) -> str:
    """Safety net: both cv_generation.md and custom_cv_generate.md instruct
    that a COMMUNITY INVOLVEMENT section should be included whenever the
    candidate profile has entries for it (already filtered upstream to
    include_on_cv=True ones - see build_profile_summary), omitted only when
    the list is genuinely empty - but a local model has been observed
    dropping the whole section anyway, even across otherwise-identical
    generations that included it correctly. The same stochastic-omission
    failure _ensure_all_achievements_present/_ensure_all_roles_present
    already guard against, just never extended to this section. Community
    involvement bullets are free prose rather than a fixed field format, so
    this can't verbatim-match a bullet the way achievement titles can -
    instead it checks whether each entry's event name appears anywhere in
    the section at all, and appends a plain factual bullet for any that
    don't."""
    if not community_involvement:
        return content

    def _fallback_bullet(c: dict) -> str:
        parts = [
            (c.get("event") or "").strip(),
            (c.get("participation_type") or "").strip(),
            (c.get("date") or "").strip(),
        ]
        return "- " + ", ".join(p for p in parts if p)

    section_match = re.search(r"(^## COMMUNITY INVOLVEMENT\s*\n)(.*?)(?=\n## |\Z)", content, re.MULTILINE | re.DOTALL)
    if section_match:
        body = section_match.group(2)
        missing = [
            c for c in community_involvement
            if (c.get("event") or "").strip() and (c["event"].strip().lower() not in body.lower())
        ]
        if not missing:
            return content
        new_body = body.rstrip("\n") + "\n" + "\n".join(_fallback_bullet(c) for c in missing) + "\n"
        return content[:section_match.start(2)] + new_body + content[section_match.end(2):]

    # Section missing entirely - it's always the last section in both CV
    # formats, so append it at the very end.
    bullets = "\n".join(_fallback_bullet(c) for c in community_involvement if (c.get("event") or "").strip())
    if not bullets:
        return content
    return content.rstrip("\n") + "\n\n## COMMUNITY INVOLVEMENT\n" + bullets + "\n"


def apply_cv_safety_nets(content: str, profile: dict, jd_terminology: list[str] | None = None) -> str:
    """The full set of deterministic post-generation corrections, applied in
    order, to any CV rendered from a profile dict - the Master CV and a
    per-application Custom CV alike. Each individual function above documents
    the specific local-model failure it exists to catch; this just runs them
    in the order that makes each one's precondition hold (e.g. dedup only
    works once every real achievement is guaranteed present)."""
    content = re.sub(r"\n[ \t]*-[ \t]*\n", "\n", content)
    content = _strip_unsupported_profile_claims(content, profile, jd_terminology or [])
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
    content = _ensure_community_involvement_present(content, profile.get("community_involvement", []))
    return content


def apply_custom_cv_safety_nets(content: str, profile: dict, jd_terminology: list[str] | None = None) -> str:
    """Custom-CV-specific sibling of apply_cv_safety_nets, for the
    restructured custom_cv_generate.md format: two-paragraph PROFESSIONAL
    PROFILE, prose CORE CAPABILITIES (replacing the Master CV's inline
    Security Domains/Leadership & People lines), deterministic SELECTED
    TECHNOLOGIES (its own heading, replacing the inline Platforms & Tools
    line), dataless roles folded into ADDITIONAL BACKGROUND instead of
    appearing heading-only in PROFESSIONAL EXPERIENCE, and a merged
    CERTIFICATIONS & TRAINING section. Shares every safety net that doesn't
    depend on that layout difference (achievement enrichment/completeness/
    dedup, project rebuilding, community involvement, blank-bullet cleanup)
    with apply_cv_safety_nets above - kept as its own explicit function
    rather than parameterising the shared one, since the two formats' key-
    skills/platforms-and-tools handling genuinely diverges rather than
    merely varying by a flag."""
    content = re.sub(r"\n[ \t]*-[ \t]*\n", "\n", content)
    content = _strip_unsupported_profile_claims(content, profile, jd_terminology or [])
    content = _ensure_two_paragraph_profile(content)
    content = _normalize_core_capabilities(content, profile.get("platforms_and_tools_display", []))
    content = _strip_unsupported_claims_by_line(content, profile, jd_terminology or [], "CORE CAPABILITIES")
    content = _strip_trailing_line_commas(content)
    non_dataless_roles = _non_dataless_roles(profile.get("work_experience", []))
    content = _force_selected_technologies(content, profile.get("platforms_and_tools_display", []))
    content = _force_correct_projects(content, profile.get("projects", []))
    content = _remove_fabricated_role_headings(content, non_dataless_roles)
    content = _ensure_all_roles_present(content, non_dataless_roles)
    content = _enrich_achievement_bullets(content, profile.get("achievements", []))
    content = _ensure_all_achievements_present(content, profile.get("achievements", []))
    content = _dedupe_achievement_bullets(content, profile.get("achievements", []))
    content = _force_certifications_and_training(content, profile.get("certifications", []), profile.get("training", []))
    content = _force_additional_background(content, profile.get("work_experience", []), profile.get("education", []))
    content = _ensure_community_involvement_present(content, profile.get("community_involvement", []))
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
