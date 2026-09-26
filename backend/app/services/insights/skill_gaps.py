"""Master CV Feedback Loop: surfaces requirements that keep showing up across
target roles but are weakly evidenced in the Master CV. The point isn't to
score any one application - it's to notice a pattern ("Threat Hunting has come
up in 4 of your last 6 target roles and your Master CV has limited evidence of
it") so the user can capture real experience once, in the Master CV, and every
future application benefits from it.

Fully deterministic - built entirely from Job Match reports already computed
and stored (requirement_coverage), no LLM call of its own.
"""
from ..matching.synonyms import expand_terms

# Coverage values that mean "this came up, but isn't solidly evidenced yet" -
# NOT_FOUND is deliberately included: an application-level 🔴 doesn't claim
# the candidate lacks the experience, just that the Master CV doesn't show it
# (see services/matching/evidence.py) - which is exactly the gap this loop
# exists to close.
WEAK_COVERAGE = {"PARTIAL_EVIDENCE", "NO_EVIDENCE"}


def _canonical_key(name: str) -> str:
    """Requirement names that are known synonyms of each other (see
    synonyms.py) must land in the same bucket - "SOC" and "Security
    Operations Centre" are one skill, not two. expand_terms always returns
    the identical set for every member of a group, so picking a fixed
    element of that set (its min) is a stable, deterministic bucket key
    regardless of which spelling triggered it."""
    variants = expand_terms(name)
    return min(variants) if variants else (name or "").strip().lower()


def compute_skill_gaps(applications: list[dict], min_appearances: int = 2) -> list[dict]:
    """applications: [{"role": str, "company": str, "requirement_coverage": [
    {"name": str, "coverage": str}, ...]}, ...] - one entry per JobApplication
    that has a stored Job Match report.

    Returns requirements that appeared in at least `min_appearances`
    applications AND were weakly evidenced in at least one of them, ranked by
    how often they were weak, then by how often they appeared at all."""
    buckets: dict[str, dict] = {}

    for app in applications:
        seen_this_app: set[str] = set()
        for row in app.get("requirement_coverage", []):
            name = row.get("name")
            if not name:
                continue
            key = _canonical_key(name)
            if key in seen_this_app:
                continue  # don't double-count a synonym pair within one application
            seen_this_app.add(key)

            bucket = buckets.setdefault(key, {"display_name": name, "appearances": 0, "weak_count": 0, "roles": []})
            bucket["appearances"] += 1
            if row.get("coverage") in WEAK_COVERAGE:
                bucket["weak_count"] += 1
                role_label = app.get("role") or "Unknown role"
                if app.get("company"):
                    role_label += f" at {app['company']}"
                bucket["roles"].append(role_label)

    results = []
    for bucket in buckets.values():
        if bucket["appearances"] < min_appearances or bucket["weak_count"] == 0:
            continue
        results.append({
            "skill": bucket["display_name"],
            "appearances": bucket["appearances"],
            "weak_count": bucket["weak_count"],
            "sample_roles": bucket["roles"][:5],
        })

    results.sort(key=lambda r: (r["weak_count"], r["appearances"]), reverse=True)
    return results
