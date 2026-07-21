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


def _clean(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    return text.strip()


def export(markdown_content: str, output_path: "str | Path") -> Path:
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    pdf = CVPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_margins(20, 18, 20)

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

        if re.match(r"^---+$", stripped):
            i += 1
            continue

        # # Name
        if stripped.startswith("# "):
            name = _clean(stripped[2:])
            pdf.set_font("Helvetica", "B", 22)
            pdf.set_text_color(*NAVY)
            pdf.cell(0, 10, name, ln=True, align="C")
            pdf.ln(1)
            i += 1

            # Contact line (next non-blank line containing | or @)
            while i < len(lines):
                next_line = lines[i].strip()
                if not next_line:
                    i += 1
                    continue
                if "|" in next_line or "@" in next_line:
                    parts = [p.strip() for p in next_line.split("|") if p.strip()]
                    contact_text = "  |  ".join(parts)
                    pdf.set_font("Helvetica", "", 8.5)
                    pdf.set_text_color(*MID)
                    pdf.cell(0, 5, contact_text, ln=True, align="C")
                    pdf.ln(3)
                    # Draw a thin rule under contact
                    pdf.set_draw_color(*BLUE)
                    pdf.set_line_width(0.4)
                    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
                    pdf.ln(5)
                    i += 1
                    break
                break
            continue

        # ## SECTION HEADING
        if stripped.startswith("## "):
            heading = _clean(stripped[3:]).upper()
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

        # ### Role | Company | Dates
        if stripped.startswith("### "):
            parts = [p.strip() for p in stripped[4:].split("|")]
            role = _clean(parts[0]) if parts else ""
            company = _clean(parts[1]) if len(parts) > 1 else ""
            dates = _clean(parts[2]) if len(parts) > 2 else ""

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
            text = _clean(stripped[2:])
            pdf.set_font("Helvetica", "", 9.5)
            pdf.set_text_color(*DARK)
            # Bullet dot
            x = pdf.get_x()
            y = pdf.get_y()
            pdf.set_fill_color(*BLUE)
            pdf.ellipse(x + 1, y + 2.5, 1.5, 1.5, "F")
            pdf.set_x(x + 5)
            pdf.multi_cell(0, 5, text)
            pdf.ln(0.5)
            i += 1
            continue

        # Plain text / paragraph
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*DARK)
        pdf.multi_cell(0, 5.5, _clean(stripped))
        pdf.ln(1)
        i += 1

    pdf.output(str(p))
    return p
