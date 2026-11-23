"""Tone down inflated self-description in generated CVs and letters.

The banned-phrase list tells the model not to write "expert-level", "highly
skilled" and so on, and forces a rewrite when it does - but a small local
model still slips them through now and then. This is the deterministic
backstop: a plain, factual register ("skilled", "experienced") instead of
superlatives the evidence can't back up.

It only rewrites the specific patterns below. "Expert" is only changed when
the candidate calls themselves one ("as a security operations expert", "an
expert in"), so role names like "subject matter expert" are left alone.
"""
import re

_INTENSIFIERS = r"(?:highly|extremely|exceptionally|incredibly|very|deeply|supremely|uniquely)"
_ADJECTIVES = r"(skilled|experienced|proficient|knowledgeable|accomplished|capable|competent|qualified)"

# "highly skilled" / "highly-skilled" -> "skilled"
_INTENSIFIED_RE = re.compile(rf"\b(?:(an?)\s+)?{_INTENSIFIERS}[- ]{_ADJECTIVES}\b", re.IGNORECASE)
# Modifiers removed outright: "(an) expert-level X" -> "(a/an) X",
# "a world-class team" -> "a team".
_REMOVABLE_RE = re.compile(
    r"\b(?:(an?)\s+)?(?:expert[- ]level|world[- ]class|best[- ]in[- ]class|unparalleled|unrivalled)\s+(\w+)",
    re.IGNORECASE,
)
_LEVEL_NOUNS = {"proficiency", "expertise", "mastery", "competence", "competency"}
# "deep/extensive/advanced/specialist expertise" -> "experience"
_EXPERTISE_RE = re.compile(r"\b(?:deep|extensive|advanced|specialist|unrivalled|unparalleled)\s+expertise\b", re.IGNORECASE)
# "(I am) an expert in X" -> "(I am) experienced in X"
_EXPERT_IN_RE = re.compile(r"\b(?:an\s+)?expert\s+(in|at|with)\b", re.IGNORECASE)
# "As a security operations expert" -> "As a security operations professional"
# (self-description only: "as"/"I am" + article + up to three words + expert).
_SELF_EXPERT_RE = re.compile(
    r"\b(as|i am|i'm)\s+(an?)\s+((?:[\w/&-]+\s+){0,3}?)expert\b(?!-|\s+(?:in|at|with)\b)", re.IGNORECASE)
# "My expertise spans..." -> "My experience spans...", "areas of expertise" -> "areas of experience"
_MY_EXPERTISE_RE = re.compile(r"\b(my|our)\s+expertise\b|\b(areas?)\s+of\s+expertise\b", re.IGNORECASE)
# "a wealth of experience" -> "broad experience"; "extensive experience" -> "experience"
_WEALTH_RE = re.compile(r"\ba\s+wealth\s+of\s+(\w+)", re.IGNORECASE)
_EXTENSIVE_RE = re.compile(r"\bextensive\s+(experience)\b", re.IGNORECASE)
# "...experience to the table" -> "...experience"
_TO_THE_TABLE_RE = re.compile(r"\s+to\s+the\s+table\b", re.IGNORECASE)


def _match_case(original: str, replacement: str) -> str:
    return replacement[:1].upper() + replacement[1:] if original[:1].isupper() else replacement


def _article_for(word_start: str) -> str:
    return "an" if word_start[:1].lower() in "aeiou" else "a"


def tone_down(text: str | None) -> str | None:
    if not text:
        return text

    def _drop_intensifier(m: re.Match) -> str:
        # "a highly experienced" -> "an experienced": the article must follow the new first word.
        article, adjective = m.group(1), m.group(2).lower()
        if article:
            return _match_case(article, _article_for(adjective)) + " " + adjective
        return _match_case(m.group(0), adjective)
    text = _INTENSIFIED_RE.sub(_drop_intensifier, text)

    def _remove_modifier(m: re.Match) -> str:
        article, nxt = m.group(1), m.group(2)
        if nxt.lower() in _LEVEL_NOUNS:
            # "I have expert-level proficiency in X" -> "I have experience in X"
            return _match_case(m.group(0), "experience")
        if article:
            return _match_case(article, _article_for(nxt)) + " " + nxt
        return _match_case(m.group(0), nxt)
    text = _REMOVABLE_RE.sub(_remove_modifier, text)

    text = _EXPERTISE_RE.sub(lambda m: _match_case(m.group(0), "experience"), text)
    def _self_expert(m: re.Match) -> str:
        lead, article, words = m.group(1), m.group(2), m.group(3)
        if "subject matter" in words.lower():
            return m.group(0)
        first = (words.split() or ["professional"])[0]
        return f"{lead} {_match_case(article, _article_for(first))} {words}professional"
    text = _SELF_EXPERT_RE.sub(_self_expert, text)
    text = _MY_EXPERTISE_RE.sub(
        lambda m: (f"{m.group(1)} " + _match_case(m.group(0)[len(m.group(1)) + 1:], "experience")) if m.group(1)
        else f"{m.group(2)} of experience", text)
    text = _WEALTH_RE.sub(lambda m: _match_case(m.group(0), f"broad {m.group(1)}"), text)
    text = _EXTENSIVE_RE.sub(lambda m: _match_case(m.group(0), m.group(1).lower()), text)
    text = _TO_THE_TABLE_RE.sub("", text)
    text = _EXPERT_IN_RE.sub(lambda m: _match_case(m.group(0), f"experienced {m.group(1).lower()}"
                                                   if m.group(1).lower() != "at" else "skilled at"), text)
    return text
