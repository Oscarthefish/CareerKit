import unittest

from app.api.cv import _build_achievement_bullet, _enrich_achievement_bullets

CV_TEMPLATE = """# Alex Example

## KEY SKILLS

- SIEM

## SELECTED ACHIEVEMENTS
{bullets}

## PROJECTS
- Something
"""


class BuildAchievementBulletTests(unittest.TestCase):
    def test_appends_detail_that_adds_new_information(self):
        bullet = _build_achievement_bullet(
            "Acted as interim Head of Cyber Security",
            "Provided leadership continuity until a new CISO was appointed internationally.",
        )
        self.assertIn("interim Head of Cyber Security", bullet)
        self.assertIn("CISO", bullet)

    def test_skips_near_duplicate_result(self):
        bullet = _build_achievement_bullet(
            "Increased endpoint protection coverage from ~60% to 98%",
            "Increased endpoint protection coverage from approximately 60% to 98% of known endpoints.",
        )
        self.assertEqual(bullet, "Increased endpoint protection coverage from ~60% to 98%")

    def test_no_detail_returns_title_only(self):
        self.assertEqual(_build_achievement_bullet("Some achievement", ""), "Some achievement")

    def test_handles_title_already_ending_in_punctuation(self):
        bullet = _build_achievement_bullet(
            "Did the thing!", "This unlocked a completely different specific outcome for the team."
        )
        self.assertTrue(bullet.startswith("Did the thing! This unlocked"))


class EnrichAchievementBulletsTests(unittest.TestCase):
    def test_enriches_a_title_only_bullet(self):
        achievements = [{
            "title": "Acted as interim Head of Cyber Security",
            "result": "Provided leadership continuity until a new CISO was appointed internationally, at which point the team was rebuilt under permanent leadership.",
        }]
        content = CV_TEMPLATE.format(bullets="- Acted as interim Head of Cyber Security")
        result = _enrich_achievement_bullets(content, achievements)
        self.assertIn("CISO", result)
        self.assertIn("Acted as interim Head of Cyber Security. Provided leadership continuity", result)

    def test_leaves_near_duplicate_result_alone(self):
        achievements = [{
            "title": "Increased endpoint protection coverage from ~60% to 98%",
            "result": "Increased endpoint protection coverage from approximately 60% to 98% of known endpoints.",
        }]
        content = CV_TEMPLATE.format(bullets="- Increased endpoint protection coverage from ~60% to 98%")
        result = _enrich_achievement_bullets(content, achievements)
        self.assertEqual(result, content)

    def test_does_not_overwrite_a_bullet_the_model_already_enriched_well(self):
        achievements = [{
            "title": "Helped build a global 24/7 SOC across three locations",
            "result": "Successfully built out the 6-person local SOC team as part of the wider global 24/7 programme.",
        }]
        already_good = "- Helped build a global 24/7 SOC across three locations, growing the local team to 6 people as part of the wider programme."
        content = CV_TEMPLATE.format(bullets=already_good)
        result = _enrich_achievement_bullets(content, achievements)
        self.assertEqual(result, content)

    def test_achievement_with_no_matching_bullet_does_not_crash(self):
        achievements = [{"title": "Something not present in the CV at all", "result": "Some result."}]
        content = CV_TEMPLATE.format(bullets="- A completely different achievement")
        result = _enrich_achievement_bullets(content, achievements)
        self.assertEqual(result, content)

    def test_no_selected_achievements_section_does_not_crash(self):
        content = "# Alex Example\n\n## KEY SKILLS\n\n- SIEM\n"
        result = _enrich_achievement_bullets(content, [{"title": "X", "result": "Y specific detail here"}])
        self.assertEqual(result, content)

    def test_achievement_with_no_result_or_action_left_as_title(self):
        achievements = [{"title": "Some bare achievement", "result": "", "action": ""}]
        content = CV_TEMPLATE.format(bullets="- Some bare achievement")
        result = _enrich_achievement_bullets(content, achievements)
        self.assertEqual(result, content)

    def test_falls_back_to_action_when_result_is_empty(self):
        achievements = [{
            "title": "Did a thing",
            "result": "",
            "action": "Carried out a specific, detailed piece of work involving named tools.",
        }]
        content = CV_TEMPLATE.format(bullets="- Did a thing")
        result = _enrich_achievement_bullets(content, achievements)
        self.assertIn("named tools", result)

    def test_multiple_achievements_each_handled_independently(self):
        achievements = [
            {
                "title": "Increased endpoint protection coverage from ~60% to 98%",
                "result": "Increased endpoint protection coverage from approximately 60% to 98% of known endpoints.",
            },
            {
                "title": "Acted as interim Head of Cyber Security",
                "result": "Provided leadership continuity until a new CISO was appointed internationally.",
            },
        ]
        content = CV_TEMPLATE.format(bullets=(
            "- Increased endpoint protection coverage from ~60% to 98%\n"
            "- Acted as interim Head of Cyber Security"
        ))
        result = _enrich_achievement_bullets(content, achievements)
        self.assertIn("- Increased endpoint protection coverage from ~60% to 98%\n", result)
        self.assertIn("Acted as interim Head of Cyber Security. Provided leadership continuity", result)


if __name__ == "__main__":
    unittest.main()
