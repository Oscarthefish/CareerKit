import unittest

from app.services.matching.evidence import (
    _MAX_REQUIREMENTS_PER_LLM_CALL,
    _evidence_is_real,
    _make_structure_validator,
    _profile_item_names,
    _sanitize_evidence,
    match_evidence,
    match_evidence_llm,
    match_requirement_deterministic,
    sanitize_scorecard,
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

    def test_possible_with_no_source_passes_through_unchanged(self):
        # POSSIBLE is allowed to cite nothing at all (a vague/indirect signal) -
        # only a GIVEN citation needs to be real.
        entry = {"requirement": "X", "evidence_level": "POSSIBLE", "sources": [], "rationale": "vague signal"}
        result = _sanitize_evidence([entry], self.known)
        self.assertEqual(result[0], entry)

    def test_possible_with_a_fabricated_or_garbage_citation_is_downgraded(self):
        # Observed in practice: a local model citing a raw internal-looking
        # reference like "achievements/5" instead of a real item name.
        result = _sanitize_evidence([{
            "requirement": "X", "evidence_level": "POSSIBLE", "sources": ["achievements/5"],
        }], self.known)
        self.assertEqual(result[0]["evidence_level"], "NOT_FOUND")
        self.assertEqual(result[0]["sources"], [])

    def test_possible_with_a_real_citation_is_kept(self):
        result = _sanitize_evidence([{
            "requirement": "X", "evidence_level": "POSSIBLE",
            "sources": ["Achievement: Led ransomware response"],
        }], self.known)
        self.assertEqual(result[0]["evidence_level"], "POSSIBLE")


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


class MatchEvidenceLlmChunkingTests(unittest.IsolatedAsyncioTestCase):
    async def test_splits_a_large_unresolved_list_into_multiple_calls(self):
        calls: list[set] = []

        class Provider:
            async def generate_json(self, prompt, system=None, required_keys=None, validate=None):
                # Reconstruct which chunk this call covers from the requirement
                # names actually embedded in the prompt.
                chunk = [n for n in unresolved if n in prompt]
                calls.append(set(chunk))
                return {"evidence": [
                    {"requirement": n, "evidence_level": "NOT_FOUND", "sources": [], "confidence": 0.0}
                    for n in chunk
                ]}

        unresolved = [f"Requirement {i}" for i in range(_MAX_REQUIREMENTS_PER_LLM_CALL * 2 + 1)]
        result = await match_evidence_llm(Provider(), unresolved, PROFILE, PROFILE)

        self.assertEqual(len(calls), 3)  # 6 + 6 + 1, with the default batch size
        self.assertEqual(len(result), len(unresolved))

    async def test_one_failing_chunk_does_not_cost_other_chunks_their_results(self):
        class Provider:
            def __init__(self):
                self.call_count = 0

            async def generate_json(self, prompt, system=None, required_keys=None, validate=None):
                self.call_count += 1
                if self.call_count == 1:
                    raise ValueError("stub: this chunk's model output was never usable")
                chunk = [n for n in unresolved if n in prompt]
                return {"evidence": [
                    {
                        "requirement": n, "evidence_level": "EXPLICIT", "confidence": 0.9,
                        "sources": ["Achievement: Led ransomware response"],
                    }
                    for n in chunk
                ]}

        unresolved = [f"Requirement {i}" for i in range(_MAX_REQUIREMENTS_PER_LLM_CALL + 1)]
        result = await match_evidence_llm(Provider(), unresolved, PROFILE, PROFILE)

        # First chunk (the failing one) contributes nothing - its requirements
        # simply aren't in the result (callers treat "missing" as NOT_FOUND).
        first_chunk_names = set(unresolved[:_MAX_REQUIREMENTS_PER_LLM_CALL])
        second_chunk_names = set(unresolved[_MAX_REQUIREMENTS_PER_LLM_CALL:])
        self.assertFalse(first_chunk_names & set(result.keys()))
        self.assertTrue(second_chunk_names <= set(result.keys()))
        for name in second_chunk_names:
            self.assertEqual(result[name]["evidence_level"], "EXPLICIT")

    async def test_small_list_makes_a_single_call(self):
        calls = []

        class Provider:
            async def generate_json(self, prompt, system=None, required_keys=None, validate=None):
                calls.append(1)
                return {"evidence": [{"requirement": "Only one", "evidence_level": "NOT_FOUND", "sources": []}]}

        await match_evidence_llm(Provider(), ["Only one"], PROFILE, PROFILE)
        self.assertEqual(len(calls), 1)


class EvidenceIsRealTests(unittest.TestCase):
    def setUp(self):
        self.known = _profile_item_names(PROFILE)

    def test_the_literal_string_none_is_not_real_evidence(self):
        self.assertFalse(_evidence_is_real("None", self.known))
        self.assertFalse(_evidence_is_real("none", self.known))

    def test_other_placeholder_values_are_not_real_evidence(self):
        for placeholder in ("N/A", "-", "unspecified", "TBC", ""):
            self.assertFalse(_evidence_is_real(placeholder, self.known))

    def test_a_real_profile_item_reference_is_real_evidence(self):
        self.assertTrue(_evidence_is_real("Achievement: Led ransomware response", self.known))

    def test_a_fabricated_reference_is_not_real_evidence(self):
        self.assertFalse(_evidence_is_real("Something that doesn't exist in the profile", self.known))


class SanitizeScorecardTests(unittest.TestCase):
    def test_moves_a_none_evidence_strong_match_to_do_not_claim(self):
        scorecard = {
            "strong_matches": [{"skill": "NIST CSF", "evidence": "None"}],
            "do_not_claim": [],
        }
        result = sanitize_scorecard(scorecard, PROFILE)
        self.assertEqual(result["strong_matches"], [])
        self.assertIn("NIST CSF", result["do_not_claim"])

    def test_keeps_a_strong_match_with_real_evidence(self):
        scorecard = {
            "strong_matches": [{"skill": "Incident Response", "evidence": "Achievement: Led ransomware response"}],
            "do_not_claim": [],
        }
        result = sanitize_scorecard(scorecard, PROFILE)
        self.assertEqual(len(result["strong_matches"]), 1)
        self.assertEqual(result["strong_matches"][0]["skill"], "Incident Response")

    def test_moves_a_fabricated_evidence_strong_match_to_do_not_claim(self):
        scorecard = {
            "strong_matches": [{"skill": "Cloud Security", "evidence": "Extensive cloud security background"}],
            "do_not_claim": [],
        }
        result = sanitize_scorecard(scorecard, PROFILE)
        self.assertEqual(result["strong_matches"], [])
        self.assertIn("Cloud Security", result["do_not_claim"])

    def test_preserves_existing_do_not_claim_entries(self):
        scorecard = {
            "strong_matches": [{"skill": "X", "evidence": "None"}],
            "do_not_claim": ["Already listed gap"],
        }
        result = sanitize_scorecard(scorecard, PROFILE)
        self.assertIn("Already listed gap", result["do_not_claim"])
        self.assertIn("X", result["do_not_claim"])

    def test_missing_strong_matches_key_does_not_crash(self):
        result = sanitize_scorecard({"do_not_claim": []}, PROFILE)
        self.assertEqual(result["strong_matches"], [])

    def test_does_not_mutate_the_input_scorecard(self):
        scorecard = {"strong_matches": [{"skill": "X", "evidence": "None"}], "do_not_claim": []}
        import copy
        before = copy.deepcopy(scorecard)
        sanitize_scorecard(scorecard, PROFILE)
        self.assertEqual(scorecard, before)


if __name__ == "__main__":
    unittest.main()
