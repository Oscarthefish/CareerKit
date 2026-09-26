import json
import unittest

from app.api.applications import _job_match_summary


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


if __name__ == "__main__":
    unittest.main()
