"""CV wording fixes that depend on CV structure (services/cv_wording.py).

Synthetic data only (this repo is public); the sentences mirror real
regressions from a regenerated custom CV.
"""
import unittest

from app.ai.tone import tone_down
from app.services.cv_wording import (
    dedupe_profile_sentences, past_tense_for_past_roles, polish_cv_wording, strip_our_without_current_role,
)

CV = """# Alex Example
alex@example.com | Our Street, Auckland

## PROFESSIONAL PROFILE
I relocated to Auckland in 2016 to build out security operations. I have experience with a wide range of security tools and technologies, including SIEM, Splunk Enterprise Security, EDR and Cortex XDR. I am always looking for ways to improve our security operations and reduce our risk.

## CORE CAPABILITIES
**Incident Response:** I investigate phishing and malware incidents end to end. I have experience working with a wide range of security tools and technologies, including SIEM, Splunk Enterprise Security, EDR, and Cortex XDR.
**Tooling:** I have experience working with a wide range of security tools and technologies, including SIEM, Splunk Enterprise Security, EDR, and Cortex XDR.

## PROFESSIONAL EXPERIENCE
### Senior Analyst | Example Co | Jan 2022 – Aug 2026
- Investigating phishing, malware and account compromise events
- Analysing suspicious activity across SIEM and EDR
- Tracking down odd behaviour
### Analyst | Current Co | Jan 2027 – Present
- Investigating phishing in the current role
"""


class PastTenseTests(unittest.TestCase):
    def test_past_role_bullets_move_to_the_past_tense(self):
        out = past_tense_for_past_roles(CV)
        self.assertIn("- Investigated phishing, malware and account compromise events", out)
        self.assertIn("- Analysed suspicious activity across SIEM and EDR", out)

    def test_unknown_verbs_and_current_roles_are_left_alone(self):
        out = past_tense_for_past_roles(CV)
        self.assertIn("- Tracking down odd behaviour", out)
        self.assertIn("- Investigating phishing in the current role", out)


class OurTests(unittest.TestCase):
    def test_our_is_dropped_without_a_current_role(self):
        out = strip_our_without_current_role(CV, has_current_role=False)
        self.assertIn("improve security operations and reduce risk", out)
        self.assertIn("Our Street", out)  # contact preamble untouched

    def test_our_stays_with_a_current_role(self):
        self.assertEqual(strip_our_without_current_role(CV, has_current_role=True), CV)

    def test_sentence_initial_our(self):
        md = "# A\n\n## PROFESSIONAL PROFILE\nOur team grew to six.\n"
        self.assertEqual(strip_our_without_current_role(md, False), "# A\n\n## PROFESSIONAL PROFILE\nTeam grew to six.\n")


class DedupeTests(unittest.TestCase):
    def test_repeated_tool_sentence_is_dropped_where_the_line_has_other_content(self):
        out = dedupe_profile_sentences(CV)
        self.assertIn("**Incident Response:** I investigate phishing and malware incidents end to end.\n", out)
        # Profile keeps the first mention; Tooling keeps it only because it's
        # the line's sole sentence (see the next test).
        self.assertEqual(out.count("wide range of security tools"), 2)

    def test_a_capability_line_is_never_left_empty(self):
        out = dedupe_profile_sentences(CV)
        tooling = next(l for l in out.splitlines() if l.startswith("**Tooling:**"))
        self.assertGreater(len(tooling), len("**Tooling:** "))

    def test_distinct_sentences_survive(self):
        md = ("## PROFESSIONAL PROFILE\nI led a Cortex XDR tenant migration of 1,000 endpoints. "
              "I built a six-person SOC team in Auckland.\n")
        self.assertEqual(dedupe_profile_sentences(md), md)


class TrackRecordTests(unittest.TestCase):
    def test_proven_track_record_is_plain(self):
        self.assertEqual(tone_down("I have a proven track record of investigating incidents."),
                         "I have a track record of investigating incidents.")


class PolishTests(unittest.TestCase):
    def test_all_together(self):
        out = polish_cv_wording(CV, has_current_role=False)
        self.assertIn("- Investigated phishing", out)
        self.assertNotIn("our security operations", out)
        self.assertNotIn("Incident Response:** I investigate phishing and malware incidents end to end. I have", out)


if __name__ == "__main__":
    unittest.main()
