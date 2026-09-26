import unittest

from app.services.matching.recommendations import build_priority_fixes, safety_tier


def _req(name, type_, importance, evidence_level, sources=None):
    return {
        "name": name, "type": type_, "importance": importance,
        "evidence_level": evidence_level, "confidence": 0.9, "sources": sources or [],
    }


class SafetyTierTests(unittest.TestCase):
    def test_explicit_needs_no_fix(self):
        self.assertIsNone(safety_tier(_req("Splunk", "tool", "critical", "EXPLICIT")))

    def test_inferred_is_safe_optimisation(self):
        self.assertEqual(safety_tier(_req("SIEM", "tool", "critical", "INFERRED")), "SAFE_OPTIMISATION")

    def test_possible_is_evidence_needed(self):
        self.assertEqual(safety_tier(_req("CISSP", "certification", "critical", "POSSIBLE")), "EVIDENCE_NEEDED")

    def test_missing_certification_is_do_not_add(self):
        self.assertEqual(safety_tier(_req("CISSP", "certification", "critical", "NOT_FOUND")), "DO_NOT_ADD")

    def test_missing_skill_is_evidence_needed_not_do_not_add(self):
        # A skill/tool could genuinely be undocumented experience - unlike a
        # certification, it isn't binary, so it must never be auto-blocked.
        self.assertEqual(safety_tier(_req("Microsoft Sentinel", "tool", "critical", "NOT_FOUND")), "EVIDENCE_NEEDED")

    def test_no_evidence_level_can_ever_yield_safe_optimisation_for_not_found(self):
        # The core safety invariant: nothing about a NOT_FOUND requirement -
        # whatever its type or importance - can produce SAFE_OPTIMISATION.
        for type_ in ("hard_skill", "tool", "methodology", "responsibility", "certification", "industry", "soft_skill"):
            for importance in ("critical", "important", "desirable"):
                tier = safety_tier(_req("X", type_, importance, "NOT_FOUND"))
                self.assertIn(tier, ("DO_NOT_ADD", "EVIDENCE_NEEDED"))
                self.assertNotEqual(tier, "SAFE_OPTIMISATION")


class BuildPriorityFixesTests(unittest.TestCase):
    def test_explicit_requirements_produce_no_fix(self):
        reqs = [_req("Splunk", "tool", "critical", "EXPLICIT")]
        fixes = build_priority_fixes(reqs, {"state": None})
        self.assertEqual(fixes["top"], [])
        self.assertEqual(fixes["more"], [])

    def test_critical_gaps_ranked_above_low_severity(self):
        reqs = [
            _req("SIEM", "tool", "desirable", "INFERRED"),
            _req("CISSP", "certification", "critical", "NOT_FOUND"),
        ]
        fixes = build_priority_fixes(reqs, {"state": None})
        self.assertEqual(fixes["top"][0]["requirement"], "CISSP")
        self.assertEqual(fixes["top"][0]["tier"], "DO_NOT_ADD")

    def test_limit_splits_top_and_more(self):
        reqs = [_req(f"Req{i}", "hard_skill", "critical", "NOT_FOUND") for i in range(10)]
        fixes = build_priority_fixes(reqs, {"state": None}, limit=3)
        self.assertEqual(len(fixes["top"]), 3)
        self.assertEqual(len(fixes["more"]), 7)

    def test_strong_equivalent_title_adds_a_safe_alignment_suggestion(self):
        reqs = []
        title_match = {"state": "STRONG_EQUIVALENT", "matched_title": "Senior Security Operations Analyst", "job_title": "Senior SOC Analyst"}
        fixes = build_priority_fixes(reqs, title_match)
        self.assertEqual(len(fixes["top"]), 1)
        self.assertEqual(fixes["top"][0]["tier"], "SAFE_OPTIMISATION")
        self.assertIn("Senior Security Operations Analyst", fixes["top"][0]["message"])


if __name__ == "__main__":
    unittest.main()
