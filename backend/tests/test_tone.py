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

    def test_article_follows_the_new_first_word(self):
        # Real regression: "As a highly experienced ..." became "As a experienced ...".
        self.check("As a highly experienced Security Operations professional",
                   "As an experienced Security Operations professional")
        self.check("an extremely skilled analyst", "a skilled analyst")
        self.check("A highly skilled analyst", "A skilled analyst")
        self.check("An extremely experienced lead", "An experienced lead")

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

    def test_self_described_expert_and_padding(self):
        # Real regression from a regenerated custom CV's profile paragraph.
        self.check("I bring a wealth of experience to the table. As a security operations expert based in Auckland, "
                   "I lead teams.",
                   "I bring broad experience. As a security operations professional based in Auckland, I lead teams.")
        self.check("My expertise spans incident response.", "My experience spans incident response.")
        self.check("I have extensive experience in investigating incidents.",
                   "I have experience in investigating incidents.")
        self.check("One of my strongest areas of expertise is triage.",
                   "One of my strongest areas of experience is triage.")
        self.check("As an incident response expert, I led it.", "As an incident response professional, I led it.")

    def test_plain_and_role_wording_is_left_alone(self):
        for text in ("Skilled in incident response.", "Acted as subject matter expert for the SIEM.",
                     "Acted as a subject matter expert for the SIEM.",
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
