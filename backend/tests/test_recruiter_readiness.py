import unittest

from app.services.recruiter.scoring import (
    _validate_review,
    compute_recruiter_readiness,
)

GOOD_REVIEW = {
    "first_impression": "Strong opening.",
    "top_third_strength": "strong",
    "top_third_notes": "...",
    "target_role_clarity": "clear",
    "credibility_rating": "high",
    "credibility_notes": "...",
    "generic_rating": "specific",
    "generic_notes": "...",
    "missing_evidence": [],
    "weak_bullets": [],
    "repeated_wording": [],
    "ats_issues": [],
    "readability_issues": [],
    "shortlisting_blockers": [],
    "priority_fixes": [],
    "overall_verdict": "Excellent.",
}

BAD_REVIEW = {
    **GOOD_REVIEW,
    "top_third_strength": "weak",
    "target_role_clarity": "missing",
    "credibility_rating": "low",
    "generic_rating": "generic",
    "missing_evidence": ["a", "b", "c"],
    "weak_bullets": ["1", "2", "3", "4", "5"],
    "repeated_wording": ["x", "y"],
    "readability_issues": ["p", "q", "r"],
    "shortlisting_blockers": ["blocker 1", "blocker 2"],
}

CV_WITH_10_BULLETS = "# Name\n\n## SKILLS\n\n" + "\n".join(f"- bullet {i}" for i in range(10))


class ValidateReviewTests(unittest.TestCase):
    def test_valid_review_passes(self):
        self.assertIsNone(_validate_review(GOOD_REVIEW))

    def test_invalid_enum_rejected(self):
        bad = {**GOOD_REVIEW, "top_third_strength": "amazing"}
        self.assertIsNotNone(_validate_review(bad))

    def test_missing_priority_fixes_rejected(self):
        bad = dict(GOOD_REVIEW)
        del bad["priority_fixes"]
        self.assertIsNotNone(_validate_review(bad))

    def test_non_list_field_rejected(self):
        bad = {**GOOD_REVIEW, "weak_bullets": "not a list"}
        self.assertIsNotNone(_validate_review(bad))


class ComputeRecruiterReadinessTests(unittest.TestCase):
    def test_good_review_scores_high(self):
        result = compute_recruiter_readiness(GOOD_REVIEW, CV_WITH_10_BULLETS)
        self.assertGreaterEqual(result["score"], 90)
        self.assertEqual(result["band"], "Excellent")

    def test_bad_review_scores_much_lower(self):
        good = compute_recruiter_readiness(GOOD_REVIEW, CV_WITH_10_BULLETS)
        bad = compute_recruiter_readiness(BAD_REVIEW, CV_WITH_10_BULLETS)
        self.assertLess(bad["score"], good["score"])

    def test_score_bounded_0_to_100(self):
        for review in (GOOD_REVIEW, BAD_REVIEW):
            result = compute_recruiter_readiness(review, CV_WITH_10_BULLETS)
            self.assertGreaterEqual(result["score"], 0)
            self.assertLessEqual(result["score"], 100)
        for sub in result["sub_scores"].values():
            self.assertGreaterEqual(sub, 0)
            self.assertLessEqual(sub, 100)

    def test_deterministic(self):
        first = compute_recruiter_readiness(BAD_REVIEW, CV_WITH_10_BULLETS)
        second = compute_recruiter_readiness(BAD_REVIEW, CV_WITH_10_BULLETS)
        self.assertEqual(first, second)

    def test_weak_bullet_ratio_matters_not_just_raw_count(self):
        # 2 weak bullets out of 10 is a much smaller problem than 2 weak
        # bullets out of 3 - the score should reflect the ratio.
        review_with_2_weak = {**GOOD_REVIEW, "weak_bullets": ["a", "b"]}
        few_bullets_cv = "# Name\n\n## SKILLS\n\n- bullet 1\n- bullet 2\n- bullet 3\n"
        many_bullets_result = compute_recruiter_readiness(review_with_2_weak, CV_WITH_10_BULLETS)
        few_bullets_result = compute_recruiter_readiness(review_with_2_weak, few_bullets_cv)
        self.assertGreater(
            many_bullets_result["sub_scores"]["achievement_quality"],
            few_bullets_result["sub_scores"]["achievement_quality"],
        )

    def test_missing_bullet_count_does_not_crash(self):
        result = compute_recruiter_readiness(GOOD_REVIEW, "")
        self.assertIn("achievement_quality", result["sub_scores"])

    def test_unknown_enum_value_falls_back_rather_than_crashing(self):
        # compute_recruiter_readiness should never be called on an unvalidated
        # review, but as a defence-in-depth check it must not KeyError.
        odd = {**GOOD_REVIEW, "top_third_strength": "somehow_invalid"}
        result = compute_recruiter_readiness(odd, CV_WITH_10_BULLETS)
        self.assertIsInstance(result["score"], int)


if __name__ == "__main__":
    unittest.main()
