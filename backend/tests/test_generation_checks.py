import asyncio
import unittest

from app.ai.ollama_provider import OllamaProvider, _find_unsupported_claims
from app.api.applications import _unsupported_claim_skills

GAPS = ["Digital Forensics", "Forensic tools (X-Ways Forensics, Axiom, FTK)", "SentinelOne"]


class UnsupportedClaimTests(unittest.TestCase):
    def test_flags_claims_of_gap_skills(self):
        # Verbatim from a real generated letter for a Digital Forensics role.
        text = ("I am confident that my ability to conduct forensic analysis and incident response, combined "
                "with my experience in threat hunting and digital forensics, make me a strong candidate.")
        self.assertEqual(_find_unsupported_claims(text, GAPS), ["Digital Forensics", "Forensic tools (X-Ways Forensics, Axiom, FTK)"])

    def test_honest_hedges_are_fine(self):
        text = ("I haven't worked with X-Ways or Axiom directly. I have a strong interest in digital forensics "
                "and completed SANS FOR500 training as a foundation. I'm keen to develop my forensic skills.")
        self.assertEqual(_find_unsupported_claims(text, GAPS), [])

    def test_mentioning_without_claiming_is_fine(self):
        text = ("I am applying for the Digital Forensics Specialist role. I used Cortex XDR daily for containment. "
                "My experience makes me a good fit for the Digital Forensics Specialist role.")
        self.assertEqual(_find_unsupported_claims(text, GAPS), [])


class _FakeProvider(OllamaProvider):
    def __init__(self, replies):
        super().__init__("http://unused", "fake")
        self.replies = list(replies)
        self.calls = 0

    async def _chat(self, messages, temperature=0.7):
        self.calls += 1
        return self.replies.pop(0)


class CorrectionLoopTests(unittest.TestCase):
    def run_gen(self, replies, **kw):
        p = _FakeProvider(replies)
        out = asyncio.run(p.generate("prompt", banned_phrases=["moreover"], **kw))
        return out, p.calls

    def test_rechecks_each_rewrite_until_clean(self):
        out, calls = self.run_gen(["Moreover, bad.", "Moreover, still bad.", "Clean letter."], max_corrections=3)
        self.assertEqual(out, "Clean letter.")
        self.assertEqual(calls, 3)

    def test_returns_the_attempt_with_fewest_problems(self):
        replies = ["Moreover, I have experience in digital forensics.", "Moreover, fine otherwise.", "Moreover, I have experience in digital forensics."]
        out, calls = self.run_gen(replies, unsupported_claims=["Digital Forensics"], max_corrections=2)
        self.assertEqual(out, "Moreover, fine otherwise.")
        self.assertEqual(calls, 3)

    def test_default_is_a_single_correction(self):
        out, calls = self.run_gen(["Moreover, a.", "Moreover, b.", "c."])
        self.assertEqual(calls, 2)

    def test_clean_first_draft_makes_one_call(self):
        out, calls = self.run_gen(["All good."], max_corrections=3)
        self.assertEqual((out, calls), ("All good.", 1))


class UnsupportedClaimSkillsTests(unittest.TestCase):
    def test_collects_gaps_demoted_matches_and_do_not_claim_except_company(self):
        scorecard = {
            "genuine_gaps": [{"skill": "Memory analysis"}],
            "quick_learning_gaps": [{"skill": "Linux and macOS forensic analysis"}],
            "partial_matches": [
                {"skill": "Digital Forensics", "gap": "The cited evidence doesn't directly show this skill - don't present it as a strength."},
                {"skill": "EDR/XDR platforms", "gap": "Not SentinelOne specifically"},
            ],
            "do_not_claim": ["SentinelOne", "AWS"],
        }
        self.assertEqual(
            _unsupported_claim_skills(scorecard, "SentinelOne"),
            ["Memory analysis", "Linux and macOS forensic analysis", "Digital Forensics", "AWS"],
        )
        self.assertEqual(_unsupported_claim_skills(None, "x"), [])


if __name__ == "__main__":
    unittest.main()


class CurrentRoleTests(unittest.TestCase):
    def test_flags_current_role_wording_when_no_role_is_current(self):
        from app.ai.ollama_provider import _find_current_role_claims
        text = "In my current role as a Senior Security Operations Analyst, I built a SOC team."
        self.assertEqual(_find_current_role_claims(text, False), ["In my current"])
        self.assertEqual(_find_current_role_claims(text, True), [])
        self.assertEqual(_find_current_role_claims(text, None), [])
        self.assertEqual(_find_current_role_claims("In my previous role I built a SOC team.", False), [])
