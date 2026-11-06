import unittest

from app.ai.tone import tone_down
from app.api.cv import apply_custom_cv_safety_nets


class ToneDownTests(unittest.TestCase):
    def check(self, before, after):
        self.assertEqual(tone_down(before), after)

    def test_intensified_adjectives_become_plain(self):
        self.check("Highly skilled analyst.", "Skilled analyst.")
        self.check("I am a highly-skilled and highly experienced SOC lead.", "I am a skilled and experienced SOC lead.")
        self.check("Extremely proficient with Splunk.", "Proficient with Splunk.")

    def test_expert_level_is_removed_with_article_fixed(self):
        self.check("Expert-level knowledge of Splunk.", "Knowledge of Splunk.")
        self.check("with expert level knowledge of EDR", "with knowledge of EDR")
        self.check("an expert-level Splunk user", "a Splunk user")
        self.check("An expert-level understanding of EDR", "An understanding of EDR")
        self.check("I have expert-level proficiency in SIEM.", "I have experience in SIEM.")
        self.check("Expert-level expertise in EDR.", "Experience in EDR.")

    def test_expert_in_and_expertise(self):
        self.check("I am an expert in threat hunting.", "I am experienced in threat hunting.")
        self.check("Deep expertise in triage.", "Experience in triage.")
        self.check("expert at writing reports", "skilled at writing reports")

    def test_hype_words_are_dropped(self):
        self.check("Built a world-class team.", "Built a team.")
        self.check("an unparalleled eye for detail", "an eye for detail")

    def test_plain_and_role_wording_is_left_alone(self):
        for text in ("Skilled in incident response.", "Acted as subject matter expert for the SIEM.",
                     "Experienced analyst with expertise in EDR.", "", None):
            self.assertEqual(tone_down(text), text)

    def test_custom_cv_safety_nets_apply_it(self):
        cv = ("# Jane Example\njane@example.com | Auckland\n\n## PROFESSIONAL PROFILE\n"
              "Highly skilled analyst with expert-level knowledge of Splunk.\n")
        out = apply_custom_cv_safety_nets(cv, {})
        self.assertIn("Skilled analyst with knowledge of Splunk.", out)
        self.assertNotIn("expert-level", out.lower())


if __name__ == "__main__":
    unittest.main()
