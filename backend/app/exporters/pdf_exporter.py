import re
from pathlib import Path
from fpdf import FPDF

NAVY = (12, 35, 64)
BLUE = (26, 64, 104)
DARK = (30, 30, 30)
MID = (74, 85, 104)
LIGHT = (160, 174, 192)


class CVPDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-13)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*LIGHT)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


_UNICODE_REPLACEMENTS = {
    "–": "-",    # en dash
    "—": "-",    # em dash
    "‘": "'",    # left single quote
    "’": "'",    # right single quote / apostrophe
    "“": '"',    # left double quote
    "”": '"',    # right double quote
    "…": "...",  # ellipsis
    "•": "-",    # bullet
    " ": " ",    # non-breaking space
}


def _sanitize_pdf_text(text: str) -> str:
    """The core PDF fonts (Helvetica etc.) only support Latin-1/WinAnsi. Map
    common "smart" typography to ASCII, then drop anything else that would
    otherwise crash the export."""
    for src, dst in _UNICODE_REPLACEMENTS.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _clean(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    return _sanitize_pdf_text(text.strip())


_BOLD_PLACEHOLDER = "\x00BOLD\x00"


def _prep_markdown(text: str) -> str:
    """Sanitize text for fpdf2's own markdown=True rendering, rather than
    stripping **bold**/*italic* to plain text — that was silently dropping all
    bold formatting (e.g. the "**Platforms & Tools:**" category labels),
    leaving them indistinguishable from surrounding body text. fpdf2 renders
    **bold** natively, but expects __italic__ (double underscore) rather than
    single *italic* for italics, so convert that marker before handing off."""
    text = text.strip()
    text = text.replace("**", _BOLD_PLACEHOLDER)
    text = re.sub(r"\*(.+?)\*", r"__\1__", text)
    text = text.replace(_BOLD_PLACEHOLDER, "**")
    return _sanitize_pdf_text(text)


def export(markdown_content: str, output_path: "str | Path") -> Path:
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    pdf = CVPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(20, 14, 20)

    lines = markdown_content.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        # Skip preamble before # Name
        if not any(l.startswith("# ") for l in lines[:i+1]) and not stripped.startswith("# "):
            i += 1
            continue

        if not stripped:
            pdf.ln(2)
            i += 1
            continue

        # Manual page-break marker — lets you force a break by hand wherever
        # the automatic keep-together logic still isn't quite right, rather
        # than fighting the heuristics for every possible layout.
        if stripped == "<!-- pagebreak -->":
            pdf.add_page()
            i += 1
            continue

        if re.match(r"^---+$", stripped):
            i += 1
            continue

        # # Name
        if stripped.startswith("# "):
            name = _clean(stripped[2:])
            pdf.set_font("Helvetica", "B", 20)
            pdf.set_text_color(*NAVY)
            pdf.cell(0, 9, name, ln=True, align="C")
            i += 1

            # Optional subtitle/descriptor line directly under the name (e.g.
            # "Senior Security Operations Analyst · Incident Response") — the
            # next non-blank line, but ONLY if it isn't itself the contact
            # line. Previously unrecognised here, so it fell through to the
            # generic paragraph renderer as small left-aligned body text
            # instead of a centered subtitle.
            while i < len(lines) and not lines[i].strip():
                i += 1
            if i < len(lines):
                maybe_subtitle = lines[i].strip()
                if maybe_subtitle and "|" not in maybe_subtitle and "@" not in maybe_subtitle:
                    pdf.set_font("Helvetica", "", 9.5)
                    pdf.set_text_color(*MID)
                    pdf.cell(0, 4.5, _clean(maybe_subtitle), ln=True, align="C")
                    i += 1

            # Contact line (next non-blank line containing | or @)
            while i < len(lines) and not lines[i].strip():
                i += 1
            if i < len(lines) and ("|" in lines[i].strip() or "@" in lines[i].strip()):
                next_line = lines[i].strip()
                parts = [p.strip() for p in next_line.split("|") if p.strip()]
                contact_text = _sanitize_pdf_text("  |  ".join(parts))
                pdf.set_font("Helvetica", "", 8.5)
                pdf.set_text_color(*MID)
                pdf.ln(0.5)
                pdf.cell(0, 5, contact_text, ln=True, align="C")
                pdf.ln(2)
                # Draw a thin rule under contact
                pdf.set_draw_color(*BLUE)
                pdf.set_line_width(0.4)
                pdf.line(20, pdf.get_y(), 190, pdf.get_y())
                pdf.set_line_width(0.2)
                pdf.ln(3)
                i += 1
            continue

        # ## SECTION HEADING
        if stripped.startswith("## "):
            heading = _clean(stripped[3:]).upper()
            # Keep the heading with at least the next line of content —
            # never leave it alone at the bottom of a page.
            if pdf.will_page_break(20):
                pdf.add_page()
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.set_text_color(*BLUE)
            pdf.cell(0, 5, heading, ln=True)
            # Bold underline rule
            pdf.set_draw_color(*BLUE)
            pdf.set_line_width(0.8)
            y = pdf.get_y()
            pdf.line(20, y, 190, y)
            pdf.set_line_width(0.2)
            pdf.ln(4)
            i += 1
            continue

        # ### Role | Company | Dates  (also accepts Role | Company | Location | Dates)
        if stripped.startswith("### "):
            parts = [p.strip() for p in stripped[4:].split("|")]
            role = _clean(parts[0]) if parts else ""
            # The last field is always dates; everything between role and dates
            # is company (and optionally location) — this keeps 3-field and
            # 4-field headers both working instead of silently dropping dates
            # when a location field is present (it was being read into the
            # "dates" slot and the real dates discarded entirely).
            dates = _clean(parts[-1]) if len(parts) > 1 else ""
            middle = [_clean(p) for p in parts[1:-1]] if len(parts) > 1 else []
            company = " · ".join(m for m in middle if m)

            # Keep role + company + dates together, and reserve space for the
            # paragraph immediately following too (if there is one) — a role
            # heading should never be left alone at the bottom of a page with
            # its description pushed to the next one. Bullet lists are still
            # allowed to split across a page for a long role; reserving space
            # for the whole list would waste too much room for shorter ones.
            reserve = 11
            look = i + 1
            while look < len(lines) and not lines[look].strip():
                look += 1
            if look < len(lines):
                next_stripped = lines[look].strip()
                if next_stripped and not next_stripped.startswith(("#", "-", "*")):
                    pdf.set_font("Helvetica", "", 10)
                    reserve += pdf.multi_cell(
                        0, 5.5, _prep_markdown(next_stripped),
                        dry_run=True, output="HEIGHT", markdown=True,
                    )
            if pdf.will_page_break(reserve):
                pdf.add_page()

            y_start = pdf.get_y()
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*DARK)
            pdf.cell(0, 5, role, ln=True)

            if company:
                pdf.set_font("Helvetica", "I", 9.5)
                pdf.set_text_color(*MID)
                pdf.cell(0, 4.5, company, ln=True)

            if dates:
                # Print dates right-aligned on same visual line as role
                # (Use a floating cell trick: go back up)
                pdf.set_font("Helvetica", "", 8.5)
                pdf.set_text_color(*LIGHT)
                current_y = pdf.get_y()
                pdf.set_y(y_start)
                pdf.cell(0, 5, dates, ln=True, align="R")
                pdf.set_y(current_y)

            pdf.ln(1)
            i += 1
            continue

        # Bullet
        if stripped.startswith("- ") or stripped.startswith("* "):
            text = _prep_markdown(stripped[2:])
            pdf.set_font("Helvetica", "", 9.5)
            pdf.set_text_color(*DARK)
            # Measure wrapped height at the SAME indent the text is actually drawn
            # at (x + 5) — measuring at the un-indented width underestimates the
            # line count, so a bullet lands the fits check but then wraps one
            # line further than expected and gets split by the auto page break
            # anyway, leaving a bare bullet dot behind on the old page. Must also
            # pass markdown=True here too, since bold text measures wider than
            # plain text of the same characters — a mismatch here would
            # reintroduce that same split-bullet bug for bold-containing lines.
            x0 = pdf.get_x()
            pdf.set_x(x0 + 5)
            needed = pdf.multi_cell(0, 5, text, dry_run=True, output="HEIGHT", markdown=True)
            pdf.set_x(x0)
            if pdf.will_page_break(needed):
                pdf.add_page()
            x = pdf.get_x()
            y = pdf.get_y()
            pdf.set_fill_color(*BLUE)
            pdf.ellipse(x + 1, y + 2.5, 1.5, 1.5, "F")
            pdf.set_x(x + 5)
            pdf.multi_cell(0, 5, text, markdown=True)
            pdf.ln(0.5)
            i += 1
            continue

        # Plain text / paragraph
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*DARK)
        md_text = _prep_markdown(stripped)
        needed = pdf.multi_cell(0, 5.5, md_text, dry_run=True, output="HEIGHT", markdown=True)
        if pdf.will_page_break(needed):
            pdf.add_page()
        pdf.multi_cell(0, 5.5, md_text, markdown=True)
        pdf.ln(1)
        i += 1

    pdf.output(str(p))
    return p
