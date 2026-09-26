"""Job title equivalence classification.

Only ever produces a *suggestion* to mention the advertised title alongside
the real one (e.g. "Senior Security Operations Analyst (Senior SOC Analyst)").
Never rewrites, and never invents, a historical job title - the caller must
keep using the candidate's actual `role`/`company` values regardless of what
this classifies."""
import json
from typing import Optional

from ..prompt_service import fill_prompt

TITLE_STATES = ("EXACT_MATCH", "STRONG_EQUIVALENT", "RELATED_TITLE", "WEAK_ALIGNMENT", "NO_ALIGNMENT")

# Deterministic score for the job-title sub-score in scoring.py - explainable
# and stable regardless of which path (exact-match short-circuit or LLM
# classification) produced the state.
STATE_SCORE = {
    "EXACT_MATCH": 100,
    "STRONG_EQUIVALENT": 85,
    "RELATED_TITLE": 60,
    "WEAK_ALIGNMENT": 30,
    "NO_ALIGNMENT": 5,
}


def _candidate_titles(profile: dict) -> list[str]:
    titles: list[str] = []
    for e in profile.get("work_experience", []):
        if e.get("role"):
            titles.append(e["role"])
        titles.extend(t for t in (e.get("alternative_titles") or []) if t)
    seen, out = set(), []
    for t in titles:
        low = t.lower()
        if low not in seen:
            seen.add(low)
            out.append(t)
    return out


def _validate_title_match(candidate_titles: set[str]):
    def _validate(parsed: dict) -> Optional[str]:
        state = parsed.get("state")
        if state not in TITLE_STATES:
            return f"invalid state {state!r} (must be one of {TITLE_STATES})"
        matched = parsed.get("matched_title")
        if state != "NO_ALIGNMENT":
            if not matched or matched.lower() not in candidate_titles:
                return f"matched_title {matched!r} is not one of the candidate's real titles"
        return None
    return _validate


async def match_title(provider, job_title: str, profile: dict) -> dict:
    """Returns {state, matched_title, explanation}."""
    titles = _candidate_titles(profile)

    if not job_title:
        return {"state": "NO_ALIGNMENT", "matched_title": None, "explanation": "No advertised job title to compare."}
    if not titles:
        return {"state": "NO_ALIGNMENT", "matched_title": None, "explanation": "No work experience titles on record to compare."}

    low_job_title = job_title.strip().lower()
    for t in titles:
        if t.strip().lower() == low_job_title:
            return {
                "state": "EXACT_MATCH",
                "matched_title": t,
                "explanation": f'Your title "{t}" matches the advertised title "{job_title}" exactly.',
            }

    prompt = fill_prompt(
        "title_match",
        JOB_TITLE=job_title,
        CANDIDATE_TITLES=json.dumps(titles, indent=2),
    )
    try:
        parsed = await provider.generate_json(
            prompt,
            required_keys=["state"],
            validate=_validate_title_match({t.lower() for t in titles}),
        )
    except ValueError:
        # Unreliable classification - fall back to the most conservative,
        # honest state rather than guessing.
        return {
            "state": "RELATED_TITLE",
            "matched_title": titles[0],
            "explanation": "CareerKit could not confidently classify how closely your title aligns with this one.",
        }

    return {
        "state": parsed["state"],
        "matched_title": parsed.get("matched_title"),
        "explanation": parsed.get("explanation", ""),
    }
