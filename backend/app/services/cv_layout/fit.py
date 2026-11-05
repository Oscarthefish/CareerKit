"""Page fitting from the real rendered layout.

Page counts come from actually laying the CV out with the PDF renderer (the
same code that produces the export), not from character counts.

Never forces a target: font size and margins are fixed, nothing is clipped or
removed. The only automatic adjustment is closing up vertical spacing - at
most to the "compact" preset, which is itself a readable layout - and only to
pull back a final page that would otherwise hold a sliver of content (e.g. a
lone Community Involvement entry). Anything beyond that becomes a notice plus
review-only suggestions; the CV text itself is never edited here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import blocks as cvblocks
from .normalize import apply_section_options, normalize_structure, split_sections
from .options import PRESETS, SPACING_COMPACT, SPACING_STANDARD, LayoutOptions, Spacing, blend

SPARSE_LAST_PAGE = 0.25  # fraction of the usable page height


@dataclass
class FitResult:
    pages: int
    target_pages: int | None
    fits: bool
    spacing: str
    spacing_values: Spacing
    tightened: bool = False
    last_page_fill: float = 1.0
    compact_pages: int | None = None
    notice: str | None = None
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "pages": self.pages,
            "target_pages": self.target_pages,
            "fits": self.fits,
            "spacing": self.spacing,
            "tightened": self.tightened,
            "last_page_fill": round(self.last_page_fill, 2),
            "compact_pages": self.compact_pages,
            "notice": self.notice,
            "suggestions": self.suggestions,
        }


def prepare(md: str, options: LayoutOptions, certifications=None, training=None) -> str:
    """The exact markdown every renderer should lay out."""
    md = normalize_structure(md, certifications, training)
    return apply_section_options(md, options.section_order, options.hidden_sections)


def _measure(md: str, sp: Spacing) -> tuple[int, float]:
    from ...exporters.pdf_exporter import render  # local: exporter imports this package
    r = render(md, sp)
    return r.pdf.page_no(), r.last_page_fill


def choose_spacing(md: str, options: LayoutOptions) -> FitResult:
    base_name = options.spacing if options.spacing in PRESETS else SPACING_STANDARD
    base = PRESETS[base_name]
    pages, fill = _measure(md, base)
    result = FitResult(pages=pages, target_pages=options.target_pages, fits=True,
                       spacing=base_name, spacing_values=base, last_page_fill=fill)

    # A nearly-empty final page: close up spacing toward compact, stopping at
    # the first step that removes it.
    if pages > 1 and fill < SPARSE_LAST_PAGE and base_name == SPACING_STANDARD:
        for t in (0.25, 0.5, 0.75, 1.0):
            sp = blend(base, PRESETS[SPACING_COMPACT], t)
            p2, f2 = _measure(md, sp)
            if p2 < pages:
                result.pages, result.last_page_fill = p2, f2
                result.spacing_values, result.tightened = sp, True
                break

    target = options.target_pages
    if target:
        result.fits = result.pages <= target
        if not result.fits:
            if base_name == SPACING_STANDARD:
                result.compact_pages = _measure(md, PRESETS[SPACING_COMPACT])[0]
            result.notice = _notice(result, target)
            result.suggestions = suggest_cuts(md, result.spacing_values)
    return result


def _notice(r: FitResult, target: int) -> str:
    msg = (f"This CV lays out to {r.pages} pages against a {target}-page target. "
           "Nothing has been shrunk or removed to force it.")
    if r.compact_pages is not None:
        msg += (f" Compact spacing would make it {r.compact_pages} page{'s' if r.compact_pages != 1 else ''}"
                + ("." if r.compact_pages > target else " and meet the target."))
    if r.compact_pages is None or r.compact_pages > target:
        msg += " Reaching the target needs editorial cuts - see the suggestions below for review."
    return msg


# ---------------------------------------------------------------------------
# Review-only cut suggestions
# ---------------------------------------------------------------------------

_STOP = {"the", "and", "with", "for", "from", "into", "that", "this", "across", "where", "were", "was",
         "while", "their", "them", "then", "than", "also", "including", "rather"}


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 3 and w not in _STOP}


def _section_lines(md: str, sp: Spacing) -> dict[str, float]:
    from ...exporters.pdf_exporter import _Renderer
    r = _Renderer(sp)
    out: dict[str, float] = {}
    for b in cvblocks.parse(md):
        if b.kind in ("bullet", "entry", "para", "continuation") and b.section:
            out[b.section] = out.get(b.section, 0) + r.block_lines(b)
    return out


def _end_year(dates: str) -> int | None:
    if re.search(r"present|current", dates or "", re.IGNORECASE):
        return 9999
    years = re.findall(r"\d{4}", dates or "")
    return int(years[-1]) if years else None


def suggest_cuts(md: str, sp: Spacing) -> list[str]:
    """Concrete, reviewable suggestions, largest wins first. Never applied."""
    out: list[str] = []
    blocks = cvblocks.parse(md)
    lines = _section_lines(md, sp)

    # 1. Achievements that restate an experience bullet.
    exp = [b for b in blocks if b.kind == "bullet" and "experience" in b.section.lower()]
    ach = [b for b in blocks if b.kind == "bullet" and "achievement" in b.section.lower()]
    dupes = []
    for a in ach:
        aw = _words(a.text)
        for e in exp:
            ew = _words(e.text)
            if aw and ew and len(aw & ew) / min(len(aw), len(ew)) >= 0.6:
                dupes.append(a.text)
                break
    if dupes:
        listed = "; ".join(f'"{_short(d)}"' for d in dupes[:4])
        out.append(f"{len(dupes)} Selected Achievements bullet(s) largely repeat a Professional Experience "
                   f"bullet and could be kept in one place only: {listed}.")
    if len(ach) > 6:
        out.append(f"Selected Achievements has {len(ach)} bullets (~{int(lines.get(_sec(blocks, 'achievement'), 0))} "
                   "lines). Keeping the 5-6 most relevant to this role would save the most space.")

    # 2. Older roles with several bullets.
    roles, current = [], None
    for b in blocks:
        if b.kind == "role":
            current = [b, 0]
            roles.append(current)
        elif b.kind == "section":
            current = None
        elif b.kind == "bullet" and current is not None:
            current[1] += 1
    years = [y for y in (_end_year(r[0].parts[2]) for r in roles) if y and y != 9999]
    if roles and years:
        newest = max(years + [9999 if any(_end_year(r[0].parts[2]) == 9999 for r in roles) else 0])
        cutoff = (newest if newest != 9999 else max(years)) - 10
        old = [r for r in roles if (_end_year(r[0].parts[2]) or 9999) < cutoff and r[1] >= 2]
        if old:
            names = ", ".join(f"{r[0].parts[0]} ({r[1]} bullets)" for r in old)
            out.append(f"Roles ending more than ten years before your latest one could be cut to one line "
                       f"each, or moved to Additional Background: {names}.")

    # 3. Long profile / projects.
    for key, label, limit, aim in (("profile", "Professional Profile", 9, "6-8"), ("project", "Projects", 6, "3-4")):
        sec = _sec(blocks, key)
        if sec and lines.get(sec, 0) > limit:
            out.append(f"{label} runs to ~{int(lines[sec])} lines; a {aim} line version would help.")
    return out


def _sec(blocks, needle: str) -> str | None:
    return next((b.text for b in blocks if b.kind == "section" and needle in b.text.lower()), None)


def _short(text: str, n: int = 70) -> str:
    text = re.sub(r"\*\*|\*", "", text)
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def section_list(md: str) -> list[str]:
    return [h for h, _ in split_sections(md or "")[1]]
