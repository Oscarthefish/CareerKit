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
import re
from typing import Optional

from .synonyms import expand_terms
from .tenure import match_tenure_requirement

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
        if role:
            out.append((role.lower(), f"Work experience: {base} (job title)"))
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


_FILLER_WORDS = {
    "strong", "excellent", "extensive", "solid", "proven", "demonstrated", "good", "advanced",
    "deep", "broad", "comprehensive", "practical", "hands-on", "hands",
    "experience", "expertise", "skills", "skill", "abilities", "ability", "knowledge",
    "understanding", "background", "platforms", "capability", "capabilities",
    "across", "in", "with", "of", "on", "the", "a", "an",
}
_COMPOUND_SPLIT = re.compile(r"\s*(?:,|/| and | & )\s*", re.IGNORECASE)


def _extract_candidate_phrases(requirement_name: str) -> list[str]:
    """Break a padded, multi-concept requirement name (e.g. "Strong expertise
    across SIEM and EDR/XDR platforms") into individual candidate phrases
    ("SIEM", "EDR", "XDR") a deterministic search can check independently.
    The exact-phrase/synonym search above only ever matches a short, specific
    term against the haystack - a JD-style sentence bundling several concepts
    together never gets a chance there even when every concept in it is
    individually well-evidenced (observed in practice: "Strong expertise
    across SIEM and EDR/XDR platforms" failing while a separately-extracted
    "SIEM and EDR/XDR platforms" requirement for the exact same thing
    succeeds). Filler words are stripped from BOTH ends of each part, since a
    qualifier like "expertise across" sits in front of the real concept just
    as often as a trailing one like "... platforms" sits behind it."""
    phrases = []
    for part in _COMPOUND_SPLIT.split(requirement_name.strip()):
        words = part.split()
        while words and words[0].lower().strip(".,") in _FILLER_WORDS:
            words.pop(0)
        while words and words[-1].lower().strip(".,") in _FILLER_WORDS:
            words.pop()
        cleaned = " ".join(words).strip()
        if cleaned:
            phrases.append(cleaned)
    return phrases


def _match_compound_requirement(requirement_name: str, profile: dict) -> Optional[dict]:
    """Fallback for a compound requirement the whole-phrase search can't
    match. Never invents coverage for a part that isn't found: EXPLICIT only
    if every extracted phrase matches, INFERRED if only some do (honestly
    naming what's still unevidenced), None if none do (falls through to the
    LLM-assisted pass as before)."""
    phrases = _extract_candidate_phrases(requirement_name)
    if len(phrases) < 2:
        return None  # not actually compound - nothing extra to try here

    matched_sources: list[str] = []
    unmatched: list[str] = []
    for phrase in phrases:
        hits = _search(expand_terms(phrase), _profile_haystack(profile))
        if hits:
            matched_sources.extend(hits)
        else:
            unmatched.append(phrase)

    if not matched_sources:
        return None
    if not unmatched:
        return {
            "evidence_level": "EXPLICIT",
            "confidence": 0.9,
            "sources": matched_sources[:5],
            "rationale": f"Matched every part of this requirement separately against the Master CV: {', '.join(phrases)}.",
        }
    return {
        "evidence_level": "INFERRED",
        "confidence": 0.6,
        "sources": matched_sources[:5],
        "rationale": (
            f"Matched {', '.join(p for p in phrases if p not in unmatched)} against the Master CV, "
            f"but found no direct evidence for: {', '.join(unmatched)}."
        ),
    }


def match_requirement_deterministic(requirement_name: str, profile: dict) -> Optional[dict]:
    """Returns an evidence dict if the exact-match/synonym pass resolves this
    requirement, or None if it's inconclusive and needs the LLM-assisted pass."""
    tenure_match = match_tenure_requirement(requirement_name, profile.get("work_experience", []))
    if tenure_match:
        return tenure_match

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

    return _match_compound_requirement(requirement_name, profile)

    return None


_MIN_FREE_TEXT_LEN = 20  # avoid short generic fragments causing loose accidental matches


def _profile_item_names(profile: dict) -> set[str]:
    """Every real, named profile item, PLUS the actual free-text content of
    responsibility/achievement/description fields - used to verify an LLM-
    cited source actually corresponds to something in the profile rather than
    a plausible-sounding fabrication (the failure mode that produced an in-
    progress CISSP being cited as evidence of an unrelated skill - see
    match_scorecard.md).

    The free-text content matters because a citation doesn't always name a
    short, distinct item - the model has also been observed embedding a full
    key_responsibility/achievement sentence verbatim inside a longer, path-
    like wrapper (e.g. "work_experience > 2022-01 > key_responsibilities >
    Acted as a technical escalation..."). _resolve_path_citation handles a
    clean index/field path with no embedded text; this handles the reverse -
    messy wrappers around text that IS genuinely real, regardless of the
    wrapper syntax, since the substring check below doesn't care about it."""
    names: set[str] = set()
    for s in profile.get("skills", []):
        if s.get("name"):
            names.add(s["name"].lower())
    for a in profile.get("achievements", []):
        if a.get("title"):
            names.add(a["title"].lower())
        for field in ("situation", "action", "result"):
            if a.get(field) and len(a[field]) >= _MIN_FREE_TEXT_LEN:
                names.add(a[field].lower())
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
        if e.get("description") and len(e["description"]) >= _MIN_FREE_TEXT_LEN:
            names.add(e["description"].lower())
        for resp in e.get("key_responsibilities", []) or []:
            if resp and len(resp) >= _MIN_FREE_TEXT_LEN:
                names.add(resp.lower())
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


_PATH_CITATION_PATTERN = re.compile(r"^[A-Za-z_]\w*(?:[./:]\w+)*$")


def _resolve_path_citation(source: str, data) -> Optional[str]:
    """If `source` looks like a pointer into the profile structure rather
    than free text - observed in practice: the model citing
    "work_experience.0.role", "work_experience:0:key_responsibilities:14", or
    "achievements/1/action" (dot, colon and slash all seen), or a bare field
    name like "professional_summary" - resolve it to the real value. Returns
    None if it doesn't look like a path, or the path doesn't resolve to real
    string/number content. Successfully resolving a path is proof by
    construction that the citation is real: there's no way to fabricate a
    path that happens to resolve to content that genuinely exists in the
    data, so a resolved citation is trusted outright rather than needing the
    substring "known name" check below."""
    if not source or not _PATH_CITATION_PATTERN.match(source.strip()):
        return None
    node = data
    for seg in re.split(r"[./:]", source.strip()):
        if isinstance(node, list):
            if not seg.isdigit() or not (0 <= int(seg) < len(node)):
                return None
            node = node[int(seg)]
        elif isinstance(node, dict):
            if seg not in node:
                return None
            node = node[seg]
        else:
            return None
    if isinstance(node, str) and node.strip():
        return node.strip()
    if isinstance(node, (int, float)) and not isinstance(node, bool):
        return str(node)
    return None


def _sanitize_evidence(parsed_evidence: list[dict], known_names: set[str], compact_profile: Optional[dict] = None) -> list[dict]:
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
    that looks validated but isn't.

    A path-shaped citation is resolved against compact_profile (the actual
    data the model was shown, so its array indices line up) before the real-
    name check - see _resolve_path_citation. The resolved, human-readable
    text replaces the raw path in the stored sources, so what's displayed to
    the user (and fed to Custom CV selection) is sensible content, never a
    bare pointer like "work_experience:0:key_responsibilities:14"."""
    out = []
    for e in parsed_evidence:
        level = e.get("evidence_level")
        raw_sources = e.get("sources") or []
        resolved_sources = []
        verified = False
        for s in raw_sources:
            resolved = _resolve_path_citation(s, compact_profile) if compact_profile is not None else None
            if resolved is not None:
                resolved_sources.append(resolved)
                verified = True
            else:
                resolved_sources.append(s)
                if _source_is_known(s, known_names):
                    verified = True

        needs_check = level in ("EXPLICIT", "INFERRED") or (level == "POSSIBLE" and raw_sources)
        if needs_check and not verified:
            out.append({
                **e,
                "evidence_level": "NOT_FOUND",
                "sources": [],
                "rationale": (
                    f"Downgraded from {level}: the model cited {raw_sources!r}, which doesn't match "
                    "any real item in the profile."
                ),
            })
        else:
            out.append({**e, "sources": resolved_sources})
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

        sanitized = _sanitize_evidence(parsed.get("evidence", []), known_names, compact_profile)
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


_PLACEHOLDER_EVIDENCE_VALUES = {"none", "n/a", "na", "-", "unspecified", "not specified", "unknown", "tbc", "tbd"}


def _evidence_is_real(evidence: str, known_names: set[str]) -> bool:
    low = (evidence or "").strip().lower()
    if not low or low in _PLACEHOLDER_EVIDENCE_VALUES:
        return False
    return _source_is_known(low, known_names)


def sanitize_scorecard(scorecard: dict, profile: dict) -> dict:
    """Safety net for the (older, separate) Match Scorecard feature -
    match_scorecard.md instructs the model to cite a specific real profile
    item as "evidence" for every strong match, and to never claim a strong
    match without one, but - unlike the Job Match evidence engine above -
    nothing enforces that rule in code. Observed in practice: the model
    listing a skill under "strong_matches" with the evidence field literally
    set to the string "None". Move any "strong_matches" entry whose evidence
    is missing, a placeholder, or doesn't correspond to a real profile item
    into "do_not_claim" instead, rather than let an unverifiable "strong
    match" reach the user - the same downgrade-rather-than-discard principle
    _sanitize_evidence uses above, applied to this older feature's output."""
    known_names = _profile_item_names(profile)
    result = dict(scorecard)
    do_not_claim = list(result.get("do_not_claim") or [])

    kept_strong = []
    for m in result.get("strong_matches") or []:
        evidence = m.get("evidence") if isinstance(m, dict) else None
        if isinstance(m, dict) and _evidence_is_real(evidence, known_names):
            kept_strong.append(m)
        elif isinstance(m, dict) and m.get("skill"):
            do_not_claim.append(m["skill"])

    result["strong_matches"] = kept_strong
    result["do_not_claim"] = do_not_claim
    return result
