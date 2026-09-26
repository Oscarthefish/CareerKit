import unittest

from app.services.matching.scoring import (
    coverage_for,
    compute_job_match,
    hard_skills_table,
    keyword_coverage,
    requirement_coverage_rows,
    score_band,
)


def _req(name, type_, importance, evidence_level, confidence=0.9, sources=None):
    return {
        "name": name, "type": type_, "importance": importance,
        "evidence_level": evidence_level, "confidence": confidence,
        "sources": sources or [], "rationale": "",
    }


class ScoreBandTests(unittest.TestCase):
    def test_bands(self):
        self.assertEqual(score_band(95), "Excellent alignment")
        self.assertEqual(score_band(90), "Excellent alignment")
        self.assertEqual(score_band(85), "Strong alignment")
        self.assertEqual(score_band(75), "Good alignment")
        self.assertEqual(score_band(65), "Moderate alignment")
        self.assertEqual(score_band(10), "Significant gaps")
        self.assertEqual(score_band(0), "Significant gaps")


class CoverageForTests(unittest.TestCase):
    def test_explicit_is_strong(self):
        self.assertEqual(coverage_for("EXPLICIT", 0.9), "STRONG_EVIDENCE")

    def test_inferred_high_confidence_is_strong(self):
        self.assertEqual(coverage_for("INFERRED", 0.85), "STRONG_EVIDENCE")

    def test_inferred_low_confidence_is_partial(self):
        self.assertEqual(coverage_for("INFERRED", 0.5), "PARTIAL_EVIDENCE")

    def test_possible_is_partial(self):
        self.assertEqual(coverage_for("POSSIBLE", 0.4), "PARTIAL_EVIDENCE")

    def test_not_found_is_no_evidence(self):
        self.assertEqual(coverage_for("NOT_FOUND", 0.5), "NO_EVIDENCE")

    def test_unknown_level_maps_to_unknown_coverage(self):
        self.assertEqual(coverage_for("SOMETHING_ELSE", 0.5), "UNKNOWN")


class ComputeJobMatchTests(unittest.TestCase):
    def test_all_explicit_critical_scores_100(self):
        reqs = [_req("Splunk", "tool", "critical", "EXPLICIT")]
        title_match = {"state": "EXACT_MATCH"}
        result = compute_job_match(reqs, title_match)
        self.assertEqual(result["overall"], 100)
        self.assertEqual(result["band"], "Excellent alignment")

    def test_all_not_found_scores_zero(self):
        reqs = [_req("Microsoft Sentinel", "tool", "critical", "NOT_FOUND")]
        # No title to compare (state=None) so only the requirement contributes -
        # a NO_ALIGNMENT title deliberately still contributes a small nonzero
        # floor score rather than a hard zero (see STATE_SCORE), which is
        # covered separately below.
        result = compute_job_match(reqs, {"state": None})
        self.assertEqual(result["overall"], 0)
        self.assertEqual(result["band"], "Significant gaps")

    def test_no_alignment_title_still_only_yields_a_small_floor_score(self):
        reqs = [_req("Microsoft Sentinel", "tool", "critical", "NOT_FOUND")]
        result = compute_job_match(reqs, {"state": "NO_ALIGNMENT"})
        self.assertLessEqual(result["overall"], 5)

    def test_score_bounded_0_to_100(self):
        reqs = [_req(f"Req{i}", "hard_skill", "critical", "NOT_FOUND") for i in range(5)]
        reqs += [_req("Splunk", "tool", "desirable", "EXPLICIT")]
        result = compute_job_match(reqs, {"state": None})
        self.assertGreaterEqual(result["overall"], 0)
        self.assertLessEqual(result["overall"], 100)

    def test_deterministic_same_input_same_score(self):
        reqs = [
            _req("Splunk", "tool", "critical", "EXPLICIT"),
            _req("Microsoft Sentinel", "tool", "critical", "NOT_FOUND"),
            _req("Leadership", "soft_skill", "desirable", "INFERRED", confidence=0.5),
        ]
        title_match = {"state": "STRONG_EQUIVALENT"}
        first = compute_job_match(reqs, title_match)
        second = compute_job_match(reqs, title_match)
        self.assertEqual(first, second)

    def test_sub_scores_only_include_their_own_type(self):
        reqs = [
            _req("Splunk", "tool", "critical", "EXPLICIT"),
            _req("CISSP", "certification", "critical", "NOT_FOUND"),
        ]
        result = compute_job_match(reqs, {"state": None})
        self.assertEqual(result["sub_scores"]["hard_skills"]["score"], 100)
        self.assertEqual(result["sub_scores"]["qualifications"]["score"], 0)
        self.assertIsNone(result["sub_scores"]["soft_skills"]["score"])  # no soft_skill requirements at all

    def test_job_title_folds_into_overall(self):
        reqs = [_req("Splunk", "tool", "desirable", "EXPLICIT")]
        strong_title = compute_job_match(reqs, {"state": "EXACT_MATCH"})
        weak_title = compute_job_match(reqs, {"state": "NO_ALIGNMENT"})
        self.assertGreater(strong_title["overall"], weak_title["overall"])


class TableBuildersTests(unittest.TestCase):
    def test_requirement_coverage_rows_shape(self):
        reqs = [_req("Splunk", "tool", "critical", "EXPLICIT", sources=["Skill: Splunk"])]
        rows = requirement_coverage_rows(reqs)
        self.assertEqual(rows[0]["coverage"], "STRONG_EVIDENCE")
        self.assertEqual(rows[0]["icon"], "🟢")
        self.assertEqual(rows[0]["sources"], ["Skill: Splunk"])

    def test_hard_skills_table_filters_to_hard_skill_types(self):
        reqs = [
            _req("Splunk", "tool", "critical", "EXPLICIT"),
            _req("Leadership", "soft_skill", "desirable", "EXPLICIT"),
        ]
        rows = hard_skills_table(reqs)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["skill"], "Splunk")
        self.assertEqual(rows[0]["assessment"], "Match")

    def test_keyword_coverage_counts(self):
        reqs = [
            _req("A", "hard_skill", "critical", "EXPLICIT"),
            _req("B", "hard_skill", "critical", "INFERRED"),
            _req("C", "hard_skill", "critical", "NOT_FOUND"),
        ]
        stats = keyword_coverage(reqs)
        self.assertEqual(stats["matched"], 1)
        self.assertEqual(stats["partial"], 1)
        self.assertEqual(stats["missing"], 1)
        self.assertEqual(stats["total"], 3)


if __name__ == "__main__":
    unittest.main()
