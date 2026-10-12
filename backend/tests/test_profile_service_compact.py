import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.profile_service import compact_profile_for_prompt


class CompactProfileForPromptAchievementsTests(unittest.TestCase):
    def test_ownership_field_passed_through(self):
        summary = {
            "achievements": [{
                "title": "Helped build a global 24/7 SOC across three locations",
                "situation": "A new region needed round-the-clock coverage.",
                "action": "Helped build the local team.",
                "result": "6-person team delivered.",
                "tools_involved": [],
                "skills_demonstrated": [],
                "confidence": "confirmed_hands_on",
                "ownership": "significant_contributor",
                "employer": "timbre Digital",
                "date_range": "2020-2022",
            }],
        }
        compact = compact_profile_for_prompt(summary)
        self.assertEqual(compact["achievements"][0]["ownership"], "significant_contributor")

    def test_missing_ownership_passes_through_as_none(self):
        summary = {"achievements": [{"title": "X", "confidence": "confirmed_hands_on"}]}
        compact = compact_profile_for_prompt(summary)
        self.assertIsNone(compact["achievements"][0]["ownership"])

    def test_compact_achievement_does_not_leak_employer_or_date_range(self):
        # compact_profile_for_prompt trims the profile down for the smaller
        # interview-prep/scorecard prompt context - employer/date_range are
        # not part of that trimmed shape (unlike the full build_profile_summary
        # result, which match_scorecard.md uses directly), only ownership is.
        summary = {"achievements": [{
            "title": "X", "confidence": "confirmed_hands_on",
            "ownership": "led", "employer": "Acme", "date_range": "2019-2020",
        }]}
        compact = compact_profile_for_prompt(summary)
        self.assertNotIn("employer", compact["achievements"][0])
        self.assertNotIn("date_range", compact["achievements"][0])


class CompactProfileForPromptClarificationsTests(unittest.TestCase):
    def test_clarifications_passed_through(self):
        summary = {
            "clarifications": [
                {"applies_to": "Ransomware response achievement", "statement": "I was not Incident Commander."},
            ],
        }
        compact = compact_profile_for_prompt(summary)
        self.assertEqual(compact["clarifications"], summary["clarifications"])

    def test_missing_clarifications_passes_through_as_empty_list(self):
        compact = compact_profile_for_prompt({})
        self.assertEqual(compact["clarifications"], [])


if __name__ == "__main__":
    unittest.main()
