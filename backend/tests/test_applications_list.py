import json
import unittest
from unittest.mock import Mock

from app.api.applications import (
    _ensure_forced_matches_mentioned,
    _ensure_tool_gap_bridge_mentioned,
    _export_download_name,
    _job_match_summary,
)


class JobMatchSummaryTests(unittest.TestCase):
    def test_extracts_score_and_band_from_stored_json(self):
        stored = json.dumps({"job_match": {"overall": 26, "band": "Significant gaps"}})
        score, band = _job_match_summary(stored)
        self.assertEqual(score, 26)
        self.assertEqual(band, "Significant gaps")

    def test_none_input_returns_none_none(self):
        self.assertEqual(_job_match_summary(None), (None, None))

    def test_empty_string_returns_none_none(self):
        self.assertEqual(_job_match_summary(""), (None, None))

    def test_malformed_json_does_not_crash(self):
        self.assertEqual(_job_match_summary("not valid json"), (None, None))

    def test_missing_job_match_key_returns_none_none(self):
        self.assertEqual(_job_match_summary(json.dumps({"other_field": 1})), (None, None))


def _app(company=None, role=None):
    return Mock(company=company, role=role)


class ExportDownloadNameTests(unittest.TestCase):
    def test_builds_company_role_label_for_custom_cv(self):
        name = _export_download_name(_app("Xero", "Senior Security Operations Analyst"), "custom-cv")
        self.assertEqual(name, "Xero - Senior Security Operations Analyst - Custom CV")

    def test_falls_back_to_the_label_alone_when_company_and_role_are_unset(self):
        name = _export_download_name(_app(), "custom-cv")
        self.assertEqual(name, "Custom CV")

    def test_uses_a_titled_fallback_label_for_an_unmapped_section(self):
        name = _export_download_name(_app("Xero", "SOC Analyst"), "cv-notes")
        self.assertEqual(name, "Xero - SOC Analyst - CV Notes")

    def test_strips_filesystem_unsafe_characters_from_company_and_role(self):
        name = _export_download_name(_app('Acme/Co: "Best"', "Lead <Analyst>"), "custom-cv")
        self.assertEqual(name, "AcmeCo Best - Lead Analyst - Custom CV")

    def test_role_only_omits_the_missing_company_cleanly(self):
        name = _export_download_name(_app(None, "SOC Analyst"), "custom-cv")
        self.assertEqual(name, "SOC Analyst - Custom CV")


class EnsureForcedMatchesMentionedTests(unittest.TestCase):
    def test_real_regression_appends_a_sentence_for_a_missing_forced_skill_match(self):
        # Verbatim shape of the real bug: a forced strong_matches entry for
        # a skill ("Physical Security / Lock Bypass (Locksport)") - correct
        # and present - but the generated letter never mentioned it at
        # all, defaulting entirely to generic SOC/incident-response content.
        letter = (
            "Kia ora,\n\n"
            "I am writing to express my interest in the IT Support Engineer role.\n\n"
            "I have over eight years of experience in Security Operations roles, "
            "investigating incidents across SIEM and EDR platforms.\n\n"
            "Sincerely,\nJason Hill"
        )
        scorecard = {
            "strong_matches": [
                {"skill": "Incident Response", "evidence": "Achievement: Led ransomware response"},
                {
                    "skill": "exposure to cyber and/or physical security systems",
                    "evidence": "Skill: Physical Security / Lock Bypass (Locksport)",
                    "forced": True,
                },
            ]
        }
        result = _ensure_forced_matches_mentioned(letter, scorecard)
        self.assertIn("Physical Security / Lock Bypass (Locksport)", result)
        self.assertIn("Sincerely", result)
        # Inserted before the sign-off, not tacked on after it.
        self.assertLess(result.index("Physical Security"), result.index("Sincerely"))

    def test_achievement_evidence_is_phrased_as_a_first_person_sentence(self):
        letter = "Kia ora,\n\nSome generic content here about SIEM and EDR.\n\nSincerely,\nJason Hill"
        scorecard = {
            "strong_matches": [{
                "skill": "manage, maintain, and document physical security",
                "evidence": "Achievement: Tested physical security of the Auckland office via lock bypass techniques",
                "forced": True,
            }]
        }
        result = _ensure_forced_matches_mentioned(letter, scorecard)
        self.assertIn("I tested physical security of the Auckland office", result)

    def test_does_not_duplicate_a_match_already_substantively_mentioned(self):
        letter = (
            "Kia ora,\n\n"
            "My background includes hands-on experience with Physical Security / Lock Bypass "
            "(Locksport), gained while testing office access controls.\n\n"
            "Sincerely,\nJason Hill"
        )
        scorecard = {
            "strong_matches": [{
                "skill": "exposure to cyber and/or physical security systems",
                "evidence": "Skill: Physical Security / Lock Bypass (Locksport)",
                "forced": True,
            }]
        }
        result = _ensure_forced_matches_mentioned(letter, scorecard)
        self.assertEqual(result, letter)

    def test_ignores_non_forced_matches(self):
        letter = "Kia ora,\n\nSome generic content.\n\nSincerely,\nJason Hill"
        scorecard = {
            "strong_matches": [{
                "skill": "exposure to cyber and/or physical security systems",
                "evidence": "Skill: Physical Security / Lock Bypass (Locksport)",
            }]
        }
        result = _ensure_forced_matches_mentioned(letter, scorecard)
        self.assertEqual(result, letter)

    def test_appends_at_the_end_when_no_sign_off_is_found(self):
        letter = "Just some body text with no sign-off line at all."
        scorecard = {
            "strong_matches": [{
                "skill": "exposure to cyber and/or physical security systems",
                "evidence": "Skill: Physical Security / Lock Bypass (Locksport)",
                "forced": True,
            }]
        }
        result = _ensure_forced_matches_mentioned(letter, scorecard)
        self.assertTrue(result.startswith(letter))
        self.assertIn("Physical Security / Lock Bypass (Locksport)", result)

    def test_empty_scorecard_returns_letter_unchanged(self):
        letter = "Kia ora,\n\nSome content.\n\nSincerely,\nJason Hill"
        self.assertEqual(_ensure_forced_matches_mentioned(letter, {}), letter)


class EnsureToolGapBridgeMentionedTests(unittest.TestCase):
    def test_real_regression_inserts_before_the_closing_kia_ora_not_the_opening_one(self):
        # Verbatim shape of a real placement bug: the model used "Kia ora,"
        # as BOTH the opening greeting and the closing sign-off in the same
        # letter. The bridge must land before the CLOSING one, not get
        # appended after the whole letter (including the signature) just
        # because the opening "Kia ora," isn't the one that matters.
        letter = (
            "Kia ora,\n\nI bring over eight years of SOC experience, with hands-on work in "
            "Splunk Enterprise Security.\n\nI would welcome the chance to discuss this further.\n\n"
            "Kia ora,\nJason Hill"
        )
        scorecard = {"genuine_gaps": [{"skill": "Microsoft Sentinel", "impact": "x"}]}
        profile = {"skills": [{"name": "Splunk Enterprise Security", "tool_category": "SIEM", "confidence": "confirmed_hands_on"}]}
        result = _ensure_tool_gap_bridge_mentioned(letter, scorecard, profile)
        self.assertIn("Microsoft Sentinel", result)
        # The bridge text must appear BEFORE the final "Jason Hill" line,
        # not bolted on after the whole signed letter.
        self.assertLess(result.index("Microsoft Sentinel"), result.rindex("Jason Hill"))

    def test_real_regression_bridges_a_siem_gap_to_the_candidates_real_siem(self):
        # Verbatim shape of the real bug: a real cover letter for a SOC
        # Analyst role never once mentioned Microsoft Sentinel, CrowdStrike
        # Falcon/NG-SIEM or Rapid7 InsightIDR, despite the Scorecard
        # already correctly flagging all three as gaps against the
        # candidate's real Splunk Enterprise Security / Cortex XDR
        # experience.
        letter = (
            "Kia ora,\n\nI bring over eight years of SOC experience, with hands-on work in "
            "Splunk Enterprise Security and Cortex XDR.\n\nSincerely,\nJason Hill"
        )
        scorecard = {
            "partial_matches": [
                {"skill": "Microsoft Sentinel", "gap": "Limited experience with Sentinel.", "evidence": "x"},
            ],
            "genuine_gaps": [
                {"skill": "Rapid7 InsightIDR", "impact": "High impact."},
                {"skill": "CrowdStrike Falcon/NG-SIEM", "impact": "High impact."},
            ],
        }
        profile = {
            "skills": [
                {"name": "Splunk Enterprise Security", "tool_category": "SIEM", "confidence": "confirmed_hands_on"},
                {"name": "Palo Alto Cortex XDR", "tool_category": "EDR / XDR", "confidence": "confirmed_hands_on"},
            ]
        }
        result = _ensure_tool_gap_bridge_mentioned(letter, scorecard, profile)
        self.assertIn("Microsoft Sentinel", result)
        self.assertIn("Rapid7 InsightIDR", result)
        self.assertIn("Splunk Enterprise Security", result)
        self.assertIn("CrowdStrike Falcon/NG-SIEM", result)
        self.assertIn("Palo Alto Cortex XDR", result)
        self.assertLess(result.index("Microsoft Sentinel"), result.index("Sincerely"))

    def test_does_not_bridge_an_unrecognised_vendor(self):
        letter = "Kia ora,\n\nSome content.\n\nSincerely,\nJason Hill"
        scorecard = {"genuine_gaps": [{"skill": "SomeObscureNicheTool9000", "impact": "x"}]}
        profile = {"skills": [{"name": "Splunk", "tool_category": "SIEM", "confidence": "confirmed_hands_on"}]}
        result = _ensure_tool_gap_bridge_mentioned(letter, scorecard, profile)
        self.assertEqual(result, letter)

    def test_does_not_bridge_without_a_real_alternate_in_the_same_category(self):
        letter = "Kia ora,\n\nSome content.\n\nSincerely,\nJason Hill"
        scorecard = {"genuine_gaps": [{"skill": "Microsoft Sentinel", "impact": "x"}]}
        # Candidate's only tool skill is a different category (EDR, not SIEM).
        profile = {"skills": [{"name": "Cortex XDR", "tool_category": "EDR / XDR", "confidence": "confirmed_hands_on"}]}
        result = _ensure_tool_gap_bridge_mentioned(letter, scorecard, profile)
        self.assertEqual(result, letter)

    def test_does_not_bridge_a_gap_already_substantively_mentioned(self):
        letter = (
            "Kia ora,\n\nWhile I haven't used Microsoft Sentinel directly, my Splunk experience "
            "transfers well.\n\nSincerely,\nJason Hill"
        )
        scorecard = {"genuine_gaps": [{"skill": "Microsoft Sentinel", "impact": "x"}]}
        profile = {"skills": [{"name": "Splunk Enterprise Security", "tool_category": "SIEM", "confidence": "confirmed_hands_on"}]}
        result = _ensure_tool_gap_bridge_mentioned(letter, scorecard, profile)
        self.assertEqual(result, letter)

    def test_requires_confirmed_hands_on_confidence_for_the_real_alternate(self):
        letter = "Kia ora,\n\nSome content.\n\nSincerely,\nJason Hill"
        scorecard = {"genuine_gaps": [{"skill": "Microsoft Sentinel", "impact": "x"}]}
        profile = {"skills": [{"name": "Splunk Enterprise Security", "tool_category": "SIEM", "confidence": "familiarity"}]}
        result = _ensure_tool_gap_bridge_mentioned(letter, scorecard, profile)
        self.assertEqual(result, letter)

    def test_appends_at_the_end_when_no_sign_off_is_found(self):
        letter = "Just some body text with no sign-off line at all."
        scorecard = {"genuine_gaps": [{"skill": "Microsoft Sentinel", "impact": "x"}]}
        profile = {"skills": [{"name": "Splunk Enterprise Security", "tool_category": "SIEM", "confidence": "confirmed_hands_on"}]}
        result = _ensure_tool_gap_bridge_mentioned(letter, scorecard, profile)
        self.assertTrue(result.startswith(letter))
        self.assertIn("Microsoft Sentinel", result)


if __name__ == "__main__":
    unittest.main()
