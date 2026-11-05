"""Structural normalisation of CV markdown.

normalize_structure() is idempotent and content-preserving: it restructures
Certifications & Training into grouped entries and writes ISO role dates
("2022-01 - 2026-08") as "Jan 2022 – Aug 2026". It never drops text. It runs
on generation, on read (so CVs saved before this existed display correctly)
and on export.

apply_section_options() applies the user's section order / inclusion choice
for rendering only - it is never written back to the stored CV, so hiding a
section can't lose it.
"""
from __future__ import annotations

import re

from . import credentials

_SECTION_RE = re.compile(r"^## +(.+?)\s*$", re.MULTILINE)
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_ISO_MONTH_RE = re.compile(r"\b(\d{4})-(\d{2})\b")
_RANGE_SEP_RE = re.compile(r"\s+[-–—]\s+")

_CERT_HEADINGS = {"certifications", "certifications & training", "certifications and training",
                  "training and certifications", "training & certifications"}
_TRAINING_HEADINGS = {"professional training", "training"}


def split_sections(md: str) -> tuple[str, list[tuple[str, str]]]:
    """(preamble, [(heading, body), ...]) - body excludes the heading line and
    keeps its own trailing blank lines stripped."""
    matches = list(_SECTION_RE.finditer(md))
    if not matches:
        return md, []
    preamble = md[:matches[0].start()]
    sections = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        body = md[m.end():end].strip("\n")
        sections.append((m.group(1).strip(), body))
    return preamble, sections


def join_sections(preamble: str, sections: list[tuple[str, str]]) -> str:
    out = preamble.rstrip("\n")
    for heading, body in sections:
        out += f"\n\n## {heading}\n{body}".rstrip("\n")
    return out.lstrip("\n") + "\n"


def _format_month(m: re.Match) -> str:
    idx = int(m.group(2)) - 1
    return f"{_MONTHS[idx]} {m.group(1)}" if 0 <= idx < 12 else m.group(0)


def _format_role_heading(line: str) -> str:
    parts = [p.strip() for p in line[4:].split("|")]
    if len(parts) < 2:
        return line
    dates = _ISO_MONTH_RE.sub(_format_month, parts[-1])
    dates = _RANGE_SEP_RE.sub(" – ", dates)
    parts[-1] = dates
    return "### " + " | ".join(parts)


def _restructure_credentials(sections, certifications, training):
    idx = [i for i, (h, _) in enumerate(sections) if h.lower() in _CERT_HEADINGS]
    tidx = [i for i, (h, _) in enumerate(sections) if h.lower() in _TRAINING_HEADINGS]
    if not idx and not tidx:
        return sections
    first = min(idx + tidx)
    cert_body = "\n".join(sections[i][1] for i in idx)
    training_body = "\n".join(sections[i][1] for i in tidx)
    if "#### " in cert_body and not training_body:
        return sections  # already structured
    built = credentials.convert_legacy(cert_body, training_body, certifications, training)
    if not built:
        return sections
    heading, body = built.split("\n", 1)
    new = []
    for i, sec in enumerate(sections):
        if i == first:
            new.append((heading[3:].strip(), body.strip("\n")))
        elif i in idx or i in tidx:
            continue
        else:
            new.append(sec)
    return new


def normalize_structure(md: str, certifications: list[dict] | None = None,
                        training: list[dict] | None = None) -> str:
    if not md or not md.strip():
        return md
    lines = [(_format_role_heading(l) if l.startswith("### ") else l) for l in md.split("\n")]
    md = "\n".join(lines)
    preamble, sections = split_sections(md)
    if not sections:
        return md
    sections = _restructure_credentials(sections, certifications, training)
    return join_sections(preamble, sections)


def replace_credentials_section(md: str, certifications: list[dict], training: list[dict]) -> str:
    """Generation-time safety net: force the section to the structured
    records, whatever the model wrote (it has repeatedly mistyped names)."""
    built = credentials.build_section(certifications, training)
    preamble, sections = split_sections(md)
    keep = [s for s in sections if s[0].lower() not in _CERT_HEADINGS | _TRAINING_HEADINGS]
    if not built:
        return join_sections(preamble, keep) if len(keep) != len(sections) else md
    heading, body = built.split("\n", 1)
    entry = (heading[3:].strip(), body.strip("\n"))
    positions = [i for i, s in enumerate(sections) if s[0].lower() in _CERT_HEADINGS | _TRAINING_HEADINGS]
    if positions:
        # Same place as before - count kept sections that came before it.
        insert_at = sum(1 for s in sections[:positions[0]] if s in keep)
    else:
        # Before Education / Additional Background / Community, else at end.
        tail = {"education", "additional background", "community involvement"}
        insert_at = next((i for i, s in enumerate(keep) if s[0].lower() in tail), len(keep))
    keep.insert(insert_at, entry)
    return join_sections(preamble, keep)


def section_names(md: str) -> list[str]:
    return [h for h, _ in split_sections(md or "")[1]]


def apply_section_options(md: str, order: list[str] | None, hidden: list[str] | None) -> str:
    if not order and not hidden:
        return md
    preamble, sections = split_sections(md)
    if not sections:
        return md
    hidden_l = {h.lower() for h in hidden or []}
    rank = {h.lower(): i for i, h in enumerate(order or [])}
    visible = [s for s in sections if s[0].lower() not in hidden_l]
    # Stable: listed sections first in the given order, unlisted keep theirs.
    visible = sorted(enumerate(visible), key=lambda p: (rank.get(p[1][0].lower(), len(rank)), p[0]))
    return join_sections(preamble, [s for _, s in visible])
