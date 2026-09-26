import unittest
from datetime import date, timedelta

from app.services.matching.tenure import compute_tenure_years, match_tenure_requirement


def _months_ago(n: int) -> str:
    d = date.today()
    total = d.year * 12 + (d.month - 1) - n
    return f"{total // 12}-{total % 12 + 1:02d}"


class ComputeTenureYearsTests(unittest.TestCase):
    def test_sums_matching_roles_only(self):
        work_experience = [
            {"role": "Senior Security Operations Analyst", "start_date": "2022-01", "end_date": "2026-08"},
            {"role": "Security Operations Analyst", "start_date": "2018-01", "end_date": "2022-01"},
            {"role": "Desktop Support Supervisor", "start_date": "2011-09", "end_date": "2014-09"},
        ]
        years = compute_tenure_years(work_experience, ("security operations", "soc"))
        self.assertAlmostEqual(years, 8.6, delta=0.2)

    def test_current_role_counts_to_today(self):
        work_experience = [{"role": "SOC Analyst", "start_date": _months_ago(24), "is_current": True}]
        years = compute_tenure_years(work_experience, ("soc",))
        self.assertAlmostEqual(years, 2.0, delta=0.15)

    def test_non_matching_role_contributes_nothing(self):
        work_experience = [{"role": "Desktop Support", "start_date": "2010-01", "end_date": "2020-01"}]
        self.assertEqual(compute_tenure_years(work_experience, ("soc",)), 0.0)

    def test_missing_or_malformed_dates_contribute_nothing(self):
        work_experience = [{"role": "SOC Analyst", "start_date": None, "end_date": "2020-01"}]
        self.assertEqual(compute_tenure_years(work_experience, ("soc",)), 0.0)


class MatchTenureRequirementTests(unittest.TestCase):
    def setUp(self):
        self.work_experience = [
            {"role": "Senior Security Operations Analyst", "company": "X", "start_date": "2022-01",
             "end_date": "2026-08", "is_current": False},
            {"role": "Security Operations Analyst", "company": "X", "start_date": "2018-01",
             "end_date": "2022-01", "is_current": False},
        ]

    def test_matches_when_real_tenure_meets_the_threshold(self):
        result = match_tenure_requirement("At least 5 years of dedicated Security Operations Centre experience",
                                           self.work_experience)
        self.assertIsNotNone(result)
        self.assertEqual(result["evidence_level"], "EXPLICIT")
        self.assertIn("Senior Security Operations Analyst", result["sources"][0])

    def test_matches_a_lower_threshold_too(self):
        result = match_tenure_requirement("3+ years SOC experience", self.work_experience)
        self.assertIsNotNone(result)
        self.assertEqual(result["evidence_level"], "EXPLICIT")

    def test_returns_none_when_threshold_not_met(self):
        result = match_tenure_requirement("15+ years SOC experience", self.work_experience)
        self.assertIsNone(result)

    def test_returns_none_for_a_non_tenure_requirement(self):
        result = match_tenure_requirement("Demonstrated ownership of complex incident response", self.work_experience)
        self.assertIsNone(result)

    def test_returns_none_for_a_tenure_requirement_outside_security(self):
        # "5 years of project management experience" - has a year count but
        # isn't a security-tenure claim this function should confidently compute.
        result = match_tenure_requirement("5+ years of project management experience", self.work_experience)
        self.assertIsNone(result)

    def test_broader_security_keyword_also_matches(self):
        work_experience = self.work_experience + [
            {"role": "Network Security Analyst", "company": "Y", "start_date": "2014-10", "end_date": "2016-02"},
        ]
        result = match_tenure_requirement("5+ years of cyber security experience", work_experience)
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
