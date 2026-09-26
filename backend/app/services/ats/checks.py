"""ATS Compatibility: deterministic checks only - no LLM calls, so a result is
always exactly reproducible from the same CV content.

Two categories, kept explicitly separate per the "don't claim to have tested
what you can't" rule:

  "content"  - checks run directly against the actual CV markdown (headings,
               contact fields, dates, length, bullets). Genuinely inspected,
               every time.
  "document" - most of these are static facts about CareerKit's own exporters
               (pdf_exporter.py / docx_exporter.py): single column, no tables,
               standard fonts, no images or hidden content. These are reported
               as guaranteed by the exporter's design, not by parsing the
               rendered PDF/DOCX - CareerKit does not currently do that, and
               says so rather than pretending otherwise. The one document
               check that DOES inspect real content is the unsupported-
               character scan, since that's genuinely derivable from the text
               and the exporter's own known Latin-1 limitation.
"""
import re
from dataclasses import dataclass

from ...exporters.pdf_exporter import _UNICODE_REPLACEMENTS
from .sections import STANDARD_HEADINGS, parse, section_present

Status = str  # "pass" | "warn" | "fail" | "info"


@dataclass
class CheckResult:
    id: str
    category: str  # "content" | "document"
    label: str
    status: Status
    detail: str
    weight: int = 1  # relative importance for scoring; "info" checks are weight 0


SCORE_BANDS = [(90, "Excellent"), (75, "Good"), (60, "Needs attention"), (0, "Significant issues")]


def _band(score: int) -> str:
    for threshold, label in SCORE_BANDS:
        if score >= threshold:
            return label
    return SCORE_BANDS[-1][1]


# Month names, so "March 2021" style dates can be told apart from bare "2021"
# and from CareerKit's own internal ISO "YYYY-MM" storage format.
_MONTH_YEAR_RE = re.compile(r"^[A-Za-z]{3,9}\.?\s+\d{4}$")
_ISO_YEAR_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
_YEAR_ONLY_RE = re.compile(r"^\d{4}$")

_PDF_KNOWN_REPLACEMENTS = set(_UNICODE_REPLACEMENTS.keys())


def _date_style(token: str) -> str | None:
    token = token.strip()
    if token.lower() in ("present", "current"):
        return None  # not a real date to compare style against
    if _MONTH_YEAR_RE.match(token):
        return "month_year"
    if _ISO_YEAR_MONTH_RE.match(token):
        return "iso_year_month"
    if _YEAR_ONLY_RE.match(token):
        return "year_only"
    return "other"


def find_unsupported_export_characters(markdown: str) -> list[str]:
    """Characters that will be altered on PDF export because fpdf2's core fonts
    only support Latin-1 (see pdf_exporter._sanitize_pdf_text) and aren't
    already one of the ones it knows how to normalise (smart quotes, dashes,
    bullets, ellipsis)."""
    problems = []
    for ch in sorted(set(markdown or "")):
        if ch in _PDF_KNOWN_REPLACEMENTS or ch in "\n\t":
            continue
        try:
            ch.encode("latin-1")
        except UnicodeEncodeError:
            problems.append(ch)
    return problems


def check_content_structure(markdown: str) -> list[CheckResult]:
    parsed = parse(markdown)
    checks: list[CheckResult] = []

    checks.append(CheckResult(
        "name", "content", "Name detected", "pass" if parsed.name else "fail",
        f'Detected "{parsed.name}".' if parsed.name else "No # Name heading found at the top of the document.",
        weight=2,
    ))
    checks.append(CheckResult(
        "email", "content", "Email detected", "pass" if parsed.has_email else "fail",
        "An email address was found in the contact line." if parsed.has_email
        else "No email address was found near the top of the document.",
        weight=2,
    ))
    checks.append(CheckResult(
        "phone", "content", "Phone number detected", "pass" if parsed.has_phone else "warn",
        "A phone number was found in the contact line." if parsed.has_phone
        else "No phone number was found near the top of the document.",
        weight=1,
    ))

    for key, label in [
        ("professional_summary", "Professional summary section"),
        ("work_experience", "Work experience section"),
        ("skills", "Skills section"),
    ]:
        present = section_present(parsed, key)
        checks.append(CheckResult(
            key, "content", label, "pass" if present else "fail",
            f"A recognised {label.lower()} heading was found." if present
            else f"No recognised {label.lower()} heading was found (e.g. "
                 f"{'/'.join(sorted(STANDARD_HEADINGS[key]))[:60]}...).",
            weight=3 if key == "work_experience" else 2,
        ))
    for key, label in [("education", "Education section"), ("certifications", "Certifications section")]:
        present = section_present(parsed, key)
        checks.append(CheckResult(
            key, "content", label, "pass" if present else "warn",
            f"A recognised {label.lower()} heading was found." if present
            else f"No recognised {label.lower()} heading was found - fine if genuinely not applicable.",
            weight=1,
        ))

    if parsed.unrecognised_headings:
        checks.append(CheckResult(
            "unusual_headings", "content", "Unusual section headings", "warn",
            "These headings may not be recognised by an ATS's section parser: "
            + ", ".join(f'"{h}"' for h in parsed.unrecognised_headings)
            + ". Consider a conventional heading instead (e.g. \"Professional Experience\", \"Skills\").",
            weight=1,
        ))
    else:
        checks.append(CheckResult(
            "unusual_headings", "content", "Unusual section headings", "pass",
            "All section headings match conventional ATS-recognised wording.", weight=1,
        ))

    missing_dates = [r for r in parsed.role_date_ranges if not r[1] or not r[2]]
    checks.append(CheckResult(
        "missing_dates", "content", "Employment dates present", "pass" if not missing_dates else "fail",
        "Every role has a start and end date." if not missing_dates
        else f"{len(missing_dates)} role heading(s) are missing a clear date range: "
             + ", ".join(r[0] for r in missing_dates[:5]),
        weight=2,
    ))

    real_dates = [r for r in parsed.role_date_ranges if r[1] and r[2]]
    styles = {s for r in real_dates for s in (_date_style(r[1]), _date_style(r[2])) if s}
    checks.append(CheckResult(
        "date_consistency", "content", "Consistent date formatting", "pass" if len(styles) <= 1 else "warn",
        "All dates use one consistent style." if len(styles) <= 1
        else "Dates mix styles (e.g. \"2021\" and \"March 2021\") - pick one consistent format throughout.",
        weight=1,
    ))

    word_count = parsed.body_word_count
    if word_count < 150:
        length_status, length_detail = "warn", f"Only {word_count} words of body content - this may read as too sparse."
    elif word_count > 2000:
        length_status, length_detail = "warn", f"{word_count} words is on the long side - check nothing repeats."
    else:
        length_status, length_detail = "pass", f"{word_count} words - a reasonable length."
    checks.append(CheckResult("length", "content", "CV length", length_status, length_detail, weight=1))

    long_paragraphs = [p for p in parsed.paragraph_lines if len(p.split()) > 60]
    checks.append(CheckResult(
        "paragraph_length", "content", "Paragraph length", "pass" if not long_paragraphs else "warn",
        "No excessively long paragraphs found." if not long_paragraphs
        else f"{len(long_paragraphs)} paragraph(s) are quite long - dense blocks of text are harder to scan than bullets.",
        weight=1,
    ))

    # A role heading (### ...) is a stronger signal of "there is experience
    # content to bullet" than the parent ## heading matching a known synonym -
    # an unusually-titled section still has real role entries under it.
    has_experience = bool(parsed.role_date_ranges)
    checks.append(CheckResult(
        "bullet_structure", "content", "Bullet-point structure",
        "pass" if parsed.bullet_count > 0 or not has_experience else "warn",
        f"{parsed.bullet_count} bullet points found." if parsed.bullet_count > 0
        else "No bullet points found - both ATS parsers and recruiters scan bullet points more easily than dense paragraphs.",
        weight=1,
    ))

    return checks


def check_document_format(markdown: str) -> list[CheckResult]:
    """Static facts about CareerKit's own exporters, plus the one genuinely
    data-dependent document/export check (unsupported characters)."""
    checks = [
        CheckResult("single_column", "document", "Single-column layout", "pass",
                    "CareerKit's PDF/DOCX export is always single-column - guaranteed by the exporter's "
                    "design, not by inspecting a rendered file.", weight=2),
        CheckResult("no_tables", "document", "No tables", "pass",
                    "The exporters do not use tables.", weight=2),
        CheckResult("no_images_graphics", "document", "No images, icons, or graphics", "pass",
                    "The exporters render text only - no images, icons, or decorative graphics.", weight=2),
        CheckResult("standard_fonts", "document", "Standard fonts", "pass",
                    "Helvetica (PDF) / Calibri (DOCX) - both standard, widely-parsed fonts.", weight=1),
        CheckResult("no_text_boxes", "document", "No text boxes or headers/footers", "pass",
                    "No text boxes; the only footer content is a page number.", weight=1),
        CheckResult("reading_order", "document", "Linear reading order", "pass",
                    "Content flows top-to-bottom in one column, so reading order matches visual order.", weight=1),
    ]

    bad_chars = find_unsupported_export_characters(markdown)
    checks.append(CheckResult(
        "export_characters", "document", "Export-safe characters", "pass" if not bad_chars else "warn",
        "No characters were found that PDF export would need to alter." if not bad_chars
        else "These characters aren't supported by the PDF font and will be altered or dropped on export: "
             + " ".join(repr(c) for c in bad_chars[:10]),
        weight=1,
    ))
    return checks


def score_checks(checks: list[CheckResult]) -> dict:
    scored = [c for c in checks if c.status in ("pass", "warn", "fail")]
    total_weight = sum(c.weight for c in scored)
    if total_weight == 0:
        return {"score": 0, "band": _band(0)}
    earned = sum(c.weight * (1.0 if c.status == "pass" else 0.4 if c.status == "warn" else 0.0) for c in scored)
    score = max(0, min(100, round(earned / total_weight * 100)))
    return {"score": score, "band": _band(score)}


def run_ats_check(markdown: str) -> dict:
    content_checks = check_content_structure(markdown)
    document_checks = check_document_format(markdown)
    all_checks = content_checks + document_checks
    overview = score_checks(all_checks)
    return {
        "score": overview["score"],
        "band": overview["band"],
        "content_checks": [c.__dict__ for c in content_checks],
        "document_checks": [c.__dict__ for c in document_checks],
    }
