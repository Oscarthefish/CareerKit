"""Deterministic Job Match scoring.

The AI classifies (requirement importance, evidence level, title equivalence);
everything in this file is a pure function of that already-validated
structured data. Same inputs always produce the same score - no LLM calls
here, nothing to retry, nothing non-deterministic.

Formula: each requirement contributes (importance weight) x (evidence
multiplier) to a weighted average, expressed as a percentage. The same
formula, scoped to a subset of requirements, produces every explainable
sub-score - Overall Job Match is not a separate calculation, it's the same
formula applied to every requirement at once (with job title folded in as one
more weighted item), so "why did I get this score" always has one answer.
"""
from typing import Optional

from .title_match import STATE_SCORE

IMPORTANCE_WEIGHT = {"critical": 3, "important": 2, "desirable": 1}
EVIDENCE_MULTIPLIER = {"EXPLICIT": 1.0, "INFERRED": 0.7, "POSSIBLE": 0.3, "NOT_FOUND": 0.0}

# requirement "type" -> the explainability sub-score it feeds (matches the
# same categories used for keyword-coverage breakdown and the requirement
# extraction schema, so every view of the data uses one vocabulary).
SUBSCORE_TYPES = {
    "hard_skills": {"hard_skill", "tool", "methodology"},
    "experience_seniority": {"responsibility"},
    "qualifications": {"certification"},
    "soft_skills": {"soft_skill"},
    "industry_context": {"industry"},
}

COVERAGE_ICON = {"STRONG_EVIDENCE": "🟢", "PARTIAL_EVIDENCE": "🟡", "NO_EVIDENCE": "🔴", "UNKNOWN": "⚪"}
COVERAGE_LABEL = {
    "STRONG_EVIDENCE": "Strong",
    "PARTIAL_EVIDENCE": "Partial",
    "NO_EVIDENCE": "Not demonstrated",
    "UNKNOWN": "Cannot determine",
}
ASSESSMENT_LABEL = {"EXPLICIT": "Match", "INFERRED": "Improve", "POSSIBLE": "Improve", "NOT_FOUND": "Evidence needed"}

SCORE_BANDS = [
    (90, "Excellent alignment"),
    (80, "Strong alignment"),
    (70, "Good alignment"),
    (60, "Moderate alignment"),
    (0, "Significant gaps"),
]


def coverage_for(evidence_level: str, confidence: float = 0.5) -> str:
    if evidence_level == "EXPLICIT":
        return "STRONG_EVIDENCE"
    if evidence_level == "INFERRED":
        return "STRONG_EVIDENCE" if confidence >= 0.8 else "PARTIAL_EVIDENCE"
    if evidence_level == "POSSIBLE":
        return "PARTIAL_EVIDENCE"
    if evidence_level == "NOT_FOUND":
        return "NO_EVIDENCE"
    return "UNKNOWN"


def score_band(score: int) -> str:
    for threshold, label in SCORE_BANDS:
        if score >= threshold:
            return label
    return SCORE_BANDS[-1][1]


def _weighted_avg(pairs: list[tuple[float, float]]) -> Optional[int]:
    total_weight = sum(w for w, _ in pairs)
    if total_weight <= 0:
        return None
    total_earned = sum(w * m for w, m in pairs)
    return max(0, min(100, round(total_earned / total_weight * 100)))


def _pairs_for(items: list[dict]) -> list[tuple[float, float]]:
    return [
        (IMPORTANCE_WEIGHT.get(it.get("importance"), 1), EVIDENCE_MULTIPLIER.get(it.get("evidence_level"), 0.0))
        for it in items
    ]


def compute_job_match(requirements_with_evidence: list[dict], title_match: dict) -> dict:
    """requirements_with_evidence: output of evidence.match_evidence().
    title_match: output of title_match.match_title()."""
    sub_scores = {}
    for key, types in SUBSCORE_TYPES.items():
        items = [r for r in requirements_with_evidence if r.get("type") in types]
        sub_scores[key] = {"score": _weighted_avg(_pairs_for(items)), "requirement_count": len(items)}

    title_state = title_match.get("state")
    title_score = STATE_SCORE.get(title_state) if title_state else None
    sub_scores["job_title"] = {"score": title_score, "requirement_count": 1 if title_state else 0}

    overall_pairs = _pairs_for(requirements_with_evidence)
    if title_score is not None:
        overall_pairs.append((IMPORTANCE_WEIGHT["critical"], title_score / 100))
    overall = _weighted_avg(overall_pairs)
    overall = overall if overall is not None else 0

    return {
        "overall": overall,
        "band": score_band(overall),
        "sub_scores": sub_scores,
    }


def requirement_coverage_rows(requirements_with_evidence: list[dict]) -> list[dict]:
    rows = []
    for r in requirements_with_evidence:
        cov = coverage_for(r["evidence_level"], r.get("confidence", 0.5))
        rows.append({
            "name": r["name"],
            "type": r["type"],
            "importance": r["importance"],
            "coverage": cov,
            "icon": COVERAGE_ICON[cov],
            "label": COVERAGE_LABEL[cov],
            "sources": r.get("sources", []),
            "rationale": r.get("rationale", ""),
        })
    return rows


def hard_skills_table(requirements_with_evidence: list[dict]) -> list[dict]:
    rows = [r for r in requirements_with_evidence if r["type"] in ("hard_skill", "tool", "methodology")]
    return [
        {
            "skill": r["name"],
            "importance": r["importance"],
            "coverage": coverage_for(r["evidence_level"], r.get("confidence", 0.5)),
            "assessment": ASSESSMENT_LABEL[r["evidence_level"]],
            "sources": r.get("sources", []),
        }
        for r in rows
    ]


def keyword_coverage(requirements_with_evidence: list[dict]) -> dict:
    matched = sum(1 for r in requirements_with_evidence if r["evidence_level"] == "EXPLICIT")
    partial = sum(1 for r in requirements_with_evidence if r["evidence_level"] in ("INFERRED", "POSSIBLE"))
    missing = sum(1 for r in requirements_with_evidence if r["evidence_level"] == "NOT_FOUND")
    total = len(requirements_with_evidence)
    coverage_pct = round((matched + 0.5 * partial) / total * 100) if total else 0

    by_category: dict[str, dict] = {}
    for r in requirements_with_evidence:
        bucket = by_category.setdefault(r["type"], {"matched": 0, "partial": 0, "missing": 0})
        if r["evidence_level"] == "EXPLICIT":
            bucket["matched"] += 1
        elif r["evidence_level"] in ("INFERRED", "POSSIBLE"):
            bucket["partial"] += 1
        else:
            bucket["missing"] += 1

    return {
        "matched": matched,
        "partial": partial,
        "missing": missing,
        "total": total,
        "coverage_pct": coverage_pct,
        "by_category": by_category,
    }
