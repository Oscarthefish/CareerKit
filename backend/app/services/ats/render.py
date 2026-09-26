"""'View what an ATS sees': a simplified, structured plain-text rendering of
the CV, built from CareerKit's own markdown parsing. This is an approximation
based on CareerKit's structured content, not a simulation of any specific
real-world ATS parser - CareerKit cannot inspect how a third-party ATS
actually behaves, so it doesn't claim to."""
import re

from .sections import parse


def _strip_markdown(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    return text.strip()


def render_ats_view(markdown: str) -> str:
    parsed = parse(markdown or "")
    lines: list[str] = []

    if parsed.name:
        lines.append(parsed.name.upper())
    if parsed.contact_line:
        lines.append(parsed.contact_line)
    lines.append("")

    for raw in parsed.raw_lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("# ") or line == parsed.contact_line:
            continue  # name/contact already rendered above
        if line.startswith("## "):
            lines.append("")
            lines.append(line[3:].strip().upper())
            lines.append("")
            continue
        if line.startswith("### "):
            lines.append(_strip_markdown(line[4:]))
            continue
        if line.startswith("- ") or line.startswith("* "):
            lines.append(_strip_markdown(line[2:]))
            continue
        if re.match(r"^-{3,}$", line) or line == "<!-- pagebreak -->":
            continue
        lines.append(_strip_markdown(line))

    return "\n".join(lines).strip() + "\n"
