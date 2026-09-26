"""Job Description Intelligence: extract structured, classified requirements
from a job analysis + the raw JD text.

Importance (critical/important/desirable) is an LLM judgement call, but it is
validated against a fixed enum before being trusted, and the prompt explicitly
tells the model to classify by wording/placement/context - not by counting how
many times a phrase appears (see job_requirements.md)."""
import json
from typing import Optional

from ..prompt_service import fill_prompt

REQUIREMENT_TYPES = (
    "hard_skill", "tool", "methodology", "responsibility",
    "certification", "industry", "soft_skill",
)
IMPORTANCE_LEVELS = ("critical", "important", "desirable")

# The model occasionally invents a plausible-sounding type that isn't in the
# enum instead of picking the closest real one (observed in practice:
# "experience" for a tenure requirement like "3+ years SOC experience", which
# the prompt uses as its own worked example without ever saying which type it
# is). Rather than let a single bad enum value fail validation twice and
# raise - discarding the whole requirements list over one field - normalise
# known near-misses to the closest real type first.
_TYPE_ALIASES = {
    "experience": "hard_skill",
    "years_experience": "hard_skill",
    "seniority": "hard_skill",
    "skill": "hard_skill",
    "technical_skill": "hard_skill",
    "platform": "tool",
    "technology": "tool",
    "process": "methodology",
    "duty": "responsibility",
    "task": "responsibility",
    "cert": "certification",
    "qualification": "certification",
    "domain": "industry",
    "sector": "industry",
    "soft_skills": "soft_skill",
    "communication": "soft_skill",
}


def _normalize_type(raw_type) -> Optional[str]:
    if not isinstance(raw_type, str):
        return None
    key = raw_type.strip().lower().replace(" ", "_").replace("-", "_")
    if key in REQUIREMENT_TYPES:
        return key
    return _TYPE_ALIASES.get(key)


def _validate_requirements(parsed: dict) -> Optional[str]:
    items = parsed.get("requirements")
    if not isinstance(items, list) or not items:
        return "missing or empty 'requirements' list"
    seen_names = set()
    for r in items:
        if not isinstance(r, dict) or not r.get("name"):
            return "every requirement needs a 'name'"
        if r["name"].lower() in seen_names:
            return f"duplicate requirement {r['name']!r} - list each requirement once"
        seen_names.add(r["name"].lower())
        if r.get("importance") not in IMPORTANCE_LEVELS:
            return f"invalid importance {r.get('importance')!r} for {r['name']!r} (must be one of {IMPORTANCE_LEVELS})"
        normalized_type = _normalize_type(r.get("type"))
        if normalized_type is None:
            return f"invalid type {r.get('type')!r} for {r['name']!r} (must be one of {REQUIREMENT_TYPES})"
        r["type"] = normalized_type  # mutates the dict generate_json returns, so the fix sticks
    return None


async def extract_requirements(provider, job_analysis: dict, job_description_raw: str) -> list[dict]:
    """Returns a list of {name, type, importance, source_text} dicts."""
    prompt = fill_prompt(
        "job_requirements",
        JOB_ANALYSIS=json.dumps(job_analysis, indent=2),
        JOB_DESCRIPTION=(job_description_raw or "")[:6000],
    )
    parsed = await provider.generate_json(
        prompt,
        required_keys=["requirements"],
        validate=_validate_requirements,
    )
    return parsed["requirements"]


def bucket_by_importance(requirements: list[dict]) -> dict[str, list[dict]]:
    buckets: dict[str, list[dict]] = {level: [] for level in IMPORTANCE_LEVELS}
    for r in requirements:
        buckets.setdefault(r.get("importance", "desirable"), []).append(r)
    return buckets
