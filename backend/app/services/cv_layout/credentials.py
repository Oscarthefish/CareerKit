"""Certifications & Training as structured, scannable CV entries.

Built from the structured Certification / Training records (see
models/profile.py) rather than free text, as three compact groups:

    ## CERTIFICATIONS & TRAINING
    #### Certifications
    - GIAC Penetration Tester (GPEN) — GIAC / SANS | 2018
    #### Professional Training
    - SANS SEC504 — Hacker Tools, Techniques, and Incident Handling
    #### Currently Studying
    - Certified Information Systems Security Professional (CISSP) — ISC2 | In progress

Honesty rules, all deliberate:
- An awarded certification shows the year it was obtained, never "active" or
  "current" - nothing here infers that an older certification is still valid.
  "Expired"/"Retired" appear only when the record's own status says so.
- Training is never listed under Certifications, and its entry never mentions
  a related certification, so attending a course can't read as passing an exam.
- In-progress certifications and in-progress/enrolled training go under
  Currently Studying, separate from anything awarded or completed.
- Names, providers and dates are taken verbatim from the records; the only
  rewording is moving a leading course code ("SEC504: Title", provider "SANS")
  into "SANS SEC504 — Title", which drops nothing.
"""
from __future__ import annotations

import re

SECTION_HEADING = "CERTIFICATIONS & TRAINING"
GROUP_CERTIFICATIONS = "Certifications"
GROUP_TRAINING = "Professional Training"
GROUP_STUDYING = "Currently Studying"

_IN_PROGRESS_TRAINING = {"in_progress", "enrolled"}
# Only training that genuinely happened belongs on a CV - "purchased, not
# started" and "unconfirmed" records stay off it, as before this change.
_COMPLETED_TRAINING = {"completed", None, ""}

# "SEC504: Hacker Tools..." / "FOR500 - Windows..." / "SC-200: Microsoft..."
_COURSE_CODE_RE = re.compile(r"^([A-Z]{2,5}-?\d{2,4}[A-Z]?)\s*[:\-–—]\s*(.+)$")

SEP = " — "


def _year(value) -> str:
    return str(value).strip() if value else ""


def cert_entry(cert: dict) -> str:
    name = (cert.get("name") or "").strip()
    issuer = (cert.get("issuer") or "").strip()
    parts = [name + (SEP + issuer if issuer else "")]
    if cert.get("in_progress"):
        parts.append("In progress")
    else:
        if _year(cert.get("date_obtained")):
            parts.append(_year(cert.get("date_obtained")))
        status = cert.get("status")
        if status == "expired":
            parts.append("Expired")
        elif status == "retired_legacy":
            parts.append("Retired")
    return " | ".join(p for p in parts if p)


def training_entry(training: dict) -> str:
    title = (training.get("title") or "").strip()
    provider = (training.get("provider") or "").strip()
    m = _COURSE_CODE_RE.match(title)
    # "SANS SEC504 — Title" when the provider is a short brand that reads
    # naturally as a prefix; otherwise keep the provider after the title.
    if m and provider and len(provider.split()) == 1 and provider.lower() not in title.lower():
        head = f"{provider} {m.group(1)}{SEP}{m.group(2).strip()}"
    elif m:
        head = f"{m.group(1)}: {m.group(2).strip()}" + (SEP + provider if provider else "")
    else:
        head = title + (SEP + provider if provider and provider.lower() not in title.lower() else "")
    parts = [head]
    if training.get("completion_status") in _IN_PROGRESS_TRAINING:
        parts.append("In progress")
    elif _year(training.get("date")):
        parts.append(_year(training.get("date")))
    return " | ".join(parts)


def group_entries(certifications: list[dict], training: list[dict]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {GROUP_CERTIFICATIONS: [], GROUP_TRAINING: [], GROUP_STUDYING: []}
    for c in certifications or []:
        if not (c.get("name") or "").strip():
            continue
        groups[GROUP_STUDYING if c.get("in_progress") else GROUP_CERTIFICATIONS].append(cert_entry(c))
    for t in training or []:
        if not (t.get("title") or "").strip():
            continue
        status = t.get("completion_status")
        if status in _IN_PROGRESS_TRAINING:
            groups[GROUP_STUDYING].append(training_entry(t))
        elif status in _COMPLETED_TRAINING:
            groups[GROUP_TRAINING].append(training_entry(t))
    return groups


def render_groups(groups: dict[str, list[str]]) -> str:
    """Section body (no ## heading). Empty groups are omitted."""
    out = []
    for label in (GROUP_CERTIFICATIONS, GROUP_TRAINING, GROUP_STUDYING):
        entries = groups.get(label) or []
        if entries:
            out.append(f"#### {label}")
            out.extend(f"- {e}" for e in entries)
    return "\n".join(out)


def build_section(certifications: list[dict], training: list[dict]) -> str | None:
    body = render_groups(group_entries(certifications, training))
    return f"## {SECTION_HEADING}\n{body}\n" if body else None


# ---------------------------------------------------------------------------
# Backward compatibility with CVs saved before this structure existed.
# ---------------------------------------------------------------------------

def _legacy_cert_line(c: dict) -> str:
    """Exactly what profile_service._cert_display used to produce."""
    issuer = f", {c.get('issuer')}" if c.get("issuer") else ""
    if c.get("in_progress"):
        return f"{c.get('name')}{issuer} (In Progress)"
    suffix = {"expired": " (expired)", "retired_legacy": " (retired)"}.get(c.get("status"), "")
    year = f", {c.get('date_obtained')}" if c.get("date_obtained") else ""
    return f"{c.get('name')}{issuer}{year}{suffix}"


def _legacy_training_line(t: dict) -> str:
    """Exactly what profile_service._training_display used to produce."""
    provider = f", {t.get('provider')}" if t.get("provider") else ""
    date = f", {t.get('date')}" if t.get("date") else ""
    suffix = " (In Progress)" if t.get("completion_status") in _IN_PROGRESS_TRAINING else ""
    return f"{t.get('title')}{provider}{date}{suffix}"


_LEGACY_IN_PROGRESS_RE = re.compile(r"\s*\((?:in progress|enrolled)\)\s*$", re.IGNORECASE)


def legacy_entries(body: str) -> tuple[list[str], list[str]]:
    """Split an old-style section body into (certification lines, training
    lines), verbatim. Handles the Custom CV's pipe-joined paragraph plus
    "Relevant training: a; b" line, and the Master CV's bullet lists."""
    certs, training = [], []
    for raw in body.split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        is_training = False
        if line.lower().startswith("relevant training:"):
            line, is_training = line.split(":", 1)[1].strip(), True
            items = [p.strip() for p in line.split(";")]
        elif line.startswith(("- ", "* ")):
            items = [line[2:].strip()]
        else:
            items = [p.strip() for p in line.split(" | ")]
        (training if is_training else certs).extend(i for i in items if i)
    return certs, training


def convert_legacy(cert_body: str, training_body: str,
                   certifications: list[dict] | None, training: list[dict] | None) -> str | None:
    """Turn legacy certification/training text into the grouped structure.

    Entries that exactly match a current profile record's legacy display text
    are rebuilt from that record (same facts, structured wording). Anything
    else - hand-edited text, a record since deleted - is kept verbatim, only
    moved onto its own line. Nothing is dropped."""
    # Custom CV: one body holding both a pipe-joined certifications paragraph
    # and a "Relevant training:" line.
    cert_lines, training_lines = legacy_entries(cert_body)
    if training_body:
        # Master CV: everything in a separate PROFESSIONAL TRAINING section is
        # training, however it's punctuated.
        a, b = legacy_entries(training_body)
        training_lines = training_lines + a + b
    if not cert_lines and not training_lines:
        return None

    by_cert_line = {_legacy_cert_line(c): c for c in certifications or []}
    by_training_line = {_legacy_training_line(t): t for t in training or []}
    groups: dict[str, list[str]] = {GROUP_CERTIFICATIONS: [], GROUP_TRAINING: [], GROUP_STUDYING: []}

    for line in cert_lines:
        rec = by_cert_line.get(line)
        if rec is not None:
            groups[GROUP_STUDYING if rec.get("in_progress") else GROUP_CERTIFICATIONS].append(cert_entry(rec))
        elif _LEGACY_IN_PROGRESS_RE.search(line):
            groups[GROUP_STUDYING].append(_LEGACY_IN_PROGRESS_RE.sub("", line) + " | In progress")
        else:
            groups[GROUP_CERTIFICATIONS].append(line)
    for line in training_lines:
        rec = by_training_line.get(line)
        if rec is not None:
            in_prog = rec.get("completion_status") in _IN_PROGRESS_TRAINING
            groups[GROUP_STUDYING if in_prog else GROUP_TRAINING].append(training_entry(rec))
        elif _LEGACY_IN_PROGRESS_RE.search(line):
            groups[GROUP_STUDYING].append(_LEGACY_IN_PROGRESS_RE.sub("", line) + " | In progress")
        else:
            groups[GROUP_TRAINING].append(line)
    return f"## {SECTION_HEADING}\n{render_groups(groups)}\n"
