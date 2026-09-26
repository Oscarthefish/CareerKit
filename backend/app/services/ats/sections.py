"""Deterministic parser for CareerKit's own markdown CV format.

This parses the SAME markdown the exporters (pdf_exporter.py / docx_exporter.py)
already read - # Name, optional subtitle, a contact line, ## SECTION HEADINGS,
### Role | Company | Dates, and bullets. Nothing here calls an LLM: the whole
point of the ATS content-structure check is that it should be 100% reproducible
against the actual CV text CareerKit is about to export.
"""
import re
from dataclasses import dataclass, field

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{6,}\d)")

# Recognised synonyms for each conventional CV section, including CareerKit's
# own default template headings (see prompts/cv_generation.md) so the app's
# own output is never flagged as using an unusual heading.
STANDARD_HEADINGS: dict[str, set[str]] = {
    "professional_summary": {"professional summary", "summary", "profile", "career summary",
                              "career profile", "professional profile"},
    "work_experience": {"work experience", "professional experience", "employment history",
                         "experience", "career history"},
    "education": {"education", "education & training", "academic background"},
    "certifications": {"certifications", "certifications & training", "professional certifications",
                        "professional training"},
    "skills": {"technical skills", "skills", "key skills", "core competencies",
               "platforms & tools", "skills & tools"},
    # Common, well-understood supplementary sections - not one of the "core
    # five" an ATS keys on, but conventional enough that flagging them as an
    # unusual heading on every single CV would just be noise.
    "supplementary": {"selected achievements", "achievements", "key achievements",
                       "projects", "selected projects", "community involvement"},
}
_ALL_KNOWN_HEADINGS = {h for group in STANDARD_HEADINGS.values() for h in group}

# ### Role | Company | Dates
ROLE_HEADING_RE = re.compile(r"^###\s+(.+)$")
# A date token is "Month YYYY", plain "YYYY", or ISO "YYYY-MM" (the format
# CareerKit's own profile/CV data actually uses) - order matters here since
# "YYYY-MM" must be tried before the bare "YYYY" alternative or the regex
# would only ever match the year and leave "-MM" dangling.
_DATE_TOKEN = r"[A-Za-z]{3,9}\.?\s+\d{4}|\d{4}-\d{2}|\d{4}"
DATE_RANGE_RE = re.compile(
    rf"({_DATE_TOKEN})\s*[-–—]\s*({_DATE_TOKEN}|Present|Current)",
    re.IGNORECASE,
)


@dataclass
class ParsedCV:
    name: str | None = None
    contact_line: str | None = None
    has_email: bool = False
    has_phone: bool = False
    section_headings: list[str] = field(default_factory=list)  # as written, in order
    unrecognised_headings: list[str] = field(default_factory=list)
    role_date_ranges: list[tuple[str, str, str]] = field(default_factory=list)  # (role_line, start, end)
    body_word_count: int = 0
    bullet_count: int = 0
    paragraph_lines: list[str] = field(default_factory=list)  # non-bullet, non-heading prose lines
    raw_lines: list[str] = field(default_factory=list)


def parse(markdown: str) -> ParsedCV:
    parsed = ParsedCV()
    lines = (markdown or "").split("\n")
    parsed.raw_lines = lines

    seen_name = False
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            continue

        if not seen_name and line.startswith("# "):
            parsed.name = line[2:].strip()
            seen_name = True
            continue

        if seen_name and parsed.contact_line is None and ("|" in line or "@" in line) and not line.startswith("#"):
            parsed.contact_line = line
            parsed.has_email = bool(EMAIL_RE.search(line))
            parsed.has_phone = bool(PHONE_RE.search(line))
            continue

        if line.startswith("## "):
            heading = line[3:].strip()
            parsed.section_headings.append(heading)
            if heading.lower() not in _ALL_KNOWN_HEADINGS:
                parsed.unrecognised_headings.append(heading)
            continue

        m = ROLE_HEADING_RE.match(line)
        if m:
            date_match = DATE_RANGE_RE.search(m.group(1))
            if date_match:
                parsed.role_date_ranges.append((m.group(1), date_match.group(1), date_match.group(2)))
            else:
                parsed.role_date_ranges.append((m.group(1), "", ""))
            continue

        if line.startswith("- ") or line.startswith("* "):
            parsed.bullet_count += 1
            parsed.body_word_count += len(line.split())
            continue

        if re.match(r"^-{3,}$", line) or line == "<!-- pagebreak -->":
            continue

        parsed.paragraph_lines.append(line)
        parsed.body_word_count += len(line.split())

    return parsed


def section_present(parsed: ParsedCV, section_key: str) -> bool:
    synonyms = STANDARD_HEADINGS.get(section_key, set())
    return any(h.lower() in synonyms for h in parsed.section_headings)
