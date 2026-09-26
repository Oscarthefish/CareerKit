"""Recruiter Readiness: how compelling the CV is to a human recruiter, kept
deliberately separate from ATS Compatibility - a CV can be technically easy
to parse and still read as generic or unconvincing.

Same architecture principle as the rest of Stage 1/2: the LLM classifies
(via the existing brutal_review.md rubric), CareerKit's code computes the
score. The score is a pure function of that classification plus a couple of
deterministic counts pulled from the CV text itself (bullet count, so a weak-
bullet count means something relative to the CV's actual size) - nothing here
is "ask the model for a percentage".

Recruiter Readiness is a property of the CV itself, not of any one job
application, so a computed result is cached on the CVVersion row it was
computed from (immutable once created - a new CV version always gets a new
row) rather than recomputed on every Job Match run.
"""
import json
from typing import Optional

from ..ats.sections import parse as parse_cv
from ..prompt_service import fill_prompt

TOP_THIRD_SCORE = {"strong": 100, "ok": 60, "weak": 20}
ROLE_CLARITY_SCORE = {"clear": 100, "unclear": 50, "missing": 0}
CREDIBILITY_SCORE = {"high": 100, "medium": 60, "low": 20}
GENERIC_SCORE = {"specific": 100, "somewhat_generic": 60, "generic": 20}

SCORE_BANDS = [(90, "Excellent"), (75, "Good"), (60, "Needs work"), (0, "Significant issues")]


def _band(score: int) -> str:
    for threshold, label in SCORE_BANDS:
        if score >= threshold:
            return label
    return SCORE_BANDS[-1][1]


def _list_penalty_score(count: int, scale: int) -> int:
    """More items -> lower score; 0 items -> a perfect 100. `scale` is how many
    points each item costs, calibrated per list by how severe an item in it
    typically is (a shortlisting blocker costs far more than a repeated word)."""
    return max(0, 100 - count * scale)


def _weak_bullet_score(weak_count: int, total_bullets: int) -> int:
    if total_bullets <= 0:
        return 50  # nothing to measure a ratio against - neither reward nor punish
    ratio = weak_count / total_bullets
    return max(0, round(100 * (1 - ratio * 2)))


def _validate_review(parsed: dict) -> Optional[str]:
    """Checked before the review is trusted enough to score - the enum
    fields are looked up directly in fixed dicts below, so a value outside
    the expected set needs to be caught here rather than causing a KeyError
    (or, worse, silently defaulting) downstream."""
    checks = [
        ("top_third_strength", TOP_THIRD_SCORE),
        ("target_role_clarity", ROLE_CLARITY_SCORE),
        ("credibility_rating", CREDIBILITY_SCORE),
        ("generic_rating", GENERIC_SCORE),
    ]
    for field, allowed in checks:
        if parsed.get(field) not in allowed:
            return f"invalid {field} {parsed.get(field)!r} (must be one of {list(allowed)})"
    if not isinstance(parsed.get("priority_fixes"), list):
        return "missing or malformed 'priority_fixes' list"
    for key in ("missing_evidence", "weak_bullets", "repeated_wording", "readability_issues", "shortlisting_blockers"):
        if not isinstance(parsed.get(key, []), list):
            return f"'{key}' must be a list"
    return None


def compute_recruiter_readiness(review: dict, cv_markdown: str) -> dict:
    """review: a brutal_review.md response that has already passed
    _validate_review. Returns {score, band, sub_scores}."""
    total_bullets = parse_cv(cv_markdown or "").bullet_count

    first_impression = round((
        TOP_THIRD_SCORE.get(review.get("top_third_strength"), 60)
        + ROLE_CLARITY_SCORE.get(review.get("target_role_clarity"), 50)
    ) / 2)

    credibility = round((
        CREDIBILITY_SCORE.get(review.get("credibility_rating"), 60)
        + GENERIC_SCORE.get(review.get("generic_rating"), 60)
        + _list_penalty_score(len(review.get("missing_evidence") or []), scale=10)
    ) / 3)

    achievement_quality = _weak_bullet_score(len(review.get("weak_bullets") or []), total_bullets)

    readability = round((
        _list_penalty_score(len(review.get("readability_issues") or []), scale=8)
        + _list_penalty_score(len(review.get("repeated_wording") or []), scale=6)
    ) / 2)

    shortlisting_readiness = _list_penalty_score(len(review.get("shortlisting_blockers") or []), scale=15)

    sub_scores = {
        "first_impression": first_impression,
        "credibility": credibility,
        "achievement_quality": achievement_quality,
        "readability": readability,
        "shortlisting_readiness": shortlisting_readiness,
    }
    overall = round(sum(sub_scores.values()) / len(sub_scores))
    return {"score": overall, "band": _band(overall), "sub_scores": sub_scores}


async def get_or_compute_recruiter_readiness(provider, db, cv_version, force: bool = False) -> Optional[dict]:
    """Returns the full brutal_review dict plus a "readiness" key holding the
    computed score, or None if the CV is empty or the model couldn't produce
    a trustworthy classification. Cached on cv_version.recruiter_readiness_result
    unless force=True (used by the explicit "Brutal Recruiter Review" action,
    which should always get a fresh take)."""
    if not force and cv_version.recruiter_readiness_result:
        return json.loads(cv_version.recruiter_readiness_result)
    if not cv_version.content_markdown:
        return None

    prompt = fill_prompt("brutal_review", CV_CONTENT=cv_version.content_markdown)
    try:
        review = await provider.generate_json(
            prompt,
            required_keys=["overall_verdict", "priority_fixes"],
            validate=_validate_review,
        )
    except ValueError:
        return None

    result = {**review, "readiness": compute_recruiter_readiness(review, cv_version.content_markdown)}
    cv_version.recruiter_readiness_result = json.dumps(result)
    db.commit()
    return result
