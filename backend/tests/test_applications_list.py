import json
import unittest
from unittest.mock import Mock

from app.api.applications import _export_download_name, _job_match_summary


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


if __name__ == "__main__":
    unittest.main()
