import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.profile_service import _platforms_and_tools_lines, _functional_group_for


class _Skill:
    """Minimal stand-in for a Skill ORM row - _platforms_and_tools_lines only
    reads .name and .tool_category, so a real DB-backed instance isn't needed."""
    def __init__(self, name: str, tool_category: str | None):
        self.name = name
        self.tool_category = tool_category


class FunctionalGroupForTests(unittest.TestCase):
    def test_known_category_maps_to_its_group(self):
        self.assertEqual(_functional_group_for("SIEM"), "SIEM & Investigation")
        self.assertEqual(_functional_group_for("EDR / XDR"), "Endpoint & Detection")
        self.assertEqual(_functional_group_for("Firewalls"), "Network, DNS & Web")
        self.assertEqual(_functional_group_for("Threat Intelligence / OSINT"), "Threat Intelligence & Supporting Tools")
        self.assertEqual(_functional_group_for("Password Management"), "Identity & Access")
        self.assertEqual(_functional_group_for("Case Management"), "Case Management & Orchestration")
        self.assertEqual(_functional_group_for("Security Operations Platforms"), "Case Management & Orchestration")

    def test_matching_is_case_insensitive(self):
        self.assertEqual(_functional_group_for("siem"), "SIEM & Investigation")
        self.assertEqual(_functional_group_for("  EDR / XDR  "), "Endpoint & Detection")

    def test_unknown_category_falls_back_to_other_tools(self):
        # A new/unusual tool_category a user adds later must still show up
        # somewhere rather than being silently dropped.
        self.assertEqual(_functional_group_for("Some Brand New Category"), "Other Tools")

    def test_none_category_falls_back_to_other_tools(self):
        self.assertEqual(_functional_group_for(None), "Other Tools")


class PlatformsAndToolsLinesTests(unittest.TestCase):
    def test_groups_the_real_xero_tool_set_into_the_expected_buckets(self):
        skills = [
            _Skill("Jira", "Case Management"),
            _Skill("ZoneFox", "DLP"),
            _Skill("Cisco Umbrella", "DNS Security"),
            _Skill("Thinkst Canary / Canarytokens", "Deception Technology"),
            _Skill("Cisco AMP", "EDR / XDR"),
            _Skill("Palo Alto Cortex XDR", "EDR / XDR"),
            _Skill("Cisco Secure Email (ESA)", "Email Security"),
            _Skill("Mimecast", "Email Security"),
            _Skill("Trend Micro OfficeScan", "Endpoint Protection"),
            _Skill("Palo Alto Networks (NGFW)", "Firewalls"),
            _Skill("Passwordstate / Password Manager Pro", "Password Management"),
            _Skill("Splunk Enterprise Security", "SIEM"),
            _Skill("Cisco SecureX", "Security Operations Platforms"),
            _Skill("AbuseIPDB", "Threat Intelligence / OSINT"),
            _Skill("Tenable Nessus", "Vulnerability Scanning"),
            _Skill("F5 WAF", "WAF"),
        ]
        lines = _platforms_and_tools_lines(skills)
        # 14 fine-grained tags collapse to a handful of functional lines.
        self.assertLessEqual(len(lines), 6)
        by_group = {line.split(":", 1)[0]: line for line in lines}
        self.assertIn("Splunk Enterprise Security", by_group["SIEM & Investigation"])
        # Jira is ticketing/case management, not a SIEM - it must not land
        # in the same group as Splunk, even though both are SOC-adjacent.
        self.assertNotIn("Jira", by_group["SIEM & Investigation"])
        self.assertIn("Jira", by_group["Case Management & Orchestration"])
        self.assertIn("Cisco SecureX", by_group["Case Management & Orchestration"])
        self.assertIn("Palo Alto Cortex XDR", by_group["Endpoint & Detection"])
        self.assertIn("Cisco AMP", by_group["Endpoint & Detection"])
        self.assertIn("Palo Alto Networks (NGFW)", by_group["Network, DNS & Web"])
        self.assertIn("Cisco Umbrella", by_group["Network, DNS & Web"])
        self.assertIn("F5 WAF", by_group["Network, DNS & Web"])
        self.assertIn("AbuseIPDB", by_group["Threat Intelligence & Supporting Tools"])
        self.assertIn("Mimecast", by_group["Threat Intelligence & Supporting Tools"])
        self.assertIn("Passwordstate / Password Manager Pro", by_group["Identity & Access"])

    def test_display_order_is_fixed_not_alphabetical(self):
        skills = [
            _Skill("Passwordstate", "Password Management"),
            _Skill("Splunk", "SIEM"),
            _Skill("Cortex XDR", "EDR / XDR"),
        ]
        lines = _platforms_and_tools_lines(skills)
        groups = [line.split(":", 1)[0] for line in lines]
        self.assertEqual(groups, ["SIEM & Investigation", "Endpoint & Detection", "Identity & Access"])

    def test_unmapped_category_appears_under_other_tools_not_dropped(self):
        skills = [_Skill("Some Tool", "A Brand New Category")]
        lines = _platforms_and_tools_lines(skills)
        self.assertEqual(lines, ["Other Tools: Some Tool"])

    def test_duplicate_product_names_across_skills_are_not_repeated(self):
        skills = [_Skill("Jira", "Case Management"), _Skill("Jira", "Security Operations Platforms")]
        lines = _platforms_and_tools_lines(skills)
        self.assertEqual(lines, ["Case Management & Orchestration: Jira"])

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(_platforms_and_tools_lines([]), [])


if __name__ == "__main__":
    unittest.main()
