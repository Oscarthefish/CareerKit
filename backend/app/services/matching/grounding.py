"""Keep job-specific AI output grounded in the job advert actually pasted.

The local model is given illustrative examples in its prompts (e.g. "fraud
intelligence", "insurance claims management") and, being a small model,
sometimes copies one into its output as if the job had asked for it - despite
prompt wording explicitly forbidding that. A list of known example phrases
(_strip_prompt_example_contamination in evidence.py) only catches phrases
someone has already seen leak. This is the general rule instead: anything
presented as a skill/requirement *of this job* (a match, a gap, a "do not
claim", an ATS keyword, a Job Match requirement) must have its distinctive
words actually present in the job description text.

Deliberately lenient on wording: the model paraphrases ("Triage and
Investigation" for "triaging and investigating"), so words are compared by
a shared prefix stem, and generic filler words ("security", "experience",
"skills"...) never decide the outcome on their own. Only entries whose
distinctive words are absent from the advert are removed.
"""
from __future__ import annotations

import json
import re

# Words too generic to prove (or disprove) that a phrase came from this advert.
_GENERIC = {
    "the", "and", "with", "for", "from", "into", "that", "this", "your", "you",
    "our", "are", "was", "were", "has", "have", "its", "per", "via", "etc",
    "skill", "skills", "experience", "experienced", "knowledge", "ability",
    "understanding", "strong", "good", "excellent", "proven", "relevant",
    "security", "cyber", "cybersecurity", "information", "technical", "technology",
    "related", "similar", "work", "working", "role", "level", "high", "highly",
    "regarded", "including", "across", "within", "general", "management",
    "related", "years", "year", "plus", "background", "exposure", "familiarity",
    "hands", "on", "based", "using", "use", "best", "practice", "practices",
}

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9+#./-]*")
# Longest first. Light, deliberately conservative suffix stripping so that
# "writing"/"written", "reports"/"reporting" and "investigation"/
# "investigating" meet - not a full stemmer.
_SUFFIXES = (
    "ship", "ations", "ation", "ments", "ment", "ings", "ing", "ions", "ion",
    "ities", "ity", "ies", "ers", "ten", "er", "ed", "es", "ly", "s", "e",
)
# Two stems are "the same word" when equal, or when they share a prefix at
# least this long that also covers most of the shorter stem: "investig" ~
# "investigat", "analysi" ~ "analytic". Short stems must match exactly, so
# "sent" never matches "sentinel", and "investment" never matches "investig".
_MIN_PREFIX_STEM = 5
_MIN_PREFIX_SHARE = 0.7


def _words(text: str) -> list[str]:
    return [w.strip("./-") for w in _WORD_RE.findall((text or "").lower()) if w.strip("./-")]


def _stem(word: str) -> str:
    # Two passes: "leadership" -> "leader" -> "lead".
    for _ in range(2):
        for suffix in _SUFFIXES:
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                word = word[: -len(suffix)]
                break
        else:
            break
    return word


def _common_prefix_len(a: str, b: str) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def _significant(text: str) -> set[str]:
    return {w for w in _words(text) if len(w) > 2 and w not in _GENERIC}


class JobText:
    """The advert's vocabulary, precomputed once per job."""

    def __init__(self, *texts: str):
        words = set()
        for t in texts:
            words.update(_words(t))
        self._words = words
        self._stems = {_stem(w) for w in words}
        # Also index hyphen/slash parts: "go-to", "ci/cd", "sc-200" stay whole
        # above, but their parts count too ("incident-response" -> "incident").
        for w in list(words):
            for part in re.split(r"[-/]", w):
                if part:
                    self._words.add(part)
                    self._stems.add(_stem(part))

    @property
    def empty(self) -> bool:
        return not self._words

    def has_word(self, word: str) -> bool:
        if word in self._words:
            return True
        stem = _stem(word)
        if stem in self._stems:
            return True
        if len(stem) < _MIN_PREFIX_STEM:
            return False
        for s in self._stems:
            if len(s) < _MIN_PREFIX_STEM:
                continue
            common = _common_prefix_len(stem, s)
            if common >= _MIN_PREFIX_STEM and common >= _MIN_PREFIX_SHARE * min(len(stem), len(s)):
                return True
        return False

    def grounds(self, phrase: str) -> bool:
        """True when the advert contains the phrase's distinctive words. One-
        and two-word phrases need every distinctive word; longer, sentence-
        like requirements may paraphrase one word in three. A phrase made only
        of generic words can't be judged, so it's kept."""
        distinctive = _significant(phrase)
        if not distinctive:
            return True
        present = sum(1 for w in distinctive if self.has_word(w))
        return present * 3 >= len(distinctive) * 2 if len(distinctive) >= 3 else present == len(distinctive)


def job_text_for(job_description_raw: str | None) -> JobText:
    """Ground against the raw advert only - never the AI's own job analysis,
    which is itself model output and can carry the same contamination."""
    return JobText(job_description_raw or "")


def _entry_name(entry) -> str:
    if isinstance(entry, dict):
        return str(entry.get("skill") or entry.get("name") or "")
    return str(entry or "")


def filter_grounded(entries, job: JobText) -> tuple[list, list]:
    """Split a list of strings / {"skill"|"name": ...} dicts into
    (kept, removed) by whether the advert grounds each entry's name."""
    kept, removed = [], []
    for entry in entries or []:
        (kept if job.grounds(_entry_name(entry)) else removed).append(entry)
    return kept, removed


SCORECARD_SKILL_LISTS = (
    "strong_matches", "partial_matches", "quick_learning_gaps", "genuine_gaps",
    "do_not_claim", "ats_keywords_to_include",
)


def ground_scorecard(scorecard: dict, job_description_raw: str | None) -> dict:
    """Return a copy of the Match Scorecard with every job-skill entry that
    the advert doesn't mention removed. No-op without an advert to check."""
    if not isinstance(scorecard, dict):
        return scorecard
    job = job_text_for(job_description_raw)
    if job.empty:
        return scorecard
    out = dict(scorecard)
    for key in SCORECARD_SKILL_LISTS:
        if isinstance(out.get(key), list):
            out[key], _ = filter_grounded(out[key], job)
    return out


ANALYSIS_SKILL_LISTS = ("required_skills", "preferred_skills", "repeated_keywords")


def ground_job_analysis(analysis: dict, job_description_raw: str | None) -> dict:
    """Same rule for the Job Analysis skill lists, which every later prompt
    (scorecard, cover letter, CV, interview prep) is built from."""
    if not isinstance(analysis, dict):
        return analysis
    job = job_text_for(job_description_raw)
    if job.empty:
        return analysis
    out = dict(analysis)
    for key in ANALYSIS_SKILL_LISTS:
        if isinstance(out.get(key), list):
            out[key], _ = filter_grounded(out[key], job)
    return out


def _loads(blob):
    if not blob:
        return None
    try:
        return json.loads(blob)
    except (TypeError, ValueError):
        return None


def grounded_analysis(app) -> dict | None:
    """The application's stored Job Analysis with advert-ungrounded skills
    removed. Applied on every read, so analyses saved before this check
    existed are corrected too, without rewriting what's stored."""
    return ground_job_analysis(_loads(app.job_analysis), app.job_description_raw)


def grounded_scorecard(app) -> dict | None:
    """The application's stored Match Scorecard, grounded the same way."""
    return ground_scorecard(_loads(app.match_scorecard), app.job_description_raw)


def ground_requirements(requirements: list[dict], job_description_raw: str | None) -> list[dict]:
    """Job Match requirements (each {"name": ...}) the advert actually states."""
    job = job_text_for(job_description_raw)
    if job.empty:
        return requirements
    kept, _ = filter_grounded(requirements, job)
    return kept
