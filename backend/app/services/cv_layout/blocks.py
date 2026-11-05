"""CareerKit CV markdown -> a flat list of typed blocks.

The PDF and DOCX exporters both render from this, so they agree on what is a
heading, a role, a sub-group, an entry or a paragraph. (The in-app preview,
frontend/src/components/CVRenderer.tsx, mirrors the same rules in TypeScript.)

    # Name
    optional subtitle line
    contact | line | with@email
    ## SECTION
    ### Role | Company [| Location] | Dates
    #### Sub-group label           (e.g. "Certifications")
    - bullet                       (an "entry" when directly under a sub-group)
      indented continuation line   (belongs to the bullet above)
    plain paragraph
    <!-- pagebreak -->
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Block:
    kind: str  # name | subtitle | contact | section | role | group | bullet | entry | continuation | para | pagebreak
    text: str = ""
    parts: list[str] = field(default_factory=list)  # contact items / role fields
    section: str = ""  # enclosing ## heading


def parse_role(line: str) -> tuple[str, str, str]:
    """### Role | Company [| Location] | Dates -> (role, organisation, dates).
    The last field is the date range; everything between is organisation
    (and location), joined - keeps 3- and 4-field headings working."""
    parts = [p.strip() for p in line.split("|")]
    if len(parts) == 1:
        return parts[0], "", ""
    if len(parts) == 2:
        # "Role | Company" with no dates, or "Role | Dates"
        if re.search(r"\d{4}|present|current", parts[1], re.IGNORECASE):
            return parts[0], "", parts[1]
        return parts[0], parts[1], ""
    return parts[0], ", ".join(p for p in parts[1:-1] if p), parts[-1]


def parse(md: str) -> list[Block]:
    blocks: list[Block] = []
    lines = (md or "").split("\n")
    i = 0
    # Skip any preamble before "# Name" (model chatter), but only if a name exists.
    if any(l.strip().startswith("# ") for l in lines):
        while i < len(lines) and not lines[i].strip().startswith("# "):
            i += 1

    section = ""
    in_group = False
    header_phase = False
    while i < len(lines):
        raw = lines[i].rstrip()
        s = raw.strip()
        i += 1
        if not s or re.match(r"^-{3,}$", s):
            continue
        if s == "<!-- pagebreak -->":
            blocks.append(Block("pagebreak", section=section))
            continue
        if s.startswith("# "):
            blocks.append(Block("name", s[2:].strip()))
            header_phase = True
            continue
        if header_phase and not s.startswith("#"):
            if "|" in s or "@" in s:
                blocks.append(Block("contact", s, parts=[p.strip() for p in s.split("|") if p.strip()]))
                header_phase = False
            elif not any(b.kind in ("subtitle", "contact") for b in blocks):
                blocks.append(Block("subtitle", s))
            else:
                header_phase = False
                blocks.append(Block("para", s, section=section))
            continue
        header_phase = False
        if s.startswith("#### "):
            blocks.append(Block("group", s[5:].strip(), section=section))
            in_group = True
            continue
        if s.startswith("### "):
            role, org, dates = parse_role(s[4:])
            blocks.append(Block("role", role, parts=[role, org, dates], section=section))
            in_group = False
            continue
        if s.startswith("## "):
            section = s[3:].strip()
            blocks.append(Block("section", section, section=section))
            in_group = False
            continue
        if s.startswith(("- ", "* ")):
            blocks.append(Block("entry" if in_group else "bullet", s[2:].strip(), section=section))
            continue
        if raw[:1] in (" ", "\t") and blocks and blocks[-1].kind in ("bullet", "entry", "continuation"):
            blocks.append(Block("continuation", s, section=section))
            continue
        blocks.append(Block("para", s, section=section))
    return blocks
