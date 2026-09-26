"""Conservative American -> British English post-processor.

This is a backstop for free-text model output. The primary defence is the
style directive in the system prompt (see ``ollama_provider``); this pass only
catches the common spellings a local model still slips through.

It deliberately stays small and word-list based. It does NOT apply a blanket
``-ize -> -ise`` rule (that breaks "seize", "size", "prize", ...) and it leaves
JSON-structured output alone so it cannot mangle quoted job-description text or
proper nouns.
"""
import re

# American -> British. Keys are matched case-insensitively on whole words;
# the original capitalisation of the first letter is preserved.
_WORD_MAP = {
    # -our
    "color": "colour", "colors": "colours", "colored": "coloured", "coloring": "colouring",
    "behavior": "behaviour", "behaviors": "behaviours", "behavioral": "behavioural",
    "favor": "favour", "favors": "favours", "favorable": "favourable", "favorite": "favourite",
    "honor": "honour", "honors": "honours", "honored": "honoured",
    "labor": "labour", "neighbor": "neighbour", "neighbors": "neighbours",
    "rumor": "rumour", "endeavor": "endeavour", "flavor": "flavour",
    # -re
    "center": "centre", "centers": "centres", "centered": "centred",
    "fiber": "fibre", "liter": "litre", "meter": "metre", "theater": "theatre",
    # -ce / -se
    "defense": "defence", "defenses": "defences", "offense": "offence",
    "license": "licence", "licenses": "licences", "pretense": "pretence",
    # -lling / doubled l
    "canceled": "cancelled", "canceling": "cancelling", "cancelation": "cancellation",
    "modeling": "modelling", "modeled": "modelled",
    "labeling": "labelling", "labeled": "labelled",
    "traveled": "travelled", "traveling": "travelling", "traveler": "traveller",
    "signaling": "signalling", "signaled": "signalled",
    "fulfill": "fulfil", "fulfillment": "fulfilment", "enrollment": "enrolment",
    "skillful": "skilful", "willful": "wilful",
    # -ize / -yze verbs (explicit list, plus their -ing/-ed/-ation forms below)
    "analyze": "analyse", "paralyze": "paralyse", "catalyze": "catalyse",
    "organize": "organise", "recognize": "recognise", "prioritize": "prioritise",
    "specialize": "specialise", "optimize": "optimise", "realize": "realise",
    "customize": "customise", "minimize": "minimise", "maximize": "maximise",
    "categorize": "categorise", "summarize": "summarise", "emphasize": "emphasise",
    "utilize": "utilise", "standardize": "standardise", "normalize": "normalise",
    "authorize": "authorise", "apologize": "apologise", "characterize": "characterise",
    "familiarize": "familiarise", "visualize": "visualise", "modernize": "modernise",
    "centralize": "centralise", "formalize": "formalise", "capitalize": "capitalise",
    "finalize": "finalise", "harmonize": "harmonise", "synchronize": "synchronise",
    "hypothesize": "hypothesise", "scrutinize": "scrutinise", "stabilize": "stabilise",
    "mobilize": "mobilise", "digitize": "digitise", "itemize": "itemise",
    "sanitize": "sanitise", "prioritized": "prioritised",
    # misc common
    "catalog": "catalogue", "dialog": "dialogue", "analog": "analogue",
    "gray": "grey", "program": "programme", "programs": "programmes",
    "practice": "practise",  # only ever hit as a verb in our prose; noun is identical
    "artifact": "artefact", "artifacts": "artefacts",
    "acknowledgment": "acknowledgement", "judgment": "judgement",
}

# Build regex for the explicit word map.
_WORD_RE = re.compile(
    r"\b(" + "|".join(sorted((re.escape(k) for k in _WORD_MAP), key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

# Suffix families for the -ize verbs: analyzing -> analysing, organization -> organisation.
# Only stems on the allow-lists below are touched, so "sizing", "prized" etc. are safe.
_SUFFIX_RE = re.compile(
    r"\b([A-Za-z]+?)(iz)(ing|ed|es|er|ers|ation|ations)\b",
    re.IGNORECASE,
)
_SUFFIX_STEMS = {
    "analy", "paraly", "cataly",  # -yze family, stem ends in 'y' -> keep as -ys
}
_IZE_STEMS = {
    "organ", "recogn", "priorit", "special", "optim", "real", "custom", "minim",
    "maxim", "categor", "summar", "emphas", "util", "standard", "normal", "author",
    "apolog", "character", "familiar", "visual", "modern", "central", "formal",
    "capital", "final", "harmon", "synchron", "hypothes", "scrutin", "stabil",
    "mobil", "digit", "item", "sanit", "colon", "critic", "legal", "local",
}


def _preserve_case(original: str, replacement: str) -> str:
    if original.isupper():
        return replacement.upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _replace_word(m: re.Match) -> str:
    original = m.group(1)
    repl = _WORD_MAP[original.lower()]
    return _preserve_case(original, repl)


def _replace_suffix(m: re.Match) -> str:
    stem, _iz, suffix = m.group(1), m.group(2), m.group(3)
    low = stem.lower()
    if low in _SUFFIX_STEMS:  # analyzing -> analysing
        return _preserve_case(stem, stem + "s" + suffix.lower())
    if low in _IZE_STEMS:  # organizing -> organising, organization -> organisation
        return _preserve_case(stem, stem + "is" + suffix.lower())
    return m.group(0)


def to_british(text: str) -> str:
    """Return ``text`` with common American spellings converted to British.

    Safe to run on prose. Not intended for JSON or code.
    """
    if not text:
        return text
    text = _WORD_RE.sub(_replace_word, text)
    text = _SUFFIX_RE.sub(_replace_suffix, text)
    return text
