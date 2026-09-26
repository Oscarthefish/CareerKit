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
        if r.get("type") not in REQUIREMENT_TYPES:
            return f"invalid type {r.get('type')!r} for {r['name']!r} (must be one of {REQUIREMENT_TYPES})"
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
