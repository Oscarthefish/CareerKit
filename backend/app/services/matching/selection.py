"""Evidence-based selection for Custom CV generation.

A Custom CV should not be the Master CV with a few words changed - it should
select and prioritise the strongest relevant evidence for THIS job (see
custom_cv_generate.md). This module decides what to include, deterministically
and without any LLM call: relevance is purely a function of the Job Match
report already computed for the application - specifically its
requirement -> evidence -> source mapping, where "sources" are profile item
names already validated as real (see matching/evidence.py's citation check,
which downgrades any fabricated citation to NOT_FOUND before it ever reaches
this module). Same "classify with AI, decide in code" split used throughout
this package.
"""

# Evidence-strength multiplier, reusing the *stored* "coverage" field from a
# job_match_result's requirement_coverage/hard_skills tables (STRONG_EVIDENCE
# / PARTIAL_EVIDENCE / NO_EVIDENCE / UNKNOWN) rather than needing the raw
# EXPLICIT/INFERRED/POSSIBLE/NOT_FOUND evidence_level, which isn't persisted.
# A row with no evidence has no sources anyway, so it never contributes.
COVERAGE_WEIGHT = {"STRONG_EVIDENCE": 1.0, "PARTIAL_EVIDENCE": 0.6, "NO_EVIDENCE": 0.0, "UNKNOWN": 0.0}

# critical/important/desirable - same weights as scoring.py's IMPORTANCE_WEIGHT,
# duplicated rather than imported to keep this module usable with only a
# job_match_result dict on hand (no need to re-import the scoring module's
# other, unrelated constants).
IMPORTANCE_WEIGHT = {"critical": 3, "important": 2, "desirable": 1}

# How many of a role's key_responsibilities bullets survive, by recency
# position (0 = most recent role) - richest detail for recent roles, terse
# for old ones, matching the "recent roles richest detail, older concise"
# principle. A role's heading is always kept regardless (see
# select_responsibilities) so the timeline never shows a gap.
BULLET_BUDGET_BY_POSITION = [6, 6, 4, 4]
DEFAULT_OLDER_ROLE_BUDGET = 2

MIN_ACHIEVEMENTS = 4
MAX_ACHIEVEMENTS = 8

# A real job description's evidence coverage is often sparse for reasons that
# have nothing to do with the candidate's actual skill set (a batched local-
# model classification pass simply doesn't catch every match) - filtering
# Key Skills down to ONLY what got positively cited can leave a real CV with
# an unnaturally bare skills section, or a whole category (e.g. "Leadership &
# People") with nothing in it at all. Keep at least this many, backfilling
# with the rest of the candidate's real skills (unfiltered, in their existing
# order) rather than ever showing fewer than a normal CV would.
MIN_SKILLS = 15


def relevance_scores(requirement_coverage: list[dict]) -> dict[str, float]:
    """{lowercased source string -> accumulated relevance score} from a
    stored job_match_result's requirement_coverage list (or hard_skills -
    either has the same {importance, coverage, sources} shape)."""
    scores: dict[str, float] = {}
    for row in requirement_coverage or []:
        strength = COVERAGE_WEIGHT.get(row.get("coverage"), 0.0)
        if strength <= 0:
            continue
        weight = IMPORTANCE_WEIGHT.get(row.get("importance"), 1)
        contribution = weight * strength
        for source in row.get("sources") or []:
            key = (source or "").strip().lower()
            if key:
                scores[key] = scores.get(key, 0.0) + contribution
    return scores


def score_for_name(name: str, source_scores: dict[str, float]) -> float:
    """A profile item's relevance is the sum of every cited source whose text
    contains the item's name - the same substring direction evidence.py uses
    to validate a citation in the first place (the profile item's name is a
    substring of the source text, e.g. source "Splunk Enterprise Security
    (daily use)" for item name "Splunk Enterprise Security")."""
    name_l = (name or "").strip().lower()
    if not name_l:
        return 0.0
    return sum(score for source, score in source_scores.items() if name_l in source)


def _bullet_score(bullet: str, source_scores: dict[str, float]) -> float:
    """The reverse direction from score_for_name: here the source/profile-item
    name is usually the shorter string and the bullet the longer one, so check
    whether the source text appears inside the bullet."""
    bullet_l = (bullet or "").lower()
    return sum(score for source, score in source_scores.items() if source and source in bullet_l)


def select_skills(skills: list[dict], source_scores: dict[str, float]) -> list[dict]:
    """Rank skills by relevance to this job, cited ones first. If evidence
    coverage is too sparse to reach MIN_SKILLS on citations alone, backfill
    with the rest of the candidate's real skills (in their original order)
    rather than ever showing an unnaturally thin - or entirely empty -
    section: sparse Job Match coverage reflects the matching pass's own
    limits at least as often as it reflects an actual skill gap, and a
    Custom CV should not visibly punish the candidate for that."""
    scored = [(s, score_for_name(s.get("name", ""), source_scores)) for s in skills]
    cited = sorted((pair for pair in scored if pair[1] > 0), key=lambda pair: pair[1], reverse=True)
    selected = [s for s, _ in cited]

    floor = min(MIN_SKILLS, len(skills))
    if len(selected) < floor:
        selected_ids = {id(s) for s in selected}
        for s, _ in scored:
            if len(selected) >= floor:
                break
            if id(s) not in selected_ids:
                selected.append(s)
                selected_ids.add(id(s))
    return selected


def select_achievements(achievements: list[dict], source_scores: dict[str, float]) -> list[dict]:
    """Rank achievements by relevance to this job and cap at MAX_ACHIEVEMENTS.
    If fewer than MIN_ACHIEVEMENTS are actually cited by a requirement,
    backfill with the next-best (in original order) so a sparse job
    description doesn't produce a barren achievements section."""
    scored = sorted(
        enumerate(achievements),
        key=lambda pair: score_for_name(pair[1].get("title", ""), source_scores),
        reverse=True,
    )
    floor = min(MIN_ACHIEVEMENTS, len(achievements))
    cited = [a for i, a in scored if score_for_name(a.get("title", ""), source_scores) > 0]
    selected = cited[:MAX_ACHIEVEMENTS]
    if len(selected) < floor:
        selected_ids = {id(a) for a in selected}
        for i, a in scored:
            if len(selected) >= floor:
                break
            if id(a) not in selected_ids:
                selected.append(a)
                selected_ids.add(id(a))
    return selected


def select_responsibilities(work_experience: list[dict], source_scores: dict[str, float]) -> list[dict]:
    """Returns a NEW list of experience dicts (never mutates the input) with
    key_responsibilities trimmed to each role's highest-relevance bullets,
    budgeted more generously for recent roles than old ones. A role's heading
    survives even if none of its bullets do."""
    trimmed = []
    for position, exp in enumerate(work_experience):
        budget = (
            BULLET_BUDGET_BY_POSITION[position]
            if position < len(BULLET_BUDGET_BY_POSITION)
            else DEFAULT_OLDER_ROLE_BUDGET
        )
        responsibilities = exp.get("key_responsibilities") or []
        ranked = sorted(responsibilities, key=lambda r: _bullet_score(r, source_scores), reverse=True)
        top = set(ranked[:budget])
        # Keep the surviving bullets in their original order rather than
        # score order - reads as a coherent list of duties, not a ranked one.
        new_exp = dict(exp)
        new_exp["key_responsibilities"] = [r for r in responsibilities if r in top]
        trimmed.append(new_exp)
    return trimmed


def select_projects(projects: list[dict], source_scores: dict[str, float]) -> list[dict]:
    """Keep a project only if it's cited by a requirement - unless there are
    so few projects overall (<=2) that dropping the only portfolio evidence
    would do more harm than including something slightly less relevant."""
    scored = [(p, score_for_name(p.get("name", ""), source_scores)) for p in projects]
    cited = [p for p, sc in scored if sc > 0]
    if cited or len(projects) > 2:
        return cited
    return list(projects)


# See MIN_SKILLS above for why a floor matters here too: sparse evidence
# coverage against a batched local-model classification pass reflects that
# pass's own limits at least as often as an actual capability gap, and has
# been observed dropping whole, clearly-relevant tool categories (EDR/XDR,
# firewalls) down to just one surviving line. Below this many surviving
# category lines, trust the full list over a thin filtered one instead of
# trying to partially backfill within a category.
MIN_TOOL_CATEGORY_LINES = 5


def select_platforms_and_tools(tools_lines: list[str], source_scores: dict[str, float]) -> list[str]:
    """platforms_and_tools_display lines look like "Category: Product A,
    Product B" - filter each line's product list to cited products only,
    dropping the whole line if nothing in it is cited for this job. Falls
    back to the full list if too few categories survive filtering."""
    filtered = []
    for line in tools_lines:
        if ":" not in line:
            filtered.append(line)
            continue
        category, _, rest = line.partition(":")
        products = [p.strip() for p in rest.split(",") if p.strip()]
        cited = [p for p in products if score_for_name(p, source_scores) > 0]
        if cited:
            filtered.append(f"{category.strip()}: {', '.join(cited)}")
    if len(filtered) >= min(MIN_TOOL_CATEGORY_LINES, len(tools_lines)):
        return filtered
    return list(tools_lines)


def select_evidence_for_cv(profile: dict, requirement_coverage: list[dict]) -> dict:
    """Returns a new profile dict (same shape as build_profile_summary's
    output, safe to pass straight into apply_cv_safety_nets and the custom CV
    prompt) with skills/achievements/work_experience/projects/platforms-and-
    tools filtered and trimmed to the strongest evidence for this specific
    job. Certifications, training, education and community_involvement are
    left untouched - short, low-cost, and not something the tailoring spec
    asks to filter."""
    scores = relevance_scores(requirement_coverage)
    selected = dict(profile)
    selected["skills"] = select_skills(profile.get("skills", []), scores)
    selected["achievements"] = select_achievements(profile.get("achievements", []), scores)
    selected["work_experience"] = select_responsibilities(profile.get("work_experience", []), scores)
    selected["projects"] = select_projects(profile.get("projects", []), scores)
    selected["platforms_and_tools_display"] = select_platforms_and_tools(
        profile.get("platforms_and_tools_display", []), scores
    )
    return selected
