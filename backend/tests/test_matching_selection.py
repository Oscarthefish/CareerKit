import unittest

from app.services.matching.selection import (
    MAX_ACHIEVEMENTS,
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
        self.assertEqual(len(result), 3)  # backfilled up to MAX_ACHIEVEMENTS (or total, if fewer)
        self.assertEqual(result[0]["title"], "Cited one")

    def test_no_citations_at_all_still_returns_up_to_the_floor(self):
        achievements = [{"title": "A"}, {"title": "B"}]
        result = select_achievements(achievements, {})
        self.assertEqual(len(result), 2)

    def test_real_regression_backfills_past_the_floor_to_include_a_measurable_outcome(self):
        # Verbatim shape of the real bug: 6 achievements already cited (well
        # past the old floor of 4), one genuinely strong, quantified
        # achievement left uncited purely because this job's Job Match
        # citation pass never mentioned it - it must still make the cut,
        # since there's room below MAX_ACHIEVEMENTS (8).
        cited = [{"title": f"Cited {i}"} for i in range(6)]
        quantified = {"title": "Increased endpoint protection coverage from ~60% to 98%",
                      "measurable_outcome": "Endpoint protection coverage increased from ~60% to 98%"}
        achievements = cited + [quantified]
        scores = {f"cited {i}": 1.0 for i in range(6)}
        result = select_achievements(achievements, scores)
        self.assertIn(quantified, result)

    def test_measurable_outcome_achievements_are_preferred_in_the_backfill(self):
        cited = {"title": "Cited"}
        plain = {"title": "Plain uncited achievement"}
        quantified = {"title": "Quantified uncited achievement", "measurable_outcome": "50% improvement"}
        achievements = [cited, plain, quantified]
        scores = {"cited": 1.0}
        result = select_achievements(achievements, scores)
        # Both fit well within MAX_ACHIEVEMENTS, but the quantified one must
        # be backfilled ahead of the plain one regardless of input order.
        titles = [a["title"] for a in result]
        self.assertLess(titles.index("Quantified uncited achievement"), titles.index("Plain uncited achievement"))

    def test_does_not_backfill_past_max_achievements_even_with_measurable_outcomes(self):
        cited = [{"title": f"Cited {i}"} for i in range(8)]
        quantified = {"title": "Quantified but no room left", "measurable_outcome": "100% improvement"}
        achievements = cited + [quantified]
        scores = {f"cited {i}": 1.0 for i in range(8)}
        result = select_achievements(achievements, scores)
        self.assertEqual(len(result), 8)
        self.assertNotIn(quantified, result)

    def test_real_regression_always_include_guarantees_a_specific_achievement_survives(self):
        # The actual real-world case reported: 6 cited, 5 other uncited
        # achievements (several with their own measurable_outcome) all
        # competing for the 2 remaining backfill slots, with database order
        # happening to favour others ahead of this specific one. Flagging
        # it always_include must guarantee it regardless of that contest.
        cited = [{"title": f"Cited {i}"} for i in range(6)]
        competitors = [
            {"title": f"Competing quantified achievement {i}", "measurable_outcome": f"{i}0% improvement"}
            for i in range(4)
        ]
        target = {
            "title": "Increased endpoint protection coverage from ~60% to 98%",
            "measurable_outcome": "Endpoint protection coverage increased from ~60% to 98%",
            "always_include": True,
        }
        achievements = cited + competitors + [target]
        scores = {f"cited {i}": 1.0 for i in range(6)}
        result = select_achievements(achievements, scores)
        self.assertIn(target, result)

    def test_always_include_still_counts_toward_the_overall_max_when_room_allows(self):
        # One flagged achievement plus plenty of others: the flagged one is
        # guaranteed, but the total still caps at MAX_ACHIEVEMENTS overall
        # (it consumes one of the 8 slots) rather than adding on top of a
        # full 8 from the rest - CV length stays sane for the common case
        # of flagging just one or two signature achievements. Flagging MORE
        # than MAX_ACHIEVEMENTS is the deliberate exception - see
        # test_can_select_all_achievements_by_flagging_more_than_max below.
        always = {"title": "Signature achievement", "always_include": True}
        others = [{"title": f"Other {i}"} for i in range(10)]
        result = select_achievements([always] + others, {})
        self.assertIn(always, result)
        self.assertEqual(len(result), MAX_ACHIEVEMENTS)

    def test_can_select_all_achievements_by_flagging_more_than_max(self):
        achievements = [{"title": f"Achievement {i}", "always_include": True} for i in range(12)]
        result = select_achievements(achievements, {})
        self.assertEqual(len(result), 12)

    def test_always_include_achievements_lead_the_list_in_original_order(self):
        a = {"title": "A", "always_include": True}
        b = {"title": "B", "always_include": True}
        cited = {"title": "Cited", }
        result = select_achievements([cited, a, b], {"cited": 1.0})
        self.assertEqual([x["title"] for x in result[:2]], ["A", "B"])


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

    def test_real_regression_requirement_name_overlap_rescues_a_miscited_bullet(self):
        # Verbatim shape of the real bug: a Job Match citation for "physical
        # security" pointed at a DIFFERENT role's description text (never a
        # substring of any bullet here), so the one bullet that's actually
        # the best evidence for it scored zero on citation alone and lost
        # its role's position-3 budget (4) to other, less relevant bullets.
        target = "Carried out physical security assessments and recommendations as part of setting up the Auckland office in 2017"
        other_bullets = [f"Some other duty {i} with no particular relevance" for i in range(10)]
        work_experience = [{"role": "Cyber Security Analyst", "key_responsibilities": other_bullets + [target]}]
        # The citation source is a role-level description, which never
        # literally appears inside any individual bullet - exactly why
        # _bullet_score alone misses it.
        scores = {"work experience: network security analyst at the workshop (description)": 1.0}
        requirement_coverage = [
            {"name": "Managing, maintaining, and documenting physical security", "coverage": "PARTIAL_EVIDENCE"},
        ]
        result = select_responsibilities(work_experience, scores, requirement_coverage=requirement_coverage)
        self.assertIn(target, result[0]["key_responsibilities"])

    def test_requirement_overlap_is_ignored_without_two_shared_significant_words(self):
        # A single shared word ("security") must not be enough on its own -
        # same false-positive guard used elsewhere in this module.
        bullet = "Investigated phishing and malware alerts"
        other_bullets = [f"Some other duty {i} with no particular relevance" for i in range(6)]
        work_experience = [{"role": "Analyst", "key_responsibilities": other_bullets + [bullet]}]
        requirement_coverage = [{"name": "Physical security systems experience", "coverage": "STRONG_EVIDENCE"}]
        result = select_responsibilities(work_experience, {}, requirement_coverage=requirement_coverage)
        self.assertNotIn(bullet, result[0]["key_responsibilities"])

    def test_requirement_overlap_ignores_no_and_unknown_evidence_rows(self):
        target = "Carried out physical security assessments and recommendations"
        other_bullets = [f"Some other duty {i} with no particular relevance" for i in range(6)]
        work_experience = [{"role": "Analyst", "key_responsibilities": other_bullets + [target]}]
        requirement_coverage = [{"name": "Physical security systems experience", "coverage": "NO_EVIDENCE"}]
        result = select_responsibilities(work_experience, {}, requirement_coverage=requirement_coverage)
        self.assertNotIn(target, result[0]["key_responsibilities"])

    def test_backward_compatible_without_requirement_coverage(self):
        work_experience = [{"role": "X", "key_responsibilities": ["a", "b"]}]
        result = select_responsibilities(work_experience, {})
        self.assertEqual(result[0]["key_responsibilities"], ["a", "b"])


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

    # Distinct, non-overlapping fake brand names rather than "Product N" -
    # the shared word "product" would otherwise make every one of them look
    # fuzzy-cited by _fuzzy_name_cited (see SelectPlatformsAndToolsTests
    # below for that behaviour's own dedicated tests), which isn't what
    # these floor/fallback tests are about.
    _BRANDS = ["Zendrix", "Korvalon", "Fenhollow", "Trabium", "Quorvex", "Nalderin", "Brexwell"]

    def test_a_moderate_cut_leaving_at_least_the_floor_is_respected(self):
        lines = [f"Category {i}: {self._BRANDS[i]}" for i in range(7)]
        scores = {self._BRANDS[i].lower(): 1.0 for i in range(6)}  # only "Category 6" uncited
        result = select_platforms_and_tools(lines, scores)
        self.assertEqual(len(result), 6)
        self.assertNotIn(f"Category 6: {self._BRANDS[6]}", result)

    def test_a_severe_cut_below_the_floor_falls_back_to_the_full_list(self):
        # Mirrors the real failure this guards against: sparse Job Match
        # coverage dropping clearly-relevant categories (EDR/XDR, firewalls)
        # down to just one surviving line.
        lines = [f"Category {i}: {self._BRANDS[i]}" for i in range(7)]
        result = select_platforms_and_tools(lines, {self._BRANDS[0].lower(): 1.0})  # only 1 of 7 cited
        self.assertEqual(result, lines)

    def test_small_list_keeps_everything_regardless_of_citation(self):
        lines = ["EDR / XDR: Cisco AMP"]
        self.assertEqual(select_platforms_and_tools(lines, {}), lines)

    def test_real_xero_regression_credits_a_vendor_prefix_truncated_citation(self):
        # Verbatim shape of the real bug: the Job Match cited "...directly
        # in Cortex XDR, including endpoint isolation..." - missing the
        # "Palo Alto" vendor prefix the candidate's actual skill record
        # carries - so the exact substring check in score_for_name alone
        # never credited it, dropping a flagship, heavily-evidenced tool
        # from a real Custom CV's Selected Technologies.
        lines = ["Endpoint & Detection: Cisco AMP, Palo Alto Cortex XDR"]
        scores = {
            "cisco amp": 1.0,
            "investigated and responded to threats directly in cortex xdr, "
            "including endpoint isolation, live response and ioc blocking": 1.0,
        }
        result = select_platforms_and_tools(lines, scores)
        self.assertEqual(result, ["Endpoint & Detection: Cisco AMP, Palo Alto Cortex XDR"])

    def test_real_xero_regression_credits_a_category_level_citation(self):
        # Verbatim shape of the real bug: a requirement named "SIEM or Log
        # Platform" with STRONG_EVIDENCE cited only the generic source
        # string "SIEM" - never the specific product name "Splunk
        # Enterprise Security" - so neither the exact nor the fuzzy
        # name-based check credited it, dropping the candidate's actual
        # SIEM platform from a real Custom CV even though this requirement
        # is unambiguously about exactly that product's category.
        lines = ["SIEM & Investigation: Splunk Enterprise Security"]
        scores = {"siem": 3.0}
        tool_skills = [{"name": "Splunk Enterprise Security", "tool_category": "SIEM", "category": "tool"}]
        requirement_coverage = [
            {"name": "SIEM or Log Platform", "coverage": "STRONG_EVIDENCE", "sources": ["SIEM"]},
        ]
        result = select_platforms_and_tools(lines, scores, tool_skills=tool_skills, requirement_coverage=requirement_coverage)
        self.assertEqual(result, ["SIEM & Investigation: Splunk Enterprise Security"])

    def test_category_credit_is_not_applied_without_tool_skills_or_requirement_coverage(self):
        # Backward compatibility: callers that don't pass the new optional
        # arguments (e.g. existing tests above) get exactly the old
        # exact-substring-only behaviour, not a silent behaviour change.
        lines = ["SIEM & Investigation: Splunk Enterprise Security"]
        result = select_platforms_and_tools(lines, {"siem": 3.0})
        self.assertEqual(result, lines)  # floor fallback, not category credit - nothing was cited

    def test_fuzzy_match_ignores_generic_marketing_words(self):
        # "Enterprise Security" is shared marketing boilerplate, not a
        # distinctive product identifier - must not let an unrelated
        # product's name fuzzy-match through it.
        lines = ["Email Security: Mimecast Enterprise Security"]
        scores = {"some other vendor enterprise security platform": 1.0}
        result = select_platforms_and_tools(lines, scores)
        self.assertEqual(result, lines)  # floor fallback - nothing genuinely cited


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
