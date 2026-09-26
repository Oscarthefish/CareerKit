"""Shared controlled vocabularies for the career-data model.

Kept as plain string constants (not DB enums) so SQLite migrations stay
additive and simple, per the existing migration pattern in database.py.
"""

# How sure we are about a skill/tool/achievement/project/evidence claim,
# and therefore how (or whether) it should appear in generated content.
# Ordered roughly from strongest to weakest claim.
CONFIDENCE_LEVELS = [
    "confirmed_hands_on",   # verified production/operational experience
    "working_knowledge",    # used it, not deep production experience
    "training_exposure",    # completed training but no confirmed production use
    "familiarity",          # conceptual familiarity only
    "interest",             # planned learning / declared interest, not experience
    "unverified",           # claim exists but has no supporting evidence yet
    "do_not_include",       # explicitly excluded from any generated output
]

# Confidence levels that are safe to present as some form of real experience
# (wording still differs a lot between these tiers — see prompts).
EXPERIENCE_TIERS = {"confirmed_hands_on", "working_knowledge", "training_exposure"}

# Confidence levels that must never be silently promoted into a CV as
# production experience. They can still be mentioned as interest/learning.
SOFT_TIERS = {"familiarity", "interest"}

# Never surfaced in generated output at all.
EXCLUDED_TIERS = {"unverified", "do_not_include"}

# Legacy values already used by Achievement/Project/EvidenceItem before this
# extension — mapped onto the new vocabulary so existing data keeps working.
LEGACY_CONFIDENCE_MAP = {
    "confirmed": "confirmed_hands_on",
    "inferred": "working_knowledge",
    "weak": "unverified",
    "do_not_use": "do_not_include",
}


def normalise_confidence(value: str | None) -> str:
    if not value:
        return "unverified"
    return LEGACY_CONFIDENCE_MAP.get(value, value)


# Who is allowed to see a piece of career data.
CONFIDENTIALITY_LEVELS = [
    "public",           # safe for a public CV, LinkedIn, or website
    "cv_safe",          # fine on any CV, not necessarily broadcast publicly
    "recruiter_only",   # only shared directly with a recruiter/employer
    "interview_only",   # only discussed verbally in an interview, never written
    "confidential",     # not to be used in generated output at all
    "do_not_use",       # excluded entirely
]

# Confidentiality levels allowed for each generation mode.
CONFIDENTIALITY_MODE_ALLOWLIST = {
    "full": {"public", "cv_safe", "recruiter_only", "interview_only"},
    "cv_safe": {"public", "cv_safe"},
    "recruiter": {"public", "cv_safe", "recruiter_only"},
    "linkedin": {"public"},
    "interview_prep": {"public", "cv_safe", "recruiter_only", "interview_only"},
}

DEFAULT_MODE = "cv_safe"
