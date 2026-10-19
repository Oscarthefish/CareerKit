"""Deterministic work-rights/citizenship matching: "AU / NZ citizenship
preferred", "must have NZ work rights" and similar requirements were being
handed to the LLM-assisted pass, which then tried to force-fit evidence from
completely unrelated skills and work history (observed in practice citing
"Skill: AlienVault OTX" and several unrelated work-experience responsibility
bullets as "evidence" of citizenship) rather than recognising this as a
single yes/no fact already on record in the candidate's own profile.

Work rights is unlike a skill/tool/achievement citation: there's no work
history to search for it, it's a structured fact
(profile.personal.nz_work_rights). So check it in code - same "classify
with AI, decide/compute in code" principle used throughout this package
(see tenure.py for the same pattern applied to years-of-experience
requirements, including the same "only ever confirm a match, never assert
a shortfall" discipline - a candidate who doesn't clearly have the right
status still falls through to the normal LLM-assisted pass rather than
this module asserting NOT_FOUND itself)."""

_WORK_RIGHTS_KEYWORDS = (
    "citizenship", "citizen", "work rights", "right to work", "work permit",
    "visa", "permanent resident", "pr status",
)

_ELIGIBLE_VALUES = ("citizen", "permanent resident", "pr", "resident")


def match_work_rights_requirement(requirement_name: str, personal: dict) -> dict | None:
    """Returns an evidence dict if requirement_name is asking about
    citizenship/visa/work-rights eligibility AND the candidate's own
    recorded status clearly confirms it, else None - either because this
    isn't a work-rights requirement at all, or because the recorded status
    doesn't clearly confirm eligibility (left to the normal pass, same as
    tenure.py's shortfall case)."""
    name_l = (requirement_name or "").lower()
    if not any(k in name_l for k in _WORK_RIGHTS_KEYWORDS):
        return None

    status = ((personal or {}).get("nz_work_rights") or "").strip()
    if not status or not any(v in status.lower() for v in _ELIGIBLE_VALUES):
        return None

    return {
        "evidence_level": "EXPLICIT",
        "confidence": 0.95,
        "sources": [f"Profile: recorded work rights status - {status}"],
        "rationale": f"The candidate's own recorded work rights status on their profile is '{status}'.",
    }
