import unittest

from app.services.matching.title_match import STATE_SCORE, match_title


PROFILE = {
    "work_experience": [
        {"role": "Senior Security Operations Analyst", "alternative_titles": ["Senior SOC Analyst"]},
        {"role": "Network Security Analyst", "alternative_titles": []},
    ],
}


class _StubProvider:
    def __init__(self, response):
        self.response = response

    async def generate_json(self, prompt, system=None, required_keys=None, validate=None):
        error = validate(self.response) if validate else None
        if error:
            raise ValueError(error)
        return self.response


class TitleMatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_exact_match_short_circuits_without_calling_the_model(self):
        result = await match_title(_StubProvider({}), "Senior Security Operations Analyst", PROFILE)
        self.assertEqual(result["state"], "EXACT_MATCH")
        self.assertEqual(result["matched_title"], "Senior Security Operations Analyst")

    async def test_alternative_title_counts_as_exact_match(self):
        result = await match_title(_StubProvider({}), "Senior SOC Analyst", PROFILE)
        self.assertEqual(result["state"], "EXACT_MATCH")

    async def test_llm_classification_used_when_no_exact_match(self):
        provider = _StubProvider({
            "state": "STRONG_EQUIVALENT",
            "matched_title": "Senior Security Operations Analyst",
            "explanation": "Same role, different naming convention.",
        })
        result = await match_title(provider, "Lead SOC Analyst", PROFILE)
        self.assertEqual(result["state"], "STRONG_EQUIVALENT")
        self.assertEqual(result["matched_title"], "Senior Security Operations Analyst")

    async def test_no_candidate_titles_is_no_alignment(self):
        result = await match_title(_StubProvider({}), "Senior SOC Analyst", {"work_experience": []})
        self.assertEqual(result["state"], "NO_ALIGNMENT")

    async def test_no_job_title_is_no_alignment(self):
        result = await match_title(_StubProvider({}), "", PROFILE)
        self.assertEqual(result["state"], "NO_ALIGNMENT")

    async def test_llm_citing_a_title_not_on_record_is_rejected_and_falls_back(self):
        provider = _StubProvider({
            "state": "STRONG_EQUIVALENT",
            "matched_title": "A title the candidate never held",
            "explanation": "...",
        })
        result = await match_title(provider, "Lead SOC Analyst", PROFILE)
        # Falls back to the conservative default rather than trusting an
        # unverifiable title.
        self.assertEqual(result["state"], "RELATED_TITLE")


class StateScoreTests(unittest.TestCase):
    def test_every_state_has_a_score(self):
        for state in ("EXACT_MATCH", "STRONG_EQUIVALENT", "RELATED_TITLE", "WEAK_ALIGNMENT", "NO_ALIGNMENT"):
            self.assertIn(state, STATE_SCORE)

    def test_scores_are_monotonically_decreasing(self):
        order = ["EXACT_MATCH", "STRONG_EQUIVALENT", "RELATED_TITLE", "WEAK_ALIGNMENT", "NO_ALIGNMENT"]
        scores = [STATE_SCORE[s] for s in order]
        self.assertEqual(scores, sorted(scores, reverse=True))


if __name__ == "__main__":
    unittest.main()
