import unittest

from app.services.insights.skill_gaps import compute_skill_gaps


def _app(role, company, coverage_pairs):
    return {
        "role": role, "company": company,
        "requirement_coverage": [{"name": n, "coverage": c} for n, c in coverage_pairs],
    }


class ComputeSkillGapsTests(unittest.TestCase):
    def test_below_min_appearances_excluded(self):
        apps = [_app("SOC Analyst", "Acme", [("Threat Hunting", "NO_EVIDENCE")])]
        self.assertEqual(compute_skill_gaps(apps, min_appearances=2), [])

    def test_frequent_and_weak_is_surfaced(self):
        apps = [
            _app("SOC Analyst", "Acme", [("Threat Hunting", "NO_EVIDENCE")]),
            _app("Senior SOC Analyst", "Beta", [("Threat Hunting", "PARTIAL_EVIDENCE")]),
            _app("Lead Analyst", "Gamma", [("Threat Hunting", "NO_EVIDENCE")]),
        ]
        gaps = compute_skill_gaps(apps, min_appearances=2)
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["skill"], "Threat Hunting")
        self.assertEqual(gaps[0]["appearances"], 3)
        self.assertEqual(gaps[0]["weak_count"], 3)
        self.assertEqual(len(gaps[0]["sample_roles"]), 3)

    def test_frequent_but_always_strong_is_not_surfaced(self):
        apps = [
            _app("SOC Analyst", "Acme", [("Splunk", "STRONG_EVIDENCE")]),
            _app("Senior SOC Analyst", "Beta", [("Splunk", "STRONG_EVIDENCE")]),
        ]
        self.assertEqual(compute_skill_gaps(apps, min_appearances=2), [])

    def test_synonyms_merged_into_one_bucket(self):
        # "SOC" and "Security Operations Centre" are the same skill (see
        # synonyms.py) - this must count as ONE requirement appearing twice,
        # not two separate requirements each appearing once.
        apps = [
            _app("Analyst", "Acme", [("SOC", "NO_EVIDENCE")]),
            _app("Analyst", "Beta", [("Security Operations Centre", "NO_EVIDENCE")]),
        ]
        gaps = compute_skill_gaps(apps, min_appearances=2)
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["appearances"], 2)

    def test_duplicate_synonym_within_one_application_not_double_counted(self):
        apps = [
            _app("Analyst", "Acme", [("SOC", "NO_EVIDENCE"), ("Security Operations Centre", "NO_EVIDENCE")]),
            _app("Analyst", "Beta", [("SOC", "NO_EVIDENCE")]),
        ]
        gaps = compute_skill_gaps(apps, min_appearances=2)
        self.assertEqual(gaps[0]["appearances"], 2)  # not 3

    def test_ranked_by_weak_count_then_appearances(self):
        apps = [
            _app("A", "X", [("Skill A", "NO_EVIDENCE"), ("Skill B", "NO_EVIDENCE")]),
            _app("B", "Y", [("Skill A", "NO_EVIDENCE"), ("Skill B", "PARTIAL_EVIDENCE")]),
            _app("C", "Z", [("Skill A", "STRONG_EVIDENCE"), ("Skill B", "NO_EVIDENCE")]),
        ]
        gaps = compute_skill_gaps(apps, min_appearances=2)
        # Skill B is weak in all 3 appearances, Skill A only in 2 - B should rank first.
        self.assertEqual(gaps[0]["skill"], "Skill B")
        self.assertEqual(gaps[0]["weak_count"], 3)

    def test_empty_applications_returns_empty(self):
        self.assertEqual(compute_skill_gaps([]), [])

    def test_missing_requirement_coverage_key_does_not_crash(self):
        self.assertEqual(compute_skill_gaps([{"role": "A", "company": "B"}]), [])


if __name__ == "__main__":
    unittest.main()
