"""Recommendation Safety Model.

A recommendation's tier is derived purely from the evidence level CareerKit
itself computed - never from anything the LLM asserts about the requirement -
so an unsupported item is structurally incapable of being marked safe to add,
regardless of model output.

    SAFE_OPTIMISATION - the Master CV already supports this (EXPLICIT or
        INFERRED evidence exists). The fix is wording, not new content.
    EVIDENCE_NEEDED - the requirement might be something the candidate has
        done, but the Master CV doesn't prove it (POSSIBLE evidence, or
        NOT_FOUND on a non-certification requirement - a skill/tool/
        responsibility could genuinely be missing from the record without
        being missing from the candidate's actual experience). Never add
        without the user confirming and adding real evidence first.
    DO_NOT_ADD - a qualification/certification with no supporting evidence.
        Unlike a skill, a certification is binary (you hold it or you don't) -
        there is no "maybe forgot to record it" case worth prompting for.
"""
from typing import Optional

from .scoring import coverage_for

_SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def safety_tier(requirement_with_evidence: dict) -> Optional[str]:
    level = requirement_with_evidence["evidence_level"]
    if level in ("EXPLICIT", "INFERRED"):
        return "SAFE_OPTIMISATION" if level == "INFERRED" else None  # EXPLICIT needs no fix at all
    if level == "POSSIBLE":
        return "EVIDENCE_NEEDED"
    # NOT_FOUND
    if requirement_with_evidence["type"] == "certification":
        return "DO_NOT_ADD"
    return "EVIDENCE_NEEDED"


def _severity(requirement_with_evidence: dict, tier: str) -> str:
    importance = requirement_with_evidence["importance"]
    if tier == "DO_NOT_ADD":
        return "critical" if importance == "critical" else "high"
    if tier == "EVIDENCE_NEEDED":
        if importance == "critical":
            return "critical"
        if importance == "important":
            return "high"
        return "medium"
    return "low"  # SAFE_OPTIMISATION - real evidence exists, just needs clearer wording


def _message(requirement_with_evidence: dict, tier: str) -> str:
    name = requirement_with_evidence["name"]
    level = requirement_with_evidence["evidence_level"]
    if tier == "SAFE_OPTIMISATION":
        sources = requirement_with_evidence.get("sources") or []
        via = sources[0] if sources else "related experience"
        return (
            f'You already demonstrate {name}-equivalent work through "{via}", but the exact '
            f'term "{name}" doesn\'t appear on your CV. Adding the recognised term may improve '
            "searchability without changing the meaning of your experience."
        )
    if tier == "EVIDENCE_NEEDED" and level == "POSSIBLE":
        return f"CareerKit found possible evidence for {name} but couldn't confidently confirm it meets this requirement."
    if tier == "EVIDENCE_NEEDED":
        return f"{name} is requested by the employer but isn't demonstrated in your Master CV. Add it only if you genuinely have this experience."
    return f"{name} is listed as required. Your Master CV does not contain it — do not add it unless you genuinely hold it."


def build_priority_fixes(requirements_with_evidence: list[dict], title_match: dict, limit: int = 8) -> dict:
    """Returns {"top": [...], "more": [...]} - `top` is what the UI shows by
    default (limit items, most severe first), `more` is everything else behind
    a "View all findings" control."""
    fixes = []
    for r in requirements_with_evidence:
        tier = safety_tier(r)
        if tier is None:
            continue
        severity = _severity(r, tier)
        fixes.append({
            "requirement": r["name"],
            "type": r["type"],
            "importance": r["importance"],
            "coverage": coverage_for(r["evidence_level"], r.get("confidence", 0.5)),
            "tier": tier,
            "severity": severity,
            "message": _message(r, tier),
        })

    title_fix = _title_recommendation(title_match)
    if title_fix:
        fixes.append(title_fix)

    fixes.sort(key=lambda f: _SEVERITY_RANK.get(f["severity"], 0), reverse=True)
    return {"top": fixes[:limit], "more": fixes[limit:]}


def _title_recommendation(title_match: dict) -> Optional[dict]:
    state = title_match.get("state")
    matched = title_match.get("matched_title")
    if state == "STRONG_EQUIVALENT" and matched:
        return {
            "requirement": "Job title alignment",
            "type": "job_title",
            "importance": "important",
            "coverage": "PARTIAL_EVIDENCE",
            "tier": "SAFE_OPTIMISATION",
            "severity": "medium",
            "message": (
                f'Your title "{matched}" is strongly equivalent to the advertised title. Consider '
                f'including the advertised title in brackets, e.g. "{matched} ({title_match.get("job_title", "")})" '
                "— never replace your real historical title, only add the alias alongside it."
            ),
        }
    if state == "RELATED_TITLE" and matched:
        return {
            "requirement": "Job title alignment",
            "type": "job_title",
            "importance": "desirable",
            "coverage": "PARTIAL_EVIDENCE",
            "tier": "EVIDENCE_NEEDED",
            "severity": "low",
            "message": (
                f'Your title "{matched}" is related but not a strong equivalent. Consider referencing the '
                "target role in your professional summary instead of the job title itself, e.g. "
                '"Security professional targeting [role] opportunities...".'
            ),
        }
    return None


def select_safe_fixes(job_match_result: dict, requested_names: list[str]) -> list[dict]:
    """Server-side enforcement of the Recommendation Safety Model for Custom
    CV generation: given the requirement names a user checked in the UI,
    returns only the ones that are BOTH requested AND already tagged
    SAFE_OPTIMISATION in the stored report. Even if a client somehow sent an
    EVIDENCE_NEEDED or DO_NOT_ADD requirement name, it is silently dropped
    here rather than ever reaching the CV-writing prompt - the client-side
    checkbox being disabled is a UX nicety, this is the actual guarantee."""
    requested = set(requested_names or [])
    fixes = job_match_result.get("priority_fixes", {})
    all_fixes = (fixes.get("top") or []) + (fixes.get("more") or [])
    return [f for f in all_fixes if f.get("requirement") in requested and f.get("tier") == "SAFE_OPTIMISATION"]
