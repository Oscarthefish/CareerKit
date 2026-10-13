import unittest

from app.api.cv import (
    _ensure_two_paragraph_profile,
    _force_additional_background,
    _force_certifications_and_training,
    _force_selected_technologies,
    _non_dataless_roles,
    _normalize_core_capabilities,
    _strip_unsupported_claims_by_line,
    apply_custom_cv_safety_nets,
)


class NonDatalessRolesTests(unittest.TestCase):
    def test_keeps_roles_with_a_description_or_responsibilities(self):
        work_experience = [
            {"role": "SOC Analyst", "company": "Acme", "description": "Did things"},
            {"role": "Helpdesk Analyst", "company": "Acme", "key_responsibilities": ["Triaged tickets"]},
            {"role": "Desktop Support", "company": "Other Co", "description": "", "key_responsibilities": []},
        ]
        kept = _non_dataless_roles(work_experience)
        self.assertEqual([e["role"] for e in kept], ["SOC Analyst", "Helpdesk Analyst"])


class StripUnsupportedClaimsByLineTests(unittest.TestCase):
    def _profile(self):
        return {"skills": [{"name": "Splunk Enterprise Security"}]}

    def test_drops_only_the_line_containing_an_unsupported_product(self):
        content = (
            "## CORE CAPABILITIES\n"
            "**Detection & analysis:** Strong SIEM work using Splunk Enterprise Security.\n"
            "**Cloud security:** Deep hands-on work with Microsoft Sentinel across tenants.\n"
            "## SELECTED TECHNOLOGIES\n"
            "SIEM & Investigation: Splunk Enterprise Security\n"
        )
        result = _strip_unsupported_claims_by_line(
            content, self._profile(), ["Advanced SIEM platforms such as Microsoft Sentinel"], "CORE CAPABILITIES"
        )
        self.assertIn("Splunk Enterprise Security", result)
        self.assertNotIn("Microsoft Sentinel", result)
        # The other section's line must survive untouched - confirms the
        # regex is scoped to CORE CAPABILITIES only, not the whole document.
        self.assertIn("SIEM & Investigation: Splunk Enterprise Security", result)

    def test_leaves_content_unchanged_when_nothing_is_unsupported(self):
        content = "## CORE CAPABILITIES\n**Detection:** Splunk Enterprise Security work.\n"
        result = _strip_unsupported_claims_by_line(
            content, self._profile(), ["Experience with Splunk Enterprise Security"], "CORE CAPABILITIES"
        )
        self.assertEqual(result, content)

    def test_never_blanks_the_whole_section(self):
        content = "## CORE CAPABILITIES\n**Cloud:** Microsoft Sentinel everywhere.\n"
        result = _strip_unsupported_claims_by_line(
            content, self._profile(), ["Microsoft Sentinel"], "CORE CAPABILITIES"
        )
        self.assertEqual(result, content)


class EnsureTwoParagraphProfileTests(unittest.TestCase):
    def test_real_xero_regression_splits_a_run_on_block_into_two_paragraphs(self):
        # Verbatim shape of the real generation this safety net exists to
        # catch: nine sentences written as one continuous block with no
        # paragraph break at all.
        content = (
            "## PROFESSIONAL PROFILE\n"
            "As a highly experienced Security Operations professional with over a decade of experience in "
            "network and cyber security, I have developed a strong background in managing security operations "
            "across enterprise environments and international infrastructure projects. With a proven track "
            "record of delivering effective security solutions, I have worked closely with globally distributed "
            "teams to triage, contain and resolve security incidents. I am excited to bring my skills and "
            "experience to a new challenge and contribute to a team that is dedicated to delivering exceptional "
            "security solutions. In my previous roles, I have worked in various capacities, including as a "
            "Cyber Security Analyst, Network Security Analyst, and Desktop Support Supervisor. I have a strong "
            "passion for OSINT and threat research, and I have completed extensive training in various areas, "
            "including incident response, threat analysis, and security operations. I am a strong believer in "
            "the importance of continuous learning and professional development, and I regularly attend "
            "industry events and conferences to stay up-to-date with the latest developments in the field.\n"
            "## CORE CAPABILITIES\n"
        )
        result = _ensure_two_paragraph_profile(content)
        original_body = content.split("## PROFESSIONAL PROFILE\n")[1].split("## CORE CAPABILITIES")[0]
        result_body = result.split("## PROFESSIONAL PROFILE\n")[1].split("## CORE CAPABILITIES")[0]
        paragraphs = [p for p in result_body.strip().split("\n\n") if p.strip()]
        self.assertEqual(len(paragraphs), 2)
        # No word lost in the reflow - same sentence content, just regrouped.
        self.assertEqual(sorted(original_body.split()), sorted(result_body.split()))

    def test_leaves_an_already_well_formed_two_paragraph_profile_unchanged_in_substance(self):
        content = (
            "## PROFESSIONAL PROFILE\n"
            "First paragraph about identity and seniority.\n\n"
            "Second paragraph about working style and interests.\n"
            "## CORE CAPABILITIES\n"
        )
        result = _ensure_two_paragraph_profile(content)
        self.assertIn("First paragraph about identity and seniority.", result)
        self.assertIn("Second paragraph about working style and interests.", result)

    def test_single_sentence_profile_is_left_as_one_paragraph(self):
        content = "## PROFESSIONAL PROFILE\nOne short sentence only.\n## CORE CAPABILITIES\n"
        self.assertEqual(_ensure_two_paragraph_profile(content), content)

    def test_no_change_when_section_missing(self):
        content = "## CORE CAPABILITIES\n**Label:** content.\n"
        self.assertEqual(_ensure_two_paragraph_profile(content), content)

    def test_three_paragraphs_collapse_to_two(self):
        content = (
            "## PROFESSIONAL PROFILE\n"
            "Sentence one is here. Sentence two follows along.\n\n"
            "Sentence three adds detail. Sentence four continues it.\n\n"
            "Sentence five wraps it up. Sentence six closes things out.\n"
            "## CORE CAPABILITIES\n"
        )
        result = _ensure_two_paragraph_profile(content)
        section = result.split("## CORE CAPABILITIES")[0].replace("## PROFESSIONAL PROFILE", "").strip()
        self.assertEqual(len(section.split("\n\n")), 2)


class NormalizeCoreCapabilitiesTests(unittest.TestCase):
    TOOLS_LINES = [
        "SIEM & Investigation: Jira",
        "Endpoint & Detection: Cisco AMP",
        "Network, DNS & Web: Cisco Umbrella",
        "Threat Intelligence & Supporting Tools: Maltego, VirusTotal",
    ]

    def test_real_xero_regression_demotes_headings_strips_leaks_and_folds_to_one_line_per_group(self):
        # Verbatim shape of the real generation this safety net exists to
        # catch: "###" sub-headings, multiple bullets per group, and several
        # bullets that are a literal SELECTED TECHNOLOGIES line (sometimes
        # run together with real content in the same comma-separated bullet).
        content = (
            "## CORE CAPABILITIES\n"
            "### Incident Response & Investigation: \n"
            "- Incident Response, Maltego, Security Information and Event Management (SIEM), "
            "SIEM & Investigation: Jira, Endpoint & Detection: Cisco AMP, Network, DNS & Web: Cisco Umbrella, "
            "Threat Intelligence & Supporting Tools: Maltego, VirusTotal\n"
            "- Endpoint Detection & Response (EDR), Endpoint & Detection: Cisco AMP\n"
            "- Security Operations, Team Leadership\n"
            "### Global SOC Operations: \n"
            "- SIEM & Investigation: Jira\n"
            "- Endpoint & Detection: Cisco AMP\n"
            "- Network, DNS & Web: Cisco Umbrella\n"
            "## SELECTED TECHNOLOGIES\n"
            "SIEM & Investigation: Jira\n"
            "Endpoint & Detection: Cisco AMP\n"
            "Network, DNS & Web: Cisco Umbrella\n"
            "Threat Intelligence & Supporting Tools: Maltego, VirusTotal\n"
        )
        result = _normalize_core_capabilities(content, self.TOOLS_LINES)
        core_section = result.split("## SELECTED TECHNOLOGIES")[0]

        self.assertNotIn("###", core_section)
        self.assertNotIn("SIEM & Investigation: Jira", core_section)
        self.assertNotIn("Endpoint & Detection: Cisco AMP", core_section)
        self.assertNotIn("Threat Intelligence & Supporting Tools:", core_section)
        # A group left with nothing but a tech-list leak collapses entirely
        # rather than surviving as an empty, padding-only line.
        self.assertNotIn("Global SOC Operations", core_section)
        # Real content from the surviving group is preserved, folded onto
        # one "**Label:**" line.
        self.assertIn("**Incident Response & Investigation:**", core_section)
        self.assertIn("Incident Response", core_section)
        self.assertIn("Security Operations, Team Leadership", core_section)
        # Exactly one surviving group - the heading line plus its one folded
        # "**Label:**" line, nothing else.
        body_lines = [l for l in core_section.strip().split("\n") if l.strip()]
        self.assertEqual(len(body_lines), 2)
        # The verbatim copy below must survive completely untouched.
        self.assertIn("SIEM & Investigation: Jira", result.split("## SELECTED TECHNOLOGIES")[1])

    def test_leaves_already_well_formed_section_unchanged_in_substance(self):
        content = (
            "## CORE CAPABILITIES\n"
            "**Detection & analysis:** Strong SIEM work using Splunk, backed by hands-on EDR triage.\n"
            "**Mentoring:** Coached junior analysts and ran onboarding for new SOC hires.\n"
        )
        result = _normalize_core_capabilities(content, self.TOOLS_LINES)
        self.assertIn("**Detection & analysis:** Strong SIEM work using Splunk, backed by hands-on EDR triage.", result)
        self.assertIn("**Mentoring:** Coached junior analysts and ran onboarding for new SOC hires.", result)

    def test_no_change_when_section_missing(self):
        content = "## PROFESSIONAL PROFILE\nSome profile text.\n"
        self.assertEqual(_normalize_core_capabilities(content, self.TOOLS_LINES), content)


class ForceSelectedTechnologiesTests(unittest.TestCase):
    def test_replaces_a_truncated_section_body(self):
        content = "## SELECTED TECHNOLOGIES\nSIEM & Investigation: Splunk\n## PROFESSIONAL EXPERIENCE\n"
        result = _force_selected_technologies(
            content, ["SIEM & Investigation: Splunk, Jira", "Endpoint & Detection: Cortex XDR"]
        )
        self.assertIn("SIEM & Investigation: Splunk, Jira", result)
        self.assertIn("Endpoint & Detection: Cortex XDR", result)

    def test_inserts_section_before_professional_experience_when_missing(self):
        content = "## PROFESSIONAL PROFILE\nSome profile text.\n## PROFESSIONAL EXPERIENCE\n### Role | Co\n"
        result = _force_selected_technologies(content, ["SIEM & Investigation: Splunk"])
        self.assertIn("## SELECTED TECHNOLOGIES\nSIEM & Investigation: Splunk", result)
        self.assertLess(result.index("SELECTED TECHNOLOGIES"), result.index("PROFESSIONAL EXPERIENCE"))

    def test_strips_a_duplicate_unlabelled_leak_elsewhere(self):
        content = (
            "## CORE CAPABILITIES\nSIEM & Investigation: Splunk, Jira\n"
            "## SELECTED TECHNOLOGIES\nSIEM & Investigation: Splunk, Jira\n"
            "## PROFESSIONAL EXPERIENCE\n"
        )
        result = _force_selected_technologies(content, ["SIEM & Investigation: Splunk, Jira"])
        self.assertEqual(result.count("SIEM & Investigation: Splunk, Jira"), 1)

    def test_leaves_content_unchanged_when_no_tools(self):
        content = "## PROFESSIONAL EXPERIENCE\n### Role | Co\n"
        self.assertEqual(_force_selected_technologies(content, []), content)


class ForceCertificationsAndTrainingTests(unittest.TestCase):
    def test_builds_both_lines(self):
        content = "## PROFESSIONAL EXPERIENCE\n### Role | Co\n- Did things\n## COMMUNITY INVOLVEMENT\n"
        certs = [{"display_line": "GCIH, GIAC (2022)"}, {"display_line": "Security+, CompTIA (2020)"}]
        training = [{"display_line": "Splunk Fundamentals, Splunk (2021)"}]
        result = _force_certifications_and_training(content, certs, training)
        self.assertIn("## CERTIFICATIONS & TRAINING", result)
        self.assertIn("GCIH, GIAC (2022) | Security+, CompTIA (2020)", result)
        self.assertIn("Relevant training: Splunk Fundamentals, Splunk (2021)", result)

    def test_omits_training_line_when_no_training(self):
        content = "## PROFESSIONAL EXPERIENCE\n### Role | Co\n"
        result = _force_certifications_and_training(content, [{"display_line": "GCIH, GIAC (2022)"}], [])
        self.assertIn("GCIH, GIAC (2022)", result)
        self.assertNotIn("Relevant training", result)

    def test_replaces_existing_wrong_section_body(self):
        content = (
            "## PROFESSIONAL EXPERIENCE\n### Role | Co\n"
            "## CERTIFICATIONS & TRAINING\nGCIH (PJR)\n"
            "## COMMUNITY INVOLVEMENT\n"
        )
        result = _force_certifications_and_training(content, [{"display_line": "GCIH, GIAC (2022)"}], [])
        self.assertIn("GCIH, GIAC (2022)", result)
        self.assertNotIn("GCIH (PJR)", result)

    def test_leaves_content_unchanged_when_nothing_to_show(self):
        content = "## PROFESSIONAL EXPERIENCE\n### Role | Co\n"
        self.assertEqual(_force_certifications_and_training(content, [], []), content)


class ForceAdditionalBackgroundTests(unittest.TestCase):
    def test_builds_earlier_roles_and_education(self):
        content = "## PROFESSIONAL EXPERIENCE\n### SOC Analyst | Acme | Jan 2020 - Present\n"
        work_experience = [
            {"role": "SOC Analyst", "company": "Acme", "description": "Real work", "start_date": "2020-01", "is_current": True},
            {"role": "IT Team Leader", "company": "Momentum Worldwide", "start_date": "2008-11", "end_date": "2011-09"},
        ]
        education = [{"display_line": "Advanced PC Servicing Diploma, Massey University (2000)"}]
        result = _force_additional_background(content, work_experience, education)
        self.assertIn("## ADDITIONAL BACKGROUND", result)
        self.assertIn("Earlier roles: IT Team Leader, Momentum Worldwide (Nov 2008 - Sep 2011).", result)
        self.assertIn("Education: Advanced PC Servicing Diploma, Massey University (2000).", result)
        # The real, included role must not also show up in Additional Background.
        self.assertNotIn("SOC Analyst, Acme", result)

    def test_omits_section_when_nothing_dataless_and_no_education(self):
        content = "## PROFESSIONAL EXPERIENCE\n### SOC Analyst | Acme | Jan 2020 - Present\n"
        work_experience = [{"role": "SOC Analyst", "company": "Acme", "description": "Real work"}]
        self.assertEqual(_force_additional_background(content, work_experience, []), content)

    def test_education_only_omits_earlier_roles_clause(self):
        content = "## PROFESSIONAL EXPERIENCE\n### SOC Analyst | Acme | Jan 2020 - Present\n"
        work_experience = [{"role": "SOC Analyst", "company": "Acme", "description": "Real work"}]
        education = [{"display_line": "BSc Computer Science, University (2015)"}]
        result = _force_additional_background(content, work_experience, education)
        self.assertNotIn("Earlier roles:", result)
        self.assertIn("Education: BSc Computer Science, University (2015).", result)


class ApplyCustomCvSafetyNetsIntegrationTests(unittest.TestCase):
    def test_folds_dataless_role_into_additional_background_not_professional_experience(self):
        content = (
            "# Alex Example\n"
            "alex@example.com\n\n"
            "## PROFESSIONAL PROFILE\n"
            "A profile paragraph.\n\n"
            "## CORE CAPABILITIES\n"
            "**Detection:** Strong SIEM work.\n\n"
            "## PROFESSIONAL EXPERIENCE\n"
            "### SOC Analyst | Acme | Jan 2020 - Present\n"
            "- Investigated alerts\n"
            "### Desktop Support | Old Co | Jan 2015 - Dec 2016\n"
            "- Fabricated bullet the model invented for a dataless role\n\n"
            "## SELECTED ACHIEVEMENTS\n"
            "- Strong achievement\n\n"
            "## PROJECTS\n"
        )
        profile = {
            "skills": [],
            "achievements": [{"title": "Strong achievement", "result": ""}],
            "work_experience": [
                {"role": "SOC Analyst", "company": "Acme", "description": "Real work", "key_responsibilities": ["Investigated alerts"], "start_date": "2020-01", "is_current": True},
                {"role": "Desktop Support", "company": "Old Co", "start_date": "2015-01", "end_date": "2016-12"},
            ],
            "projects": [],
            "platforms_and_tools_display": [],
            "certifications": [],
            "training": [],
            "education": [],
            "community_involvement": [],
        }
        result = apply_custom_cv_safety_nets(content, profile)
        self.assertNotIn("Desktop Support", result.split("## SELECTED ACHIEVEMENTS")[0])
        self.assertIn("## ADDITIONAL BACKGROUND", result)
        self.assertIn("Earlier roles: Desktop Support, Old Co (Jan 2015 - Dec 2016).", result)


if __name__ == "__main__":
    unittest.main()
