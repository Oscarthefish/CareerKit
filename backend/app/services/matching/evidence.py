"""Master CV Evidence Model.

Classifies, for each extracted job requirement, whether the candidate's
structured profile evidences it — never the markdown CV text, and never the
job description's own wording. Two passes, cheapest and most reliable first:

1. Deterministic exact/alias/synonym string matching over the profile
   (`match_requirement_deterministic`) - fast, free, and 100% reproducible.
2. For whatever is still unresolved, one validated LLM call
   (`match_evidence_llm`) that must cite a real, named profile item for
   anything it marks EXPLICIT/INFERRED - a citation that doesn't correspond to
   an actual skill/achievement/employer/etc. in the profile we handed it fails
   validation and forces a retry, then falls back to NOT_FOUND rather than
   ever trusting an uncited or fabricated "match" (see match_scorecard.md /
   cover_letter.md for the same principle applied to free-text generation).

Evidence levels (the "Master CV Evidence Model"):
    EXPLICIT   - the profile names this exact thing (or a known synonym/alias).
    INFERRED   - the profile shows something that reasonably implies it,
                 without using the term itself (e.g. "Splunk" for "SIEM").
    POSSIBLE   - weak/indirect signal only (e.g. in-progress training towards
                 it) - not enough to confidently call it evidenced.
    NOT_FOUND  - nothing in the profile supports it. This means "not
                 demonstrated in the Master CV", not "the candidate doesn't
                 have this experience" - callers must preserve that framing.
"""
import json
from typing import Optional

from .synonyms import expand_terms

EVIDENCE_LEVELS = ("EXPLICIT", "INFERRED", "POSSIBLE", "NOT_FOUND")


def _profile_haystack(profile: dict) -> list[tuple[str, str]]:
    """(lowercased searchable text, human-readable source label) pairs drawn
    from completed/confirmed profile items only - in-progress items are kept
    separate (see _in_progress_haystack) since they are not yet held."""
    out: list[tuple[str, str]] = []

    for s in profile.get("skills", []):
        name = s.get("name")
        if not name:
            continue
        label = f"Skill: {name}"
        for variant in [name, *s.get("aliases", [])]:
            if variant:
                out.append((variant.lower(), label))

    for e in profile.get("work_experience", []):
        role, company = e.get("role"), e.get("company")
        base = f"{role} at {company}" if role and company else (role or company or "a former role")
        for tech in e.get("technologies", []) or []:
            if tech:
                out.append((tech.lower(), f"Work experience: {base} (technology: {tech})"))
        for resp in e.get("key_responsibilities", []) or []:
            if resp:
                out.append((resp.lower(), f"Work experience: {base} (responsibility)"))
        if e.get("description"):
            out.append((e["description"].lower(), f"Work experience: {base} (description)"))
        for alt in e.get("alternative_titles", []) or []:
            if alt:
                out.append((alt.lower(), f"Work experience: {base} (alternative title: {alt})"))

    for a in profile.get("achievements", []):
        title = a.get("title") or "an achievement"
        for tool in a.get("tools_involved", []) or []:
            if tool:
                out.append((tool.lower(), f"Achievement: {title} (tool: {tool})"))
        for skill in a.get("skills_demonstrated", []) or []:
            if skill:
                out.append((skill.lower(), f"Achievement: {title} (skill demonstrated: {skill})"))

    for c in profile.get("certifications", []):
        if c.get("name") and not c.get("in_progress"):
            out.append((c["name"].lower(), f"Certification: {c['name']}"))

    for t in profile.get("training", []):
        status = t.get("completion_status")
        if status not in ("in_progress", "enrolled", "purchased_not_started"):
            title = t.get("title") or "a training course"
            for tool in t.get("tools", []) or []:
                if tool:
                    out.append((tool.lower(), f"Training: {title} (tool: {tool})"))
            for skill in t.get("skills", []) or []:
                if skill:
                    out.append((skill.lower(), f"Training: {title} (skill: {skill})"))

    for p in profile.get("projects", []):
        name = p.get("name") or "a project"
        for tech in p.get("technologies", []) or []:
            if tech:
                out.append((tech.lower(), f"Project: {name} (technology: {tech})"))

    for ev in profile.get("evidence", []):
        title = ev.get("title") or "a recorded piece of evidence"
        for tool in ev.get("tools_involved", []) or []:
            if tool:
                out.append((tool.lower(), f"Evidence: {title} (tool: {tool})"))
        for skill in ev.get("skills_demonstrated", []) or []:
            if skill:
                out.append((skill.lower(), f"Evidence: {title} (skill: {skill})"))

    return out


def _in_progress_haystack(profile: dict) -> list[tuple[str, str]]:
    """Certifications/training the candidate is actively studying towards -
    real signal, but not held yet, so it can only ever support POSSIBLE."""
    out: list[tuple[str, str]] = []
    for c in profile.get("certifications", []):
        if c.get("in_progress") and c.get("name"):
            out.append((c["name"].lower(), f"Certification (in progress): {c['name']}"))
    for t in profile.get("training", []):
        if t.get("completion_status") in ("in_progress", "enrolled") and t.get("title"):
            out.append((t["title"].lower(), f"Training (in progress): {t['title']}"))
    return out


def _search(term_variants: set[str], haystack: list[tuple[str, str]]) -> list[str]:
    hits = []
    for text, label in haystack:
        if any(variant and variant in text for variant in term_variants):
            hits.append(label)
    # stable de-dup, cap so a very common term doesn't produce a huge source list
    seen, out = set(), []
    for h in hits:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out[:5]


def match_requirement_deterministic(requirement_name: str, profile: dict) -> Optional[dict]:
    """Returns an evidence dict if the exact-match/synonym pass resolves this
    requirement, or None if it's inconclusive and needs the LLM-assisted pass."""
    variants = expand_terms(requirement_name)
    if not variants:
        return None

    strong_hits = _search(variants, _profile_haystack(profile))
    if strong_hits:
        return {
            "evidence_level": "EXPLICIT",
            "confidence": 0.95,
            "sources": strong_hits,
            "rationale": "Matched directly against the Master CV.",
        }

    weak_hits = _search(variants, _in_progress_haystack(profile))
    if weak_hits:
        return {
            "evidence_level": "POSSIBLE",
            "confidence": 0.4,
            "sources": weak_hits,
            "rationale": "Only in-progress study towards this was found, not demonstrated experience.",
        }

    return None


def _profile_item_names(profile: dict) -> set[str]:
    """Every real, named profile item - used to verify an LLM-cited source
    actually corresponds to something in the profile rather than a plausible-
    sounding fabrication (the failure mode that produced an in-progress CISSP
    being cited as evidence of an unrelated skill - see match_scorecard.md)."""
    names: set[str] = set()
    for s in profile.get("skills", []):
        if s.get("name"):
            names.add(s["name"].lower())
    for a in profile.get("achievements", []):
        if a.get("title"):
            names.add(a["title"].lower())
    for t in profile.get("training", []):
        if t.get("title"):
            names.add(t["title"].lower())
    for p in profile.get("projects", []):
        if p.get("name"):
            names.add(p["name"].lower())
    for c in profile.get("certifications", []):
        if c.get("name"):
            names.add(c["name"].lower())
    for e in profile.get("work_experience", []):
        if e.get("company"):
            names.add(e["company"].lower())
        if e.get("role"):
            names.add(e["role"].lower())
    for ev in profile.get("evidence", []):
        if ev.get("title"):
            names.add(ev["title"].lower())
    return {n for n in names if n}


def _source_is_known(source: str, known_names: set[str]) -> bool:
    low = (source or "").lower()
    return any(name in low for name in known_names)


def _make_structure_validator(requirement_names: set[str]):
    """Checked by generate_json's retry-then-raise mechanism: catches a
    genuinely malformed response (bad enum, wrong/missing requirement
    reference, an EXPLICIT/INFERRED claim with no citation at all). Deliberately
    does NOT check whether a citation is real - one bad citation shouldn't
    cost every other requirement in the batch its legitimate classification
    (see _sanitize_evidence, which fixes that up per-entry afterwards
    instead of discarding the whole response)."""
    def _validate(parsed: dict) -> Optional[str]:
        items = parsed.get("evidence")
        if not isinstance(items, list) or not items:
            return "missing or empty 'evidence' list"
        for e in items:
            if not isinstance(e, dict):
                return "evidence entries must be objects"
            level = e.get("evidence_level")
            if level not in EVIDENCE_LEVELS:
                return f"invalid evidence_level {level!r} (must be one of {EVIDENCE_LEVELS})"
            if e.get("requirement") not in requirement_names:
                return f"evidence entry references unknown requirement {e.get('requirement')!r}"
            if level in ("EXPLICIT", "INFERRED") and not (e.get("sources") or []):
                return f"EXPLICIT/INFERRED evidence for {e.get('requirement')!r} must cite at least one source"
        return None
    return _validate


def _sanitize_evidence(parsed_evidence: list[dict], known_names: set[str]) -> list[dict]:
    """Per-entry citation check, run AFTER the structural validation above has
    already passed. An entry whose cited source doesn't correspond to a real
    profile item is downgraded to NOT_FOUND on its own - it never drags every
    other (possibly perfectly legitimate) entry in the same batch down with
    it, the way discarding the whole response and retrying would.

    Checks POSSIBLE as well as EXPLICIT/INFERRED: the structural validator
    only requires a citation for EXPLICIT/INFERRED (POSSIBLE may legitimately
    cite nothing - a vague/indirect signal with nothing specific to point to),
    but if a POSSIBLE entry DOES cite something, that citation must be just
    as real - otherwise a raw internal reference the model invented (observed
    in practice: a bare "achievements/5") passes straight through unchecked
    and downstream code (e.g. Custom CV evidence selection) sees a citation
    that looks validated but isn't."""
    out = []
    for e in parsed_evidence:
        level = e.get("evidence_level")
        sources = e.get("sources") or []
        needs_check = level in ("EXPLICIT", "INFERRED") or (level == "POSSIBLE" and sources)
        if needs_check and not any(_source_is_known(s, known_names) for s in sources):
            out.append({
                **e,
                "evidence_level": "NOT_FOUND",
                "sources": [],
                "rationale": (
                    f"Downgraded from {level}: the model cited {sources!r}, which doesn't match "
                    "any real item in the profile."
                ),
            })
        else:
            out.append(e)
    return out


# A local 8B model classifies a handful of requirements against the profile
# reliably in one call, but empirically degrades hard past that - defaulting
# most or all of a large batch to NOT_FOUND even where obvious evidence
# exists, or failing structural validation outright (see module docstring's
# "same classify-with-AI-score-in-code lesson learned elsewhere in this
# codebase for CV generation" - this is that same failure mode, here). Chunk
# rather than trust one big call with every unresolved requirement at once.
_MAX_REQUIREMENTS_PER_LLM_CALL = 6


async def match_evidence_llm(provider, unresolved_names: list[str], profile: dict, compact_profile: dict) -> dict[str, dict]:
    """LLM-assisted pass for requirements the deterministic pass couldn't
    resolve - looks for paraphrased/indirect evidence (e.g. a CV bullet that
    describes SIEM-type work without using the word "SIEM"). Every EXPLICIT or
    INFERRED result is checked against the real profile item names after the
    fact (see _sanitize_evidence) before being trusted.

    Classifies in small batches (see _MAX_REQUIREMENTS_PER_LLM_CALL) rather
    than one call for everything: a batch that fails validation stays
    NOT_FOUND for just its own requirements, not every other requirement in
    the report alongside it."""
    from ..prompt_service import fill_prompt

    if not unresolved_names:
        return {}

    known_names = _profile_item_names(profile)
    out: dict[str, dict] = {}

    for i in range(0, len(unresolved_names), _MAX_REQUIREMENTS_PER_LLM_CALL):
        chunk = unresolved_names[i:i + _MAX_REQUIREMENTS_PER_LLM_CALL]
        prompt = fill_prompt(
            "evidence_classification",
            REQUIREMENTS=json.dumps(chunk, indent=2),
            PROFILE_SUMMARY=json.dumps(compact_profile, indent=2),
        )
        try:
            parsed = await provider.generate_json(
                prompt,
                required_keys=["evidence"],
                validate=_make_structure_validator(set(chunk)),
            )
        except ValueError:
            # This chunk's classification couldn't be trusted even after a
            # retry - its requirements stay NOT_FOUND (the honest default,
            # see module docstring), but that no longer costs every other
            # chunk its legitimate classification.
            continue

        sanitized = _sanitize_evidence(parsed.get("evidence", []), known_names)
        for e in sanitized:
            out[e["requirement"]] = {
                "evidence_level": e["evidence_level"],
                "confidence": float(e.get("confidence") or 0.5),
                "sources": e.get("sources") or [],
                "rationale": e.get("rationale") or "",
            }

    return out


async def match_evidence(provider, requirements: list[dict], profile: dict, compact_profile: dict) -> list[dict]:
    """Attach evidence to every requirement. Returns new dicts (requirement
    fields + evidence fields merged) - never mutates the input requirements."""
    resolved: dict[str, dict] = {}
    unresolved: list[str] = []

    for r in requirements:
        det = match_requirement_deterministic(r["name"], profile)
        if det:
            resolved[r["name"]] = det
        else:
            unresolved.append(r["name"])

    llm_results = await match_evidence_llm(provider, unresolved, profile, compact_profile)

    out = []
    for r in requirements:
        name = r["name"]
        evidence = resolved.get(name) or llm_results.get(name) or {
            "evidence_level": "NOT_FOUND",
            "confidence": 0.5,
            "sources": [],
            "rationale": "No supporting evidence found in the Master CV.",
        }
        out.append({**r, **evidence})
    return out
