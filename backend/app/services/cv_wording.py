"""Deterministic wording fixes for generated CVs that depend on CV structure.

tone_down (ai/tone.py) handles phrase-level inflation anywhere in a text.
These need to know where they are in the CV:

- Past roles read in the past tense. Bullets for a role with an end date that
  open with an "-ing" verb ("Investigating phishing...") become past tense
  ("Investigated phishing..."). Only verbs in the explicit table are changed.
- No current employer, no "our". When the candidate has no current role, "our
  security operations" / "reduce our risk" read as if they still work there;
  the possessive is dropped ("improve security operations", "reduce risk").
- Say a thing once. The local model repeats near-identical sentences across
  PROFESSIONAL PROFILE and CORE CAPABILITIES ("I have experience working with a
  wide range of security tools..., including SIEM, Splunk ES, EDR and Cortex
  XDR" three times). A sentence that restates an earlier one is dropped,
  never leaving a capability line empty.
"""
from __future__ import annotations

import re

# Opening "-ing" verbs seen in (or plausible for) CV bullets -> past tense.
PAST_TENSE = {
    "acting": "acted", "administering": "administered", "analysing": "analysed", "analyzing": "analysed",
    "building": "built", "conducting": "conducted", "configuring": "configured", "contributing": "contributed",
    "coordinating": "coordinated", "creating": "created", "delivering": "delivered", "deploying": "deployed",
    "designing": "designed", "developing": "developed", "documenting": "documented", "driving": "drove",
    "escalating": "escalated", "establishing": "established", "handling": "handled", "helping": "helped",
    "hunting": "hunted", "identifying": "identified", "implementing": "implemented", "improving": "improved",
    "investigating": "investigated", "leading": "led", "maintaining": "maintained", "managing": "managed",
    "mentoring": "mentored", "monitoring": "monitored", "onboarding": "onboarded", "owning": "owned",
    "participating": "participated", "performing": "performed", "providing": "provided", "recruiting": "recruited",
    "reporting": "reported", "responding": "responded", "reviewing": "reviewed", "running": "ran",
    "supervising": "supervised", "supporting": "supported", "triaging": "triaged", "tuning": "tuned",
    "using": "used", "working": "worked", "writing": "wrote",
}

_SECTION_RE = re.compile(r"^## (.+?)\s*$", re.MULTILINE)
_ROLE_RE = re.compile(r"^### .*$", re.MULTILINE)
_OPENING_VERB_RE = re.compile(r"^(\s*-\s+)([A-Za-z]+ing)\b")
_OUR_RE = re.compile(r"\b([Oo])ur\s+([A-Za-z])")
_STOP = {"with", "from", "that", "this", "have", "into", "including", "across", "using", "and", "the", "for",
         "which", "where", "their", "them", "they", "been", "also", "such", "well", "both"}


def _sections(content: str) -> list[tuple[str, int, int]]:
    """[(heading, body_start, body_end)] for each "## " section."""
    marks = list(_SECTION_RE.finditer(content))
    return [(m.group(1).strip().upper(), m.end(), marks[i + 1].start() if i + 1 < len(marks) else len(content))
            for i, m in enumerate(marks)]


def _replace_section(content: str, name: str, fn) -> str:
    for heading, start, end in _sections(content):
        if heading == name:
            return content[:start] + fn(content[start:end]) + content[end:]
    return content


# ---------------------------------------------------------------------------
# Past roles in the past tense
# ---------------------------------------------------------------------------

def _past_tense_line(line: str) -> str:
    m = _OPENING_VERB_RE.match(line)
    if not m:
        return line
    past = PAST_TENSE.get(m.group(2).lower())
    if not past:
        return line
    past = past[:1].upper() + past[1:] if m.group(2)[:1].isupper() else past
    return m.group(1) + past + line[m.end():]


def _role_is_past(heading: str) -> bool:
    dates = heading.split("|")[-1] if "|" in heading else ""
    return bool(dates.strip()) and not re.search(r"present|current|now", dates, re.IGNORECASE)


def past_tense_for_past_roles(content: str) -> str:
    def fix(body: str) -> str:
        out, past = [], False
        for line in body.split("\n"):
            if line.startswith("### "):
                past = _role_is_past(line)
            elif past:
                line = _past_tense_line(line)
            out.append(line)
        return "\n".join(out)
    return _replace_section(content, "PROFESSIONAL EXPERIENCE", fix)


# ---------------------------------------------------------------------------
# No "our" without a current employer
# ---------------------------------------------------------------------------

def strip_our_without_current_role(content: str, has_current_role: bool) -> str:
    """Drop "our" before a noun when there is no current employer:
    "improve our security operations" -> "improve security operations",
    "Our team" -> "Team". The name/contact preamble is left alone."""
    if has_current_role:
        return content
    sections = _sections(content)
    if not sections:
        return content
    start = sections[0][1]
    body = _OUR_RE.sub(lambda m: m.group(2).upper() if m.group(1) == "O" else m.group(2), content[start:])
    return content[:start] + body


# ---------------------------------------------------------------------------
# Say a thing once (PROFESSIONAL PROFILE + CORE CAPABILITIES)
# ---------------------------------------------------------------------------

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
DUPLICATE_OVERLAP = 0.7
MIN_COMPARABLE_STEMS = 5


def _stems(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9/+-]+", text.lower())
    return {w[:5] for w in words if len(w) > 3 and w not in _STOP}


def _is_restatement(sentence: str, seen: list[set[str]]) -> bool:
    s = _stems(sentence)
    if len(s) < MIN_COMPARABLE_STEMS:
        return False
    for prior in seen:
        smaller = min(len(s), len(prior))
        if smaller >= MIN_COMPARABLE_STEMS and len(s & prior) / smaller >= DUPLICATE_OVERLAP:
            return True
    return False


def dedupe_profile_sentences(content: str) -> str:
    seen: list[set[str]] = []

    def fix(body: str) -> str:
        out = []
        for line in body.split("\n"):
            label = ""
            text = line
            m = re.match(r"^(\*\*[^*]+:\*\*\s*)(.*)$", line)
            if m:
                label, text = m.group(1), m.group(2)
            if not text.strip():
                out.append(line)
                continue
            kept = []
            for sentence in _SENTENCE_SPLIT.split(text.strip()):
                if _is_restatement(sentence, seen):
                    continue
                kept.append(sentence)
                seen.append(_stems(sentence))
            if not kept:
                # Never leave a labelled capability line (or paragraph) empty.
                first = _SENTENCE_SPLIT.split(text.strip())[0]
                kept = [first]
            out.append(label + " ".join(kept))
        return "\n".join(out)

    content = _replace_section(content, "PROFESSIONAL PROFILE", fix)
    return _replace_section(content, "CORE CAPABILITIES", fix)


def polish_cv_wording(content: str, has_current_role: bool) -> str:
    content = past_tense_for_past_roles(content)
    content = strip_our_without_current_role(content, has_current_role)
    return dedupe_profile_sentences(content)
