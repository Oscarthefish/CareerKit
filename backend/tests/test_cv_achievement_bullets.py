import unittest

from app.api.cv import (
    _build_achievement_bullet,
    _dedupe_achievement_bullets,
    _enrich_achievement_bullets,
    _ensure_all_achievements_present,
    _ensure_all_roles_present,
    _force_correct_certifications,
    _force_correct_domains_line,
    _force_correct_leadership_line,
    _force_correct_ops_skills_line,
    _force_correct_projects,
    _format_role_date,
    _merge_key_skills_continuations,
    _remove_fabricated_role_headings,
    _strip_bullets_for_dataless_roles,
    _strip_empty_key_skills_lines,
    _strip_trailing_line_commas,
    _strip_unbolded_key_skills_duplicate_lines,
)

CV_TEMPLATE = """# Alex Example

## KEY SKILLS

- SIEM

## SELECTED ACHIEVEMENTS
{bullets}

## PROJECTS
- Something
"""

ROLE_CV_TEMPLATE = """# Alex Example

## KEY SKILLS

- SIEM

## PROFESSIONAL EXPERIENCE

{roles}

## SELECTED ACHIEVEMENTS
- Something

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


class EnsureAllAchievementsPresentTests(unittest.TestCase):
    def test_appends_a_dropped_achievement(self):
        achievements = [
            {"title": "Kept achievement", "result": "Some result for the kept one."},
            {"title": "Dropped achievement", "result": "This one never made it into the generated text."},
        ]
        content = CV_TEMPLATE.format(bullets="- Kept achievement. Some result for the kept one.")
        result = _ensure_all_achievements_present(content, achievements)
        self.assertIn("Dropped achievement", result)
        self.assertIn("never made it into the generated text", result)

    def test_does_not_duplicate_an_achievement_already_present(self):
        achievements = [{"title": "Already there", "result": "Some detail."}]
        content = CV_TEMPLATE.format(bullets="- Already there. Some detail.")
        result = _ensure_all_achievements_present(content, achievements)
        self.assertEqual(result.count("Already there"), 1)

    def test_no_missing_achievements_leaves_content_unchanged(self):
        achievements = [{"title": "Present one", "result": "Detail."}]
        content = CV_TEMPLATE.format(bullets="- Present one. Detail.")
        result = _ensure_all_achievements_present(content, achievements)
        self.assertEqual(result, content)

    def test_multiple_missing_achievements_all_appended(self):
        achievements = [
            {"title": "First missing", "result": "First detail."},
            {"title": "Second missing", "result": "Second detail."},
        ]
        content = CV_TEMPLATE.format(bullets="- Something completely different")
        result = _ensure_all_achievements_present(content, achievements)
        self.assertIn("First missing", result)
        self.assertIn("Second missing", result)

    def test_no_selected_achievements_section_does_not_crash(self):
        content = "# Alex Example\n\n## KEY SKILLS\n\n- SIEM\n"
        result = _ensure_all_achievements_present(content, [{"title": "X", "result": "Y"}])
        self.assertEqual(result, content)

    def test_works_together_with_enrichment_in_sequence(self):
        # Mirrors the real call order in generate_cv: enrich first, then
        # ensure nothing was dropped entirely.
        achievements = [
            {"title": "Bare title only", "result": "This detail should get merged in."},
            {"title": "Never generated at all", "result": "This should be appended."},
        ]
        content = CV_TEMPLATE.format(bullets="- Bare title only")
        step1 = _enrich_achievement_bullets(content, achievements)
        step2 = _ensure_all_achievements_present(step1, achievements)
        self.assertIn("This detail should get merged in", step2)
        self.assertIn("Never generated at all", step2)
        self.assertIn("This should be appended", step2)


class FormatRoleDateTests(unittest.TestCase):
    def test_converts_year_month_to_abbreviated_form(self):
        self.assertEqual(_format_role_date("2007-07"), "Jul 2007")

    def test_pads_nothing_but_handles_single_digit_month(self):
        self.assertEqual(_format_role_date("2016-2"), "Feb 2016")

    def test_empty_value_returns_empty_string(self):
        self.assertEqual(_format_role_date(""), "")

    def test_unrecognised_format_returned_unchanged(self):
        self.assertEqual(_format_role_date("Jul 2007"), "Jul 2007")


class EnsureAllRolesPresentTests(unittest.TestCase):
    def test_appends_a_dropped_role_with_no_description_as_heading_only(self):
        work_experience = [
            {"role": "Senior Analyst", "company": "Acme", "start_date": "2020-01",
             "end_date": None, "is_current": True, "description": "", "key_responsibilities": []},
            {"role": "Desktop Support", "company": "Old Co", "start_date": "2007-07",
             "end_date": "2008-11", "is_current": False, "description": "", "key_responsibilities": []},
        ]
        content = ROLE_CV_TEMPLATE.format(roles="### Senior Analyst | Acme | Jan 2020 - Present")
        result = _ensure_all_roles_present(content, work_experience)
        self.assertIn("### Desktop Support | Old Co | Jul 2007 - Nov 2008", result)

    def test_does_not_duplicate_a_role_already_present(self):
        work_experience = [
            {"role": "Senior Analyst", "company": "Acme", "start_date": "2020-01",
             "end_date": None, "is_current": True, "description": "", "key_responsibilities": []},
        ]
        content = ROLE_CV_TEMPLATE.format(roles="### Senior Analyst | Acme | Jan 2020 - Present")
        result = _ensure_all_roles_present(content, work_experience)
        self.assertEqual(result, content)

    def test_no_missing_roles_leaves_content_unchanged(self):
        work_experience = [
            {"role": "Senior Analyst", "company": "Acme", "start_date": "2020-01",
             "end_date": None, "is_current": True, "description": "", "key_responsibilities": []},
        ]
        content = ROLE_CV_TEMPLATE.format(roles="### Senior Analyst | Acme | Jan 2020 - Present")
        result = _ensure_all_roles_present(content, work_experience)
        self.assertEqual(result, content)

    def test_appended_role_includes_its_key_responsibilities(self):
        work_experience = [
            {"role": "Senior Analyst", "company": "Acme", "start_date": "2020-01",
             "end_date": None, "is_current": True, "description": "", "key_responsibilities": []},
            {"role": "Support Engineer", "company": "Old Co", "start_date": "2010-01",
             "end_date": "2012-01", "is_current": False, "description": "",
             "key_responsibilities": ["Triaged support tickets."]},
        ]
        content = ROLE_CV_TEMPLATE.format(roles="### Senior Analyst | Acme | Jan 2020 - Present")
        result = _ensure_all_roles_present(content, work_experience)
        self.assertIn("Triaged support tickets.", result)

    def test_no_professional_experience_section_does_not_crash(self):
        content = "# Alex Example\n\n## KEY SKILLS\n\n- SIEM\n"
        result = _ensure_all_roles_present(content, [{"role": "X", "company": "Y", "start_date": "2020-01"}])
        self.assertEqual(result, content)

    def test_same_role_title_at_different_company_not_treated_as_match(self):
        work_experience = [
            {"role": "Cyber Security Analyst", "company": "timbre Digital", "start_date": "2016-11",
             "end_date": "2018-01", "is_current": False, "description": "", "key_responsibilities": []},
            {"role": "Cyber Security Analyst", "company": "The Workshop", "start_date": "2016-02",
             "end_date": "2016-11", "is_current": False, "description": "", "key_responsibilities": []},
        ]
        content = ROLE_CV_TEMPLATE.format(
            roles="### Cyber Security Analyst | timbre Digital | Nov 2016 - Jan 2018"
        )
        result = _ensure_all_roles_present(content, work_experience)
        self.assertIn("### Cyber Security Analyst | The Workshop | Feb 2016 - Nov 2016", result)


class DedupeAchievementBulletsTests(unittest.TestCase):
    def test_drops_untitled_bullet_that_restates_a_titled_one(self):
        achievements = [{
            "title": "Led Cortex XDR tenant migration",
            "result": "Successfully completed the migration with policies, profiles, rules and exceptions intact.",
        }]
        content = CV_TEMPLATE.format(bullets=(
            "- Successfully completed the migration of more than 1,000 endpoints between Cortex XDR tenants, "
            "recreating policies, profiles, rules and exceptions.\n"
            "- Led Cortex XDR tenant migration. Successfully completed the migration with policies, profiles, "
            "rules and exceptions intact."
        ))
        result = _dedupe_achievement_bullets(content, achievements)
        self.assertEqual(result.count("Cortex XDR"), 1)
        self.assertIn("Led Cortex XDR tenant migration", result)

    def test_leaves_genuinely_distinct_bullets_alone(self):
        achievements = [{"title": "Led Cortex XDR tenant migration", "result": "Migrated endpoints cleanly."}]
        content = CV_TEMPLATE.format(bullets=(
            "- Led Cortex XDR tenant migration. Migrated endpoints cleanly.\n"
            "- Placed 11th of 110 teams - Trace Labs OSINT Search Party CTF, DEF CON 34"
        ))
        result = _dedupe_achievement_bullets(content, achievements)
        self.assertEqual(result, content)

    def test_no_selected_achievements_section_does_not_crash(self):
        content = "# Alex Example\n\n## KEY SKILLS\n\n- SIEM\n"
        result = _dedupe_achievement_bullets(content, [{"title": "X", "result": "Y"}])
        self.assertEqual(result, content)

    def test_no_titled_lines_at_all_leaves_content_unchanged(self):
        achievements = [{"title": "Something else entirely", "result": "Unrelated detail."}]
        content = CV_TEMPLATE.format(bullets="- A completely unrelated bare bullet with its own wording")
        result = _dedupe_achievement_bullets(content, achievements)
        self.assertEqual(result, content)


class StripTrailingLineCommasTests(unittest.TestCase):
    def test_strips_dangling_trailing_comma(self):
        content = "**Security Domains:** Network Security, Email Security,\n**Leadership & People:** Team Leadership\n"
        result = _strip_trailing_line_commas(content)
        self.assertEqual(result, "**Security Domains:** Network Security, Email Security\n**Leadership & People:** Team Leadership\n")

    def test_leaves_lines_without_trailing_comma_unchanged(self):
        content = "**Security Domains:** Network Security, Email Security\n"
        self.assertEqual(_strip_trailing_line_commas(content), content)

    def test_does_not_touch_a_comma_inside_a_number(self):
        content = "Migrated more than 1,000 endpoints\n"
        self.assertEqual(_strip_trailing_line_commas(content), content)


class MergeKeySkillsContinuationsTests(unittest.TestCase):
    def test_strips_a_continued_key_skills_section(self):
        content = (
            "## KEY SKILLS\n**Security Operations:** Incident Response\n"
            "\n## KEY SKILLS (continued)\nSIEM: Splunk\nEDR: Cortex XDR\n"
            "\n## PROFESSIONAL EXPERIENCE\n### Role | Company | Jan 2020 - Present\n"
        )
        result = _merge_key_skills_continuations(content)
        self.assertNotIn("continued", result.lower())
        self.assertNotIn("SIEM: Splunk", result)
        self.assertIn("## PROFESSIONAL EXPERIENCE", result)

    def test_strips_multiple_continued_sections(self):
        content = (
            "## KEY SKILLS\n**Security Operations:** Incident Response\n"
            "\n## KEY SKILLS (continued)\nSIEM: Splunk\n"
            "\n## KEY SKILLS (continued)\n**Leadership & People:** Team Leadership\n"
            "\n## PROFESSIONAL EXPERIENCE\n### Role | Company | Jan 2020 - Present\n"
        )
        result = _merge_key_skills_continuations(content)
        self.assertEqual(result.count("KEY SKILLS"), 1)

    def test_leaves_content_unchanged_when_no_continuation_present(self):
        content = "## KEY SKILLS\n**Security Operations:** Incident Response\n\n## PROFESSIONAL EXPERIENCE\n- x\n"
        self.assertEqual(_merge_key_skills_continuations(content), content)


class ForceCorrectCertificationsTests(unittest.TestCase):
    def test_fixes_a_mistyped_certification_abbreviation(self):
        certifications = [{"display_line": "Practical Junior OSINT Researcher (PJOR), TCM Security, 2024"}]
        content = "# Alex Example\n\n## CERTIFICATIONS\n- Practical Junior OSINT Researcher (PJR), TCM Security, 2024\n\n## EDUCATION\n- x\n"
        result = _force_correct_certifications(content, certifications)
        self.assertIn("(PJOR)", result)
        self.assertNotIn("(PJR)", result)

    def test_replaces_whole_section_with_all_display_lines_in_order(self):
        certifications = [
            {"display_line": "First Cert, Issuer, 2020"},
            {"display_line": "Second Cert, Issuer, 2021 (In Progress)"},
        ]
        content = "# Alex Example\n\n## CERTIFICATIONS\n- Something wrong\n\n## EDUCATION\n- x\n"
        result = _force_correct_certifications(content, certifications)
        self.assertIn("- First Cert, Issuer, 2020\n- Second Cert, Issuer, 2021 (In Progress)", result)
        self.assertNotIn("Something wrong", result)

    def test_no_certifications_section_does_not_crash(self):
        content = "# Alex Example\n\n## EDUCATION\n- x\n"
        result = _force_correct_certifications(content, [{"display_line": "First Cert, Issuer, 2020"}])
        self.assertEqual(result, content)

    def test_no_certifications_data_leaves_content_unchanged(self):
        content = "# Alex Example\n\n## CERTIFICATIONS\n- Something\n\n## EDUCATION\n- x\n"
        self.assertEqual(_force_correct_certifications(content, []), content)


class ForceCorrectOpsSkillsLineTests(unittest.TestCase):
    def test_replaces_inflated_line_with_real_skill_names(self):
        skills = [
            {"name": "Incident Response", "category": "technical"},
            {"name": "Network Security", "category": "technical"},
            {"name": "Post-Incident Review & Continuous Improvement", "category": "process"},
        ]
        content = (
            "## KEY SKILLS\n"
            "**Security Operations & Incident Response:** SIEM investigation, Timeline reconstruction, Senior technical judgement\n"
            "**Security Domains:** Network Security\n"
        )
        result = _force_correct_ops_skills_line(content, skills)
        self.assertIn(
            "**Security Operations & Incident Response:** Incident Response, Post-Incident Review & Continuous Improvement",
            result,
        )
        self.assertNotIn("Timeline reconstruction", result)

    def test_excludes_domain_skills_from_the_ops_line(self):
        skills = [
            {"name": "Incident Response", "category": "technical"},
            {"name": "Email Security", "category": "technical"},
        ]
        content = "**Security Operations & Incident Response:** old content\n"
        result = _force_correct_ops_skills_line(content, skills)
        self.assertIn("Incident Response", result)
        self.assertNotIn("Email Security", result)

    def test_inserts_the_line_when_missing_entirely_but_real_data_exists(self):
        content = "## KEY SKILLS\n**Security Domains:** Network Security\n\n## PROFESSIONAL EXPERIENCE\n"
        result = _force_correct_ops_skills_line(content, [{"name": "Incident Response", "category": "technical"}])
        self.assertIn("**Security Operations & Incident Response:** Incident Response", result)

    def test_no_key_skills_section_leaves_content_unchanged(self):
        content = "# Alex Example\n\n## PROFESSIONAL EXPERIENCE\n"
        result = _force_correct_ops_skills_line(content, [{"name": "Incident Response", "category": "technical"}])
        self.assertEqual(result, content)

    def test_removes_the_line_when_no_ops_category_skills_exist(self):
        content = "**Security Operations & Incident Response:** old content\n"
        result = _force_correct_ops_skills_line(content, [{"name": "Team Leadership", "category": "soft"}])
        self.assertNotIn("Security Operations & Incident Response", result)


class ForceCorrectProjectsTests(unittest.TestCase):
    def test_rebuilds_a_project_with_bold_name_and_all_labelled_lines(self):
        projects = [{
            "name": "SOC Analyst Toolbox",
            "description": "A local-first investigation platform.",
            "role": "Creator and sole developer",
            "technologies": ["Splunk", "Jira"],
            "outcomes": "Built and published a working tool.",
            "url": "https://github.com/Oscarthefish/SOC-Analyst-Toolbox",
        }]
        content = "## PROJECTS\n- SOC Analyst Toolbox is a local-first tool.\n\n## CERTIFICATIONS\n- x\n"
        result = _force_correct_projects(content, projects)
        self.assertIn("- **SOC Analyst Toolbox** — A local-first investigation platform.", result)
        self.assertIn("Role: Creator and sole developer", result)
        self.assertIn("Technologies: Splunk, Jira", result)
        self.assertIn("Outcomes: Built and published a working tool.", result)
        self.assertIn("URL: https://github.com/Oscarthefish/SOC-Analyst-Toolbox", result)
        self.assertIn("## CERTIFICATIONS", result)

    def test_no_projects_section_does_not_crash(self):
        content = "# Alex Example\n\n## CERTIFICATIONS\n- x\n"
        result = _force_correct_projects(content, [{"name": "X", "description": "Y"}])
        self.assertEqual(result, content)

    def test_no_projects_data_leaves_content_unchanged(self):
        content = "## PROJECTS\n- Something\n\n## CERTIFICATIONS\n- x\n"
        self.assertEqual(_force_correct_projects(content, []), content)

    def test_omits_optional_lines_when_data_is_missing(self):
        projects = [{"name": "Small Project", "description": "Does a thing."}]
        content = "## PROJECTS\n- old\n\n## CERTIFICATIONS\n- x\n"
        result = _force_correct_projects(content, projects)
        self.assertIn("- **Small Project** — Does a thing.", result)
        self.assertNotIn("Role:", result)
        self.assertNotIn("URL:", result)


class StripEmptyKeySkillsLinesTests(unittest.TestCase):
    def test_strips_a_dangling_empty_leadership_line(self):
        content = "## KEY SKILLS\n**Security Operations & Incident Response:** Incident Response\n**Leadership & People:** \n\n## PROFESSIONAL EXPERIENCE\n"
        result = _strip_empty_key_skills_lines(content)
        self.assertNotIn("Leadership & People", result)
        self.assertIn("Security Operations & Incident Response", result)

    def test_leaves_a_non_empty_line_untouched(self):
        content = "**Leadership & People:** Team Leadership, Mentoring\n"
        self.assertEqual(_strip_empty_key_skills_lines(content), content)

    def test_never_touches_platforms_and_tools_heading(self):
        # Platforms & Tools legitimately has nothing on its own line - its
        # content lives on the lines directly after.
        content = "**Platforms & Tools:**\nSIEM: Splunk Enterprise Security\n"
        self.assertEqual(_strip_empty_key_skills_lines(content), content)

    def test_strips_multiple_empty_lines(self):
        content = "**Security Domains:** \n**Leadership & People:**\n## PROFESSIONAL EXPERIENCE\n"
        result = _strip_empty_key_skills_lines(content)
        self.assertEqual(result, "## PROFESSIONAL EXPERIENCE\n")


class RemoveFabricatedRoleHeadingsTests(unittest.TestCase):
    def test_removes_a_role_paired_with_the_wrong_employer(self):
        work_experience = [
            {"role": "IT Team Leader", "company": "Momentum Worldwide", "key_responsibilities": []},
        ]
        content = (
            "## PROFESSIONAL EXPERIENCE\n\n"
            "### IT Team Leader | The Workshop | Nov 2008 - Sep 2011\n"
            "- Team leadership\n\n"
            "### IT Team Leader | Momentum Worldwide | Nov 2008 - Sep 2011\n"
            "- Team leadership\n\n"
            "## SELECTED ACHIEVEMENTS\n- x\n"
        )
        result = _remove_fabricated_role_headings(content, work_experience)
        self.assertNotIn("The Workshop", result)
        self.assertIn("IT Team Leader | Momentum Worldwide", result)
        self.assertEqual(result.count("### IT Team Leader"), 1)

    def test_keeps_a_role_title_legitimately_repeated_at_a_different_real_company(self):
        work_experience = [
            {"role": "Cyber Security Analyst", "company": "timbre Digital", "key_responsibilities": []},
            {"role": "Cyber Security Analyst", "company": "The Workshop", "key_responsibilities": []},
        ]
        content = (
            "## PROFESSIONAL EXPERIENCE\n\n"
            "### Cyber Security Analyst | timbre Digital | Nov 2016 - Jan 2018\n- a\n\n"
            "### Cyber Security Analyst | The Workshop | Feb 2016 - Nov 2016\n- b\n\n"
            "## SELECTED ACHIEVEMENTS\n- x\n"
        )
        result = _remove_fabricated_role_headings(content, work_experience)
        self.assertIn("Cyber Security Analyst | timbre Digital", result)
        self.assertIn("Cyber Security Analyst | The Workshop", result)

    def test_no_professional_experience_section_does_not_crash(self):
        content = "# Alex Example\n\n## KEY SKILLS\n- SIEM\n"
        result = _remove_fabricated_role_headings(content, [{"role": "X", "company": "Y"}])
        self.assertEqual(result, content)


class StripBulletsForDatalessRolesTests(unittest.TestCase):
    def test_strips_an_invented_bullet_under_a_role_with_no_real_data(self):
        work_experience = [
            {"role": "Information Technology Desktop Support", "company": "Interpublic Group",
             "description": "", "key_responsibilities": []},
        ]
        content = (
            "## PROFESSIONAL EXPERIENCE\n\n"
            "### Information Technology Desktop Support | Interpublic Group | Jul 2007 - Nov 2008\n"
            "- Team leadership\n\n"
            "## SELECTED ACHIEVEMENTS\n- x\n"
        )
        result = _strip_bullets_for_dataless_roles(content, work_experience)
        self.assertNotIn("Team leadership", result)
        self.assertIn("### Information Technology Desktop Support | Interpublic Group", result)

    def test_leaves_a_role_with_real_data_untouched(self):
        work_experience = [
            {"role": "X", "company": "Y", "description": "", "key_responsibilities": ["Did a real thing"]},
        ]
        content = "## PROFESSIONAL EXPERIENCE\n\n### X | Y | Jan 2020 - Present\n- Did a real thing\n\n## SELECTED ACHIEVEMENTS\n- x\n"
        result = _strip_bullets_for_dataless_roles(content, work_experience)
        self.assertEqual(result, content)

    def test_no_professional_experience_section_does_not_crash(self):
        content = "# Alex Example\n\n## KEY SKILLS\n- SIEM\n"
        result = _strip_bullets_for_dataless_roles(content, [{"role": "X", "company": "Y"}])
        self.assertEqual(result, content)


class ForceCorrectDomainsAndLeadershipLinesTests(unittest.TestCase):
    def test_inserts_domains_line_when_missing_entirely(self):
        skills = [{"name": "Network Security", "category": "technical"}, {"name": "Email Security", "category": "technical"}]
        content = "## KEY SKILLS\n**Security Operations & Incident Response:** Incident Response\n\n## PROFESSIONAL EXPERIENCE\n- x\n"
        result = _force_correct_domains_line(content, skills)
        self.assertIn("**Security Domains:** Network Security, Email Security", result)

    def test_inserts_leadership_line_when_missing_entirely(self):
        skills = [{"name": "Team Leadership", "category": "soft"}, {"name": "Mentoring & Coaching", "category": "soft"}]
        content = "## KEY SKILLS\n**Security Operations & Incident Response:** Incident Response\n\n## PROFESSIONAL EXPERIENCE\n- x\n"
        result = _force_correct_leadership_line(content, skills)
        self.assertIn("**Leadership & People:** Team Leadership, Mentoring & Coaching", result)

    def test_corrects_an_existing_wrong_leadership_line(self):
        skills = [{"name": "Team Leadership", "category": "soft"}]
        content = "**Leadership & People:** made-up filler text\n"
        result = _force_correct_leadership_line(content, skills)
        self.assertIn("**Leadership & People:** Team Leadership", result)
        self.assertNotIn("made-up filler text", result)

    def test_removes_the_line_when_nothing_real_to_show(self):
        content = "**Leadership & People:** made-up filler text\n## PROFESSIONAL EXPERIENCE\n"
        result = _force_correct_leadership_line(content, [])
        self.assertNotIn("Leadership & People", result)

    def test_domains_excludes_non_domain_technical_skills(self):
        skills = [
            {"name": "Network Security", "category": "technical"},
            {"name": "Incident Response", "category": "technical"},  # belongs to the ops line, not domains
        ]
        content = "## KEY SKILLS\n**Security Operations & Incident Response:** Incident Response\n\n## PROFESSIONAL EXPERIENCE\n"
        result = _force_correct_domains_line(content, skills)
        domains_line = [l for l in result.splitlines() if l.startswith("**Security Domains:**")][0]
        self.assertIn("Network Security", domains_line)
        self.assertNotIn("Incident Response", domains_line)


class StripUnboldedKeySkillsDuplicateLinesTests(unittest.TestCase):
    def test_strips_an_unbolded_duplicate_that_precedes_the_correct_bold_line(self):
        content = (
            "## KEY SKILLS\n\n"
            "Security Operations & Incident Response: Splunk, Incident Response\n\n"
            "Leadership & People: Team Leadership\n"
            "**Security Operations & Incident Response:** Incident Response\n"
            "**Leadership & People:** Team Leadership\n"
        )
        result = _strip_unbolded_key_skills_duplicate_lines(content)
        self.assertNotIn("Security Operations & Incident Response: Splunk", result)
        self.assertIn("**Security Operations & Incident Response:** Incident Response", result)
        self.assertIn("**Leadership & People:** Team Leadership", result)

    def test_never_touches_the_bolded_line(self):
        content = "**Security Operations & Incident Response:** Incident Response\n"
        self.assertEqual(_strip_unbolded_key_skills_duplicate_lines(content), content)

    def test_no_duplicate_present_leaves_content_unchanged(self):
        content = "## KEY SKILLS\n\n**Leadership & People:** Team Leadership\n\n## PROFESSIONAL EXPERIENCE\n"
        self.assertEqual(_strip_unbolded_key_skills_duplicate_lines(content), content)


if __name__ == "__main__":
    unittest.main()
