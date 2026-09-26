import unittest

from app.services.matching.selection import (
    relevance_scores,
    score_for_name,
    select_achievements,
    select_evidence_for_cv,
    select_platforms_and_tools,
    select_projects,
    select_responsibilities,
    select_skills,
)


def _row(name, importance, coverage, sources):
    return {"name": name, "importance": importance, "coverage": coverage, "sources": sources}


class RelevanceScoresTests(unittest.TestCase):
    def test_accumulates_across_requirements_citing_the_same_source(self):
        coverage = [
            _row("SIEM", "critical", "STRONG_EVIDENCE", ["Splunk Enterprise Security"]),  # 3 * 1.0
            _row("Log correlation", "important", "STRONG_EVIDENCE", ["Splunk Enterprise Security"]),  # 2 * 1.0
        ]
        scores = relevance_scores(coverage)
        self.assertEqual(scores["splunk enterprise security"], 5.0)

    def test_no_evidence_rows_contribute_nothing(self):
        coverage = [_row("Microsoft Sentinel", "critical", "NO_EVIDENCE", [])]
        self.assertEqual(relevance_scores(coverage), {})

    def test_unknown_coverage_contributes_nothing(self):
        coverage = [_row("Something vague", "important", "UNKNOWN", ["Some Skill"])]
        self.assertEqual(relevance_scores(coverage), {})

    def test_partial_evidence_weighted_less_than_strong(self):
        strong = relevance_scores([_row("A", "critical", "STRONG_EVIDENCE", ["Skill X"])])
        partial = relevance_scores([_row("A", "critical", "PARTIAL_EVIDENCE", ["Skill X"])])
        self.assertGreater(strong["skill x"], partial["skill x"])


class ScoreForNameTests(unittest.TestCase):
    def test_matches_case_insensitively_as_substring_of_a_source(self):
        scores = {"splunk enterprise security (daily use)": 3.0}
        self.assertEqual(score_for_name("Splunk Enterprise Security", scores), 3.0)

    def test_no_matching_source_returns_zero(self):
        scores = {"cortex xdr": 3.0}
        self.assertEqual(score_for_name("Microsoft Sentinel", scores), 0.0)

    def test_empty_name_returns_zero(self):
        self.assertEqual(score_for_name("", {"anything": 5.0}), 0.0)


class SelectSkillsTests(unittest.TestCase):
    def test_cited_skills_rank_first(self):
        skills = [{"name": "Cortex XDR"}, {"name": "Tenable Nessus"}, {"name": "Splunk Enterprise Security"}]
        scores = {"splunk enterprise security": 6.0, "cortex xdr": 3.0}
        result = select_skills(skills, scores)
        self.assertEqual([s["name"] for s in result[:2]], ["Splunk Enterprise Security", "Cortex XDR"])

    def test_small_list_keeps_everything_regardless_of_citation(self):
        skills = [{"name": "A"}, {"name": "B"}]
        self.assertEqual(select_skills(skills, {}), skills)

    def test_backfills_up_to_the_floor_when_citation_coverage_is_sparse(self):
        # Mirrors the real failure this guards against: a large skill list
        # with only a couple of citations shouldn't collapse to just those.
        skills = [{"name": f"Skill {i}"} for i in range(30)]
        scores = {"skill 0": 5.0, "skill 1": 3.0}
        result = select_skills(skills, scores)
        self.assertEqual(len(result), 15)  # MIN_SKILLS
        self.assertEqual([s["name"] for s in result[:2]], ["Skill 0", "Skill 1"])

    def test_does_not_backfill_past_the_floor_when_plenty_are_cited(self):
        skills = [{"name": f"Skill {i}"} for i in range(30)]
        scores = {f"skill {i}": 1.0 for i in range(20)}
        result = select_skills(skills, scores)
        self.assertEqual(len(result), 20)  # all cited ones, no need to pad further


class SelectAchievementsTests(unittest.TestCase):
    def test_caps_at_max_and_ranks_by_relevance(self):
        achievements = [{"title": f"Achievement {i}"} for i in range(10)]
        scores = {f"achievement {i}".lower(): float(i) for i in range(10)}
        result = select_achievements(achievements, scores)
        self.assertEqual(len(result), 8)
        self.assertEqual(result[0]["title"], "Achievement 9")

    def test_backfills_when_too_few_are_cited(self):
        achievements = [{"title": "Cited one"}, {"title": "Uncited two"}, {"title": "Uncited three"}]
        scores = {"cited one": 5.0}
        result = select_achievements(achievements, scores)
        self.assertEqual(len(result), 3)  # backfilled up to MIN_ACHIEVEMENTS (or total, if fewer)
        self.assertEqual(result[0]["title"], "Cited one")

    def test_no_citations_at_all_still_returns_up_to_the_floor(self):
        achievements = [{"title": "A"}, {"title": "B"}]
        result = select_achievements(achievements, {})
        self.assertEqual(len(result), 2)


class SelectResponsibilitiesTests(unittest.TestCase):
    def test_recent_role_keeps_more_bullets_than_an_older_role(self):
        bullets = [f"Did thing {i} involving Splunk" for i in range(10)]
        work_experience = [
            {"role": "Recent Role", "key_responsibilities": list(bullets)},
            {"role": "Old Role", "key_responsibilities": list(bullets)},
            {"role": "Older Role", "key_responsibilities": list(bullets)},
            {"role": "Oldest Role", "key_responsibilities": list(bullets)},
            {"role": "Ancient Role", "key_responsibilities": list(bullets)},
        ]
        scores = {"splunk": 1.0}
        result = select_responsibilities(work_experience, scores)
        self.assertGreater(len(result[0]["key_responsibilities"]), len(result[4]["key_responsibilities"]))

    def test_role_survives_with_zero_bullets(self):
        work_experience = [{"role": "X", "company": "Y", "key_responsibilities": []}]
        result = select_responsibilities(work_experience, {})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["role"], "X")
        self.assertEqual(result[0]["key_responsibilities"], [])

    def test_does_not_mutate_the_input(self):
        original = [{"role": "X", "key_responsibilities": ["a", "b", "c"]}]
        select_responsibilities(original, {})
        self.assertEqual(original[0]["key_responsibilities"], ["a", "b", "c"])

    def test_preserves_original_relative_order_of_surviving_bullets(self):
        work_experience = [{"role": "X", "key_responsibilities": ["low relevance", "high relevance splunk"]}]
        scores = {"splunk": 5.0}
        result = select_responsibilities(work_experience, scores)
        # budget for position 0 is 6, larger than the list, so both survive -
        # order should still be the original, not score-sorted.
        self.assertEqual(result[0]["key_responsibilities"], ["low relevance", "high relevance splunk"])


class SelectProjectsTests(unittest.TestCase):
    def test_keeps_only_cited_projects_when_there_are_several(self):
        projects = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
        result = select_projects(projects, {"a": 1.0})
        self.assertEqual([p["name"] for p in result], ["A"])

    def test_keeps_uncited_project_when_there_are_two_or_fewer(self):
        projects = [{"name": "SOC Analyst Toolbox"}]
        result = select_projects(projects, {})
        self.assertEqual(result, projects)


class SelectPlatformsAndToolsTests(unittest.TestCase):
    def test_filters_a_category_to_only_its_cited_products(self):
        lines = ["EDR / XDR: Cisco AMP, Palo Alto Cortex XDR"]
        result = select_platforms_and_tools(lines, {"palo alto cortex xdr": 3.0})
        self.assertEqual(result, ["EDR / XDR: Palo Alto Cortex XDR"])

    def test_a_moderate_cut_leaving_at_least_the_floor_is_respected(self):
        lines = [f"Category {i}: Product {i}" for i in range(7)]
        scores = {f"product {i}": 1.0 for i in range(6)}  # only "Category 6" uncited
        result = select_platforms_and_tools(lines, scores)
        self.assertEqual(len(result), 6)
        self.assertNotIn("Category 6: Product 6", result)

    def test_a_severe_cut_below_the_floor_falls_back_to_the_full_list(self):
        # Mirrors the real failure this guards against: sparse Job Match
        # coverage dropping clearly-relevant categories (EDR/XDR, firewalls)
        # down to just one surviving line.
        lines = [f"Category {i}: Product {i}" for i in range(7)]
        result = select_platforms_and_tools(lines, {"product 0": 1.0})  # only 1 of 7 cited
        self.assertEqual(result, lines)

    def test_small_list_keeps_everything_regardless_of_citation(self):
        lines = ["EDR / XDR: Cisco AMP"]
        self.assertEqual(select_platforms_and_tools(lines, {}), lines)


class SelectEvidenceForCvTests(unittest.TestCase):
    def test_leaves_certifications_and_training_untouched(self):
        profile = {
            "skills": [{"name": "Cortex XDR"}],
            "achievements": [{"title": "Did a thing"}],
            "work_experience": [{"role": "X", "key_responsibilities": []}],
            "projects": [],
            "platforms_and_tools_display": [],
            "certifications": [{"display_line": "Some Cert, 2020"}],
            "training": [{"display_line": "Some Training, 2019"}],
        }
        result = select_evidence_for_cv(profile, [])
        self.assertEqual(result["certifications"], profile["certifications"])
        self.assertEqual(result["training"], profile["training"])

    def test_does_not_mutate_the_input_profile(self):
        profile = {
            "skills": [{"name": "A"}],
            "achievements": [{"title": "B"}],
            "work_experience": [{"role": "C", "key_responsibilities": ["one"]}],
            "projects": [{"name": "D"}],
            "platforms_and_tools_display": ["Cat: A"],
        }
        import copy
        before = copy.deepcopy(profile)
        select_evidence_for_cv(profile, [_row("A", "critical", "STRONG_EVIDENCE", ["A"])])
        self.assertEqual(profile, before)


if __name__ == "__main__":
    unittest.main()
