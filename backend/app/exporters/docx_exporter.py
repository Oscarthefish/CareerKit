"""CV / document DOCX export.

Same structure and spacing rules as the PDF exporter (services/cv_layout):
single column, A4, 17 mm side margins, 10.5 pt left-aligned body text, no
tables or text boxes (role dates sit on a right-aligned tab stop, not in a
table cell), so reading order and text extraction stay linear.

Word does its own pagination, so instead of measuring, pagination is
expressed as paragraph properties Word honours: headings, role lines and
sub-group labels "keep with next"; every paragraph has widow/orphan control;
nothing larger is forced to keep together. Blank markdown lines no longer
become empty paragraphs - spacing comes from paragraph spacing only.
"""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

from ..services.cv_layout import blocks as cvblocks
from ..services.cv_layout.options import LayoutOptions, Spacing

NAVY = RGBColor(0x0C, 0x23, 0x40)
BLUE = RGBColor(0x1A, 0x40, 0x68)
DARK = RGBColor(0x1E, 0x1E, 0x1E)
MID = RGBColor(0x4A, 0x55, 0x68)

FONT = "Calibri"
BODY_PT = 10.5
PAGE_W_MM, MARGIN_X_MM = 210, 17
TEXT_W_MM = PAGE_W_MM - 2 * MARGIN_X_MM
HANG_MM = 4.5


def _mm_to_pt(mm: float) -> Pt:
    return Pt(mm * 72 / 25.4)


def _fmt(para, sp: Spacing, before: float = 0.0, after: float = 0.0, keep_next: bool = False):
    pf = para.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf.space_before = _mm_to_pt(before)
    pf.space_after = _mm_to_pt(after)
    pf.line_spacing = _mm_to_pt(sp.line)
    pf.widow_control = True
    pf.keep_with_next = keep_next
    return para


def _run(para, text: str, bold=False, italic=False, size=BODY_PT, color=DARK):
    r = para.add_run(text)
    r.bold, r.italic = bold, italic
    r.font.size = Pt(size)
    r.font.name = FONT
    r.font.color.rgb = color
    return r


def _add_inline(para, text: str, size=BODY_PT, color=DARK, base_bold=False):
    """**bold** / *italic* markdown -> runs."""
    pos = 0
    for m in re.finditer(r"\*\*(.+?)\*\*|\*(.+?)\*", text):
        if m.start() > pos:
            _run(para, text[pos:m.start()], bold=base_bold, size=size, color=color)
        if m.group(1) is not None:
            _run(para, m.group(1), bold=True, size=size, color=color)
        else:
            _run(para, m.group(2), italic=True, bold=base_bold, size=size, color=color)
        pos = m.end()
    if pos < len(text):
        _run(para, text[pos:], bold=base_bold, size=size, color=color)


def _bottom_border(para, color="96ACC8", size=6):
    p_pr = para._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    for k, v in (("w:val", "single"), ("w:sz", str(size)), ("w:space", "1"), ("w:color", color)):
        bottom.set(qn(k), v)
    borders.append(bottom)
    p_pr.append(borders)


def _page_number_footer(section):
    para = section.footer.paragraphs[0]
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def field(code):
        r = para.add_run()
        r.font.size = Pt(8)
        for tag, attr in (("w:fldChar", "begin"), ("w:instrText", code), ("w:fldChar", "end")):
            el = OxmlElement(tag)
            if tag == "w:instrText":
                el.set(qn("xml:space"), "preserve")
                el.text = code
            else:
                el.set(qn("w:fldCharType"), attr)
            r._r.append(el)

    _run(para, "Page ", size=8, color=MID)
    field("PAGE")
    _run(para, " of ", size=8, color=MID)
    field("NUMPAGES")


def export(markdown_content: str, output_path: str | Path, options: LayoutOptions | None = None,
           spacing: Spacing | None = None) -> Path:
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    sp = spacing or (options or LayoutOptions()).spacing_values

    doc = Document()
    for section in doc.sections:
        section.page_width, section.page_height = Mm(210), Mm(297)
        section.top_margin, section.bottom_margin = Mm(15), Mm(16)
        section.left_margin = section.right_margin = Mm(MARGIN_X_MM)
        section.footer_distance = Mm(8)
        _page_number_footer(section)

    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(BODY_PT)
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

    blocks = cvblocks.parse(markdown_content)
    from .pdf_exporter import letter_spacing
    sp = letter_spacing(blocks, sp)
    for j, b in enumerate(blocks):
        prev = blocks[j - 1].kind if j else ""
        if b.kind == "pagebreak":
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        elif b.kind == "name":
            para = _fmt(doc.add_paragraph(), sp, after=1, keep_next=True)
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _run(para, _strip(b.text), bold=True, size=18, color=NAVY)
        elif b.kind == "subtitle":
            para = _fmt(doc.add_paragraph(), sp, keep_next=True)
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _run(para, _strip(b.text), size=10.5, color=MID)
        elif b.kind == "contact":
            para = _fmt(doc.add_paragraph(), sp, after=2)
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _run(para, "  |  ".join(b.parts), size=9.5, color=MID)
            _bottom_border(para, color="1A4068", size=8)
        elif b.kind == "section":
            para = _fmt(doc.add_paragraph(), sp, before=sp.section_before, after=sp.section_after, keep_next=True)
            _run(para, _strip(b.text).upper(), bold=True, size=10.5, color=NAVY)
            _bottom_border(para)
        elif b.kind == "role":
            role, org, dates = b.parts
            para = _fmt(doc.add_paragraph(), sp, before=0 if prev == "section" else sp.role_before,
                        after=0.6, keep_next=True)
            para.paragraph_format.tab_stops.add_tab_stop(Mm(TEXT_W_MM), WD_TAB_ALIGNMENT.RIGHT)
            _add_inline(para, role, base_bold=True)
            if org:
                _run(para, f" — {_strip(org)}")
            if dates:
                _run(para, "\t" + _strip(dates), size=9.5, color=MID)
        elif b.kind == "group":
            para = _fmt(doc.add_paragraph(), sp, before=0 if prev == "section" else sp.group_before,
                        keep_next=True)
            _run(para, _strip(b.text), bold=True, size=10, color=BLUE)
        elif b.kind == "entry":
            para = _fmt(doc.add_paragraph(), sp, after=sp.bullet_after)
            para.paragraph_format.left_indent = Mm(HANG_MM)
            para.paragraph_format.first_line_indent = Mm(-HANG_MM)
            _add_inline(para, b.text)
        elif b.kind == "bullet":
            para = _fmt(doc.add_paragraph(style="List Bullet"), sp, after=sp.bullet_after)
            _add_inline(para, b.text)
        elif b.kind == "continuation":
            para = _fmt(doc.add_paragraph(), sp, after=sp.bullet_after)
            para.paragraph_format.left_indent = Mm(6.35)
            _add_inline(para, b.text)
        elif b.kind == "para":
            para = _fmt(doc.add_paragraph(), sp, after=sp.paragraph_after)
            _add_inline(para, b.text)

    doc.save(str(p))
    return p


def _strip(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*|\*(.+?)\*", lambda m: m.group(1) or m.group(2), text or "").strip()
