"""CV / document PDF export.

Layout rules (shared with the DOCX exporter and the in-app preview through
services/cv_layout):
- Single column, A4, 17 mm side margins, 15 mm top, body text ends 18 mm from
  the bottom so the page number never collides with content.
- 10.5 pt Helvetica body text, left-aligned (fpdf2's multi_cell defaults to
  *justified*, which is what produced the stretched word spacing before).
- No tables, text boxes or images - plain text drawn in reading order, so it
  stays selectable and extracts top-to-bottom.
- Pagination from measured text, not character counts:
  * a section heading always lands with the start of its first entry;
  * a role heading lands with its first line of content;
  * a sub-group label ("Certifications") lands with its first entry;
  * a paragraph or bullet only splits across pages when at least two lines
    stay on each side, otherwise it moves whole;
  * nothing larger (a section, a whole role) is forced to stay together.
"""
from __future__ import annotations

import dataclasses
import re
from pathlib import Path

from fpdf import FPDF

from ..services.cv_layout import blocks as cvblocks
from ..services.cv_layout.options import LayoutOptions, Spacing

NAVY = (12, 35, 64)
BLUE = (26, 64, 104)
RULE = (150, 172, 200)
DARK = (30, 30, 30)
MID = (74, 85, 104)
LIGHT = (130, 140, 155)

PAGE_W = 210.0
MARGIN_X = 17.0
MARGIN_TOP = 15.0
MARGIN_BOTTOM = 18.0
TEXT_W = PAGE_W - 2 * MARGIN_X

BODY_PT = 10.5
ROLE_PT = 10.5
SECTION_PT = 10.5
GROUP_PT = 10.0
DATE_PT = 9.5
NAME_PT = 18
CONTACT_PT = 9.5
BULLET_INDENT = 4.5
ENTRY_HANG = 4.5
MIN_SPLIT_LINES = 2


class CVPDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-11)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*LIGHT)
        self.cell(0, 5, f"Page {self.page_no()} of {{nb}}", align="C")


# Windows-1252 covers en/em dashes, curly quotes, bullets and ellipses, so
# those are kept as typed; anything else gets a plain equivalent.
_FALLBACKS = {
    "→": "->", "←": "<-", "≥": ">=", "≤": "<=", "≈": "~",
    "≡": "=", "✓": "", "✔": "", " ": " ", "‑": "-", "−": "-",
    "​": "", " ": " ", " ": " ",
}


def _sanitize_pdf_text(text: str) -> str:
    for src, dst in _FALLBACKS.items():
        text = text.replace(src, dst)
    return text.encode("cp1252", errors="replace").decode("cp1252")


def _clean(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text)
    return _sanitize_pdf_text(text.strip())


_BOLD = "\x00B\x00"


def _prep_markdown(text: str) -> str:
    """Prepare text for fpdf2's markdown=True rendering: **bold** is native;
    *italic* must become __italic__; a literal "--" would toggle underline,
    so it becomes an en dash."""
    text = text.strip().replace("**", _BOLD)
    text = text.replace("--", "–")
    text = re.sub(r"\*(.+?)\*", r"__\1__", text)
    return _sanitize_pdf_text(text.replace(_BOLD, "**"))


class _Renderer:
    def __init__(self, spacing: Spacing):
        self.sp = spacing
        pdf = CVPDF(orientation="P", unit="mm", format="A4")
        pdf.core_fonts_encoding = "windows-1252"
        pdf.set_margins(MARGIN_X, MARGIN_TOP, MARGIN_X)
        pdf.set_auto_page_break(auto=True, margin=MARGIN_BOTTOM)
        pdf.add_page()
        self.pdf = pdf

    # -- measuring -------------------------------------------------------
    def _remaining(self) -> float:
        return self.pdf.page_break_trigger - self.pdf.get_y()

    def _at_page_top(self) -> bool:
        return self.pdf.get_y() <= MARGIN_TOP + 0.5

    def _lines(self, text: str, width: float, size: float, style: str = "") -> int:
        self.pdf.set_font("Helvetica", style, size)
        return len(self.pdf.multi_cell(width, self.sp.line, _prep_markdown(text), dry_run=True,
                                       output="LINES", markdown=True, align="L"))

    def _wrap_hanging(self, text: str, size: float) -> list[str]:
        """Word-wrap for a hanging indent: first line full width, the rest
        indented by ENTRY_HANG."""
        self.pdf.set_font("Helvetica", "", size)
        words, lines, cur = _clean(text).split(" "), [], ""
        for w in words:
            limit = TEXT_W if not lines else TEXT_W - ENTRY_HANG
            trial = f"{cur} {w}" if cur else w
            if cur and self.pdf.get_string_width(trial) > limit:
                lines.append(cur)
                cur = w
            else:
                cur = trial
        if cur:
            lines.append(cur)
        return lines

    def block_lines(self, b: cvblocks.Block) -> int:
        if b.kind == "bullet":
            return self._lines(b.text, TEXT_W - BULLET_INDENT, BODY_PT)
        if b.kind == "continuation":
            return self._lines(b.text, TEXT_W - BULLET_INDENT, BODY_PT)
        if b.kind == "entry":
            return len(self._wrap_hanging(b.text, BODY_PT))
        if b.kind == "para":
            return self._lines(b.text, TEXT_W, BODY_PT)
        return 1

    def role_height(self, b: cvblocks.Block) -> float:
        role, org, dates = b.parts
        return self.sp.role_before + self._role_lines(role, org, dates) * self.sp.line

    def _role_left(self, role: str, org: str) -> str:
        return f"**{role}**" + (f" — {org}" if org else "")

    def _date_width(self, dates: str) -> float:
        if not dates:
            return 0.0
        self.pdf.set_font("Helvetica", "", DATE_PT)
        return self.pdf.get_string_width(_clean(dates)) + 4

    def _role_lines(self, role, org, dates) -> int:
        return self._lines(self._role_left(role, org), TEXT_W - self._date_width(dates), ROLE_PT)

    def first_content_height(self, blocks: list, j: int) -> float:
        """Height that must fit along with a heading: the role/group header
        that follows plus the opening lines of its content."""
        if j >= len(blocks):
            return 0.0
        b = blocks[j]
        if b.kind == "role":
            return self.role_height(b) + self.first_content_height(blocks, j + 1)
        if b.kind == "group":
            return self.sp.group_before + self.sp.line + self.first_content_height(blocks, j + 1)
        if b.kind in ("bullet", "entry", "para", "continuation"):
            n = self.block_lines(b)
            keep = n if n <= 3 else MIN_SPLIT_LINES
            return keep * self.sp.line
        return 0.0

    def _ensure(self, needed: float):
        if not self._at_page_top() and needed > self._remaining():
            self.pdf.add_page()

    def _place_flow(self, n_lines: int):
        """Before a splittable text block: page-break first unless it fits,
        or unless at least two lines stay on each side of the split."""
        if self._at_page_top():
            return
        fit = int(self._remaining() // self.sp.line)
        if fit >= n_lines:
            return
        if n_lines > 3 and fit >= MIN_SPLIT_LINES and n_lines - fit >= MIN_SPLIT_LINES:
            return
        self.pdf.add_page()

    # -- drawing ---------------------------------------------------------
    def render(self, blocks: list[cvblocks.Block]):
        pdf, sp = self.pdf, self.sp
        for j, b in enumerate(blocks):
            nxt_h = lambda: self.first_content_height(blocks, j + 1)  # noqa: E731

            if b.kind == "pagebreak":
                pdf.add_page()
            elif b.kind == "name":
                pdf.set_font("Helvetica", "B", NAME_PT)
                pdf.set_text_color(*NAVY)
                pdf.cell(0, 8.5, _clean(b.text), new_x="LMARGIN", new_y="NEXT", align="C")
            elif b.kind == "subtitle":
                pdf.set_font("Helvetica", "", 10.5)
                pdf.set_text_color(*MID)
                pdf.multi_cell(0, 5, _clean(b.text), align="C", new_x="LMARGIN", new_y="NEXT")
            elif b.kind == "contact":
                pdf.ln(0.5)
                pdf.set_font("Helvetica", "", CONTACT_PT)
                pdf.set_text_color(*MID)
                pdf.multi_cell(0, 4.6, _sanitize_pdf_text("  |  ".join(b.parts)), align="C",
                               new_x="LMARGIN", new_y="NEXT")
                pdf.ln(1.5)
                pdf.set_draw_color(*BLUE)
                pdf.set_line_width(0.35)
                pdf.line(MARGIN_X, pdf.get_y(), PAGE_W - MARGIN_X, pdf.get_y())
                pdf.ln(0.5)
            elif b.kind == "section":
                head_h = sp.section_before + 6 + sp.section_after
                self._ensure(head_h + nxt_h())
                if not self._at_page_top():
                    pdf.ln(sp.section_before)
                pdf.set_font("Helvetica", "B", SECTION_PT)
                pdf.set_text_color(*NAVY)
                pdf.cell(0, 5.5, _clean(b.text).upper(), new_x="LMARGIN", new_y="NEXT")
                pdf.set_draw_color(*RULE)
                pdf.set_line_width(0.3)
                pdf.line(MARGIN_X, pdf.get_y() + 0.3, PAGE_W - MARGIN_X, pdf.get_y() + 0.3)
                pdf.ln(0.3 + sp.section_after)
            elif b.kind == "role":
                role, org, dates = b.parts
                self._ensure(self.role_height(b) + nxt_h())
                if not self._at_page_top() and blocks[j - 1].kind != "section":
                    pdf.ln(sp.role_before)
                date_w = self._date_width(dates)
                y0 = pdf.get_y()
                pdf.set_font("Helvetica", "", ROLE_PT)
                pdf.set_text_color(*DARK)
                pdf.multi_cell(TEXT_W - date_w, sp.line, _prep_markdown(self._role_left(role, org)),
                               markdown=True, align="L", new_x="LMARGIN", new_y="NEXT")
                y1 = pdf.get_y()
                if dates:
                    pdf.set_xy(PAGE_W - MARGIN_X - date_w, y0)
                    pdf.set_font("Helvetica", "", DATE_PT)
                    pdf.set_text_color(*MID)
                    pdf.cell(date_w, sp.line, _clean(dates), align="R")
                    pdf.set_xy(MARGIN_X, y1)
                pdf.ln(0.6)
            elif b.kind == "group":
                self._ensure(sp.group_before + sp.line + nxt_h())
                if not self._at_page_top() and blocks[j - 1].kind != "section":
                    pdf.ln(sp.group_before)
                pdf.set_font("Helvetica", "B", GROUP_PT)
                pdf.set_text_color(*BLUE)
                pdf.cell(0, sp.line, _clean(b.text), new_x="LMARGIN", new_y="NEXT")
            elif b.kind == "entry":
                lines = self._wrap_hanging(b.text, BODY_PT)
                self._place_flow(len(lines))
                pdf.set_font("Helvetica", "", BODY_PT)
                pdf.set_text_color(*DARK)
                for k, line in enumerate(lines):
                    pdf.set_x(MARGIN_X + (ENTRY_HANG if k else 0))
                    pdf.cell(0, sp.line, line, new_x="LMARGIN", new_y="NEXT")
                pdf.ln(sp.bullet_after)
            elif b.kind in ("bullet", "continuation"):
                n = self.block_lines(b)
                self._place_flow(n)
                pdf.set_font("Helvetica", "", BODY_PT)
                pdf.set_text_color(*DARK)
                if b.kind == "bullet":
                    pdf.set_fill_color(*BLUE)
                    pdf.ellipse(MARGIN_X + 0.6, pdf.get_y() + sp.line / 2 - 0.65, 1.3, 1.3, "F")
                pdf.set_x(MARGIN_X + BULLET_INDENT)
                pdf.multi_cell(TEXT_W - BULLET_INDENT, sp.line, _prep_markdown(b.text),
                               markdown=True, align="L", new_x="LMARGIN", new_y="NEXT")
                pdf.ln(sp.bullet_after)
            elif b.kind == "para":
                self._place_flow(self.block_lines(b))
                pdf.set_font("Helvetica", "", BODY_PT)
                pdf.set_text_color(*DARK)
                pdf.multi_cell(TEXT_W, sp.line, _prep_markdown(b.text), markdown=True, align="L",
                               new_x="LMARGIN", new_y="NEXT")
                pdf.ln(sp.paragraph_after)

    @property
    def last_page_fill(self) -> float:
        usable = self.pdf.page_break_trigger - MARGIN_TOP
        return max(0.0, min(1.0, (self.pdf.get_y() - MARGIN_TOP) / usable))


def letter_spacing(blocks: list, spacing: Spacing) -> Spacing:
    """A document with no ## sections (a cover letter, notes) is prose: give
    paragraphs a full blank line between them instead of CV entry spacing."""
    if any(b.kind == "section" for b in blocks):
        return spacing
    return dataclasses.replace(spacing, paragraph_after=max(spacing.paragraph_after, 4.0))


def render(markdown_content: str, spacing: Spacing) -> _Renderer:
    blocks = cvblocks.parse(markdown_content)
    r = _Renderer(letter_spacing(blocks, spacing))
    r.render(blocks)
    return r


def export(markdown_content: str, output_path: "str | Path", options: LayoutOptions | None = None,
           spacing: Spacing | None = None) -> Path:
    """spacing overrides options' preset (fit.py passes a measured choice)."""
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    sp = spacing or (options or LayoutOptions()).spacing_values
    render(markdown_content, sp).pdf.output(str(p))
    return p
