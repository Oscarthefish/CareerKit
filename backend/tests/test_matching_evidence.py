import unittest

from app.services.matching.evidence import (
    _make_structure_validator,
    _profile_item_names,
    _sanitize_evidence,
    match_evidence,
    match_requirement_deterministic,
)

PROFILE = {
    "skills": [
        {"name": "Splunk", "aliases": [], "category": "tool"},
        {"name": "Security Operations Centre", "aliases": ["SOC"], "category": "hard"},
    ],
    "work_experience": [
        {
            "company": "Acme Ltd", "role": "Senior SOC Analyst",
            "technologies": ["Cortex XDR"], "key_responsibilities": ["Triaged phishing alerts"],
            "description": "", "alternative_titles": [],
        },
    ],
    "achievements": [
        {"title": "Led ransomware response", "tools_involved": ["Splunk"], "skills_demonstrated": ["Incident Response"]},
    ],
    "certifications": [
        {"name": "CompTIA Security+", "in_progress": False},
        {"name": "Certified Information Systems Security Professional (CISSP)", "in_progress": True},
    ],
    "training": [],
    "projects": [],
    "evidence": [],
}


class DeterministicMatchTests(unittest.TestCase):
    def test_exact_skill_name_is_explicit(self):
        result = match_requirement_deterministic("Splunk", PROFILE)
        self.assertIsNotNone(result)
        self.assertEqual(result["evidence_level"], "EXPLICIT")
        self.assertTrue(any("Splunk" in s for s in result["sources"]))

    def test_alias_match_is_explicit(self):
        result = match_requirement_deterministic("SOC", PROFILE)
        self.assertIsNotNone(result)
        self.assertEqual(result["evidence_level"], "EXPLICIT")

    def test_synonym_group_match_is_explicit(self):
        # requirement wording differs entirely from the profile's wording, but
        # both are in the same synonym group in synonyms.py
        result = match_requirement_deterministic("Security Operations Center", PROFILE)
        self.assertIsNotNone(result)
        self.assertEqual(result["evidence_level"], "EXPLICIT")

    def test_in_progress_cert_is_possible_not_explicit(self):
        result = match_requirement_deterministic(
            "Certified Information Systems Security Professional (CISSP)", PROFILE
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["evidence_level"], "POSSIBLE")

    def test_nothing_supports_it_returns_none_for_llm_pass(self):
        result = match_requirement_deterministic("Microsoft Sentinel", PROFILE)
        self.assertIsNone(result)


class EvidenceValidatorTests(unittest.TestCase):
    """_make_structure_validator only checks shape (enum, known requirement,
    a citation is present at all) - it deliberately does NOT judge whether a
    citation is real, so one fabricated source in a batch doesn't force a
    retry that discards every other (possibly legitimate) entry alongside it.
    That check lives in _sanitize_evidence instead (see below), and only ever
    downgrades the one bad entry."""
    def setUp(self):
        self.validator = _make_structure_validator({"Microsoft Sentinel"})

    def test_rejects_invalid_evidence_level(self):
        error = self.validator({"evidence": [{
            "requirement": "Microsoft Sentinel", "evidence_level": "CONFIRMED", "sources": [],
        }]})
        self.assertIsNotNone(error)

    def test_rejects_unrequested_requirement(self):
        error = self.validator({"evidence": [{
            "requirement": "Something Else Entirely", "evidence_level": "NOT_FOUND",
        }]})
        self.assertIsNotNone(error)

    def test_explicit_requires_a_source(self):
        error = self.validator({"evidence": [{
            "requirement": "Microsoft Sentinel", "evidence_level": "EXPLICIT", "sources": [],
        }]})
        self.assertIsNotNone(error)

    def test_well_formed_entry_passes_even_with_a_fabricated_source(self):
        # Realness of the citation is _sanitize_evidence's job, not this one -
        # see the class docstring for why.
        error = self.validator({"evidence": [{
            "requirement": "Microsoft Sentinel", "evidence_level": "EXPLICIT",
            "sources": ["Something that doesn't exist"],
        }]})
        self.assertIsNone(error)


class SanitizeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.known = _profile_item_names(PROFILE)

    def test_downgrades_fabricated_citation_to_not_found(self):
        result = _sanitize_evidence([{
            "requirement": "Microsoft Sentinel", "evidence_level": "EXPLICIT",
            "sources": ["A certification that does not exist in the profile"],
        }], self.known)
        self.assertEqual(result[0]["evidence_level"], "NOT_FOUND")
        self.assertEqual(result[0]["sources"], [])

    def test_keeps_real_citation_untouched(self):
        result = _sanitize_evidence([{
            "requirement": "Microsoft Sentinel", "evidence_level": "EXPLICIT",
            "sources": ["Achievement: Led ransomware response"],
        }], self.known)
        self.assertEqual(result[0]["evidence_level"], "EXPLICIT")

    def test_one_fabricated_entry_does_not_affect_its_siblings(self):
        # The core fix: a bad citation on one requirement must not cost every
        # other requirement in the same batch its legitimate classification.
        result = _sanitize_evidence([
            {"requirement": "A", "evidence_level": "EXPLICIT", "sources": ["nonexistent thing"]},
            {"requirement": "B", "evidence_level": "INFERRED", "sources": ["Achievement: Led ransomware response"]},
        ], self.known)
        by_req = {r["requirement"]: r for r in result}
        self.assertEqual(by_req["A"]["evidence_level"], "NOT_FOUND")
        self.assertEqual(by_req["B"]["evidence_level"], "INFERRED")

    def test_not_found_passes_through_unchanged(self):
        entry = {"requirement": "X", "evidence_level": "NOT_FOUND", "sources": [], "rationale": "nothing found"}
        result = _sanitize_evidence([entry], self.known)
        self.assertEqual(result[0], entry)


class _StubProvider:
    """A minimal AIProvider stand-in so match_evidence's orchestration can be
    tested without a real Ollama call."""
    def __init__(self, response=None, raise_error=False):
        self.response = response or {"evidence": []}
        self.raise_error = raise_error

    async def generate_json(self, prompt, system=None, required_keys=None, validate=None):
        if self.raise_error:
            raise ValueError("stub: model never produced usable JSON")
        return self.response


class MatchEvidenceOrchestrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_deterministic_hits_never_call_the_llm_for_them(self):
        requirements = [{"name": "Splunk", "type": "tool", "importance": "critical"}]
        results = await match_evidence(_StubProvider(), requirements, PROFILE, PROFILE)
        self.assertEqual(results[0]["evidence_level"], "EXPLICIT")

    async def test_unresolved_falls_back_to_not_found_when_model_unreliable(self):
        requirements = [{"name": "Microsoft Sentinel", "type": "tool", "importance": "critical"}]
        results = await match_evidence(_StubProvider(raise_error=True), requirements, PROFILE, PROFILE)
        self.assertEqual(results[0]["evidence_level"], "NOT_FOUND")

    async def test_unresolved_uses_llm_result_when_valid(self):
        requirements = [{"name": "Microsoft Sentinel", "type": "tool", "importance": "critical"}]
        provider = _StubProvider(response={"evidence": [{
            "requirement": "Microsoft Sentinel", "evidence_level": "NOT_FOUND",
            "confidence": 0.9, "sources": [], "rationale": "No SIEM/Sentinel evidence in the profile.",
        }]})
        results = await match_evidence(provider, requirements, PROFILE, PROFILE)
        self.assertEqual(results[0]["evidence_level"], "NOT_FOUND")
        self.assertEqual(results[0]["confidence"], 0.9)


if __name__ == "__main__":
    unittest.main()
