"""Deterministic tenure matching: "3+ years SOC experience", "at least 5
years of dedicated Security Operations Centre experience" and similar
requirements were consistently coming back NOT_FOUND even though the
candidate's actual work history clearly supports them - the LLM-assisted
pass either doesn't reliably do tenure arithmetic from raw start/end dates,
or tries to and cites a generic bucket name ("professional_summary") instead
of anything the citation-authenticity check can verify.

A tenure claim is unlike a skill/tool/achievement citation: there's no single
named profile item to point to, it's a fact computed FROM the work history.
So compute it in code - same "classify with AI, decide/compute in code"
principle used throughout this package - and hand back a real, dated,
human-readable source (role names and their actual date ranges) that is, by
construction, never fabricated.
"""
import re
from datetime import date
from typing import Optional

# Deliberately narrow: these are the phrasings a real SOC-titled role search
# should match. A broader "cyber/information security" bucket is also
# supported for requirements that don't specifically ask for SOC tenure.
_SOC_KEYWORDS = ("security operations", "soc")
_SECURITY_KEYWORDS = _SOC_KEYWORDS + ("cyber security", "information security", "network security")

_YEARS_PATTERN = re.compile(r"(\d+)\+?\s*years?", re.IGNORECASE)


def _parse_month(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    m = re.match(r"^(\d{4})-(\d{1,2})$", value.strip())
    if not m:
        return None
    year, month = int(m.group(1)), int(m.group(2))
    if not (1 <= month <= 12):
        return None
    return date(year, month, 1)


def _role_span_years(exp: dict) -> float:
    start = _parse_month(exp.get("start_date"))
    if not start:
        return 0.0
    end = date.today() if exp.get("is_current") else (_parse_month(exp.get("end_date")) or date.today())
    if end < start:
        return 0.0
    return (end - start).days / 365.25


def compute_tenure_years(work_experience: list[dict], keywords: tuple[str, ...]) -> float:
    """Total time (in years) spent in roles whose title contains any of the
    given keywords. Work history is a sequential career timeline, not
    concurrent roles, so summing each matching role's span is safe - it
    never double-counts the way overlapping-interval merging would need to
    guard against."""
    return sum(_role_span_years(e) for e in work_experience if any(k in (e.get("role") or "").lower() for k in keywords))


def _matching_roles_description(work_experience: list[dict], keywords: tuple[str, ...]) -> list[str]:
    return [
        f"{e.get('role')} ({e.get('start_date') or '?'} - {'Present' if e.get('is_current') else (e.get('end_date') or '?')})"
        for e in work_experience
        if any(k in (e.get("role") or "").lower() for k in keywords)
    ]


def match_tenure_requirement(requirement_name: str, work_experience: list[dict]) -> Optional[dict]:
    """Returns an evidence dict if this requirement is a tenure/years
    threshold that the candidate's real work history dates satisfy, or None
    if it isn't a tenure requirement this function recognises, or if the
    computed tenure falls short (in which case the normal LLM-assisted pass
    still gets a chance - this function only ever confirms a real, computed
    match, never asserts a shortfall itself)."""
    m = _YEARS_PATTERN.search(requirement_name or "")
    if not m:
        return None
    required_years = int(m.group(1))

    name_l = requirement_name.lower()
    if any(k in name_l for k in _SOC_KEYWORDS):
        keywords, label = _SOC_KEYWORDS, "SOC / Security Operations"
    elif any(k in name_l for k in _SECURITY_KEYWORDS):
        keywords, label = _SECURITY_KEYWORDS, "security"
    else:
        return None  # not a security-tenure requirement this function can confidently compute

    actual_years = compute_tenure_years(work_experience, keywords)
    if actual_years < required_years:
        return None

    roles = _matching_roles_description(work_experience, keywords)
    return {
        "evidence_level": "EXPLICIT",
        "confidence": 0.95,
        "sources": [f"Work history: {actual_years:.1f} years across {label} roles - " + "; ".join(roles)],
        "rationale": (
            f"Computed from the candidate's real work history dates: {actual_years:.1f} years across "
            f"{label} roles, meeting the {required_years}+ year requirement."
        ),
    }
