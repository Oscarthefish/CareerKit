import unittest

from app.services.matching.requirements import _normalize_type, _validate_requirements, bucket_by_importance


class RequirementValidationTests(unittest.TestCase):
    def test_rejects_invalid_importance(self):
        error = _validate_requirements({"requirements": [
            {"name": "Splunk", "type": "tool", "importance": "mandatory"},
        ]})
        self.assertIsNotNone(error)
        self.assertIn("importance", error)

    def test_rejects_a_genuinely_unrecognisable_type(self):
        error = _validate_requirements({"requirements": [
            {"name": "Splunk", "type": "banana", "importance": "critical"},
        ]})
        self.assertIsNotNone(error)
        self.assertIn("type", error)

    def test_normalizes_a_known_near_miss_type_instead_of_rejecting(self):
        # Observed in practice: the model classifies a tenure requirement
        # like "3+ years SOC experience" as type "experience", which isn't in
        # the enum - this used to fail validation (and, after a second failed
        # retry, raise and surface as a 502 to the user) rather than being
        # recoverable.
        requirements = [{"name": "3+ years SOC experience", "type": "experience", "importance": "critical"}]
        error = _validate_requirements({"requirements": requirements})
        self.assertIsNone(error)
        self.assertEqual(requirements[0]["type"], "hard_skill")  # normalized in place

    def test_normalizes_platform_to_tool(self):
        requirements = [{"name": "Splunk", "type": "platform", "importance": "critical"}]
        error = _validate_requirements({"requirements": requirements})
        self.assertIsNone(error)
        self.assertEqual(requirements[0]["type"], "tool")

    def test_rejects_duplicate_names(self):
        error = _validate_requirements({"requirements": [
            {"name": "Splunk", "type": "tool", "importance": "critical"},
            {"name": "splunk", "type": "tool", "importance": "important"},
        ]})
        self.assertIsNotNone(error)
        self.assertIn("duplicate", error.lower())

    def test_rejects_empty_list(self):
        self.assertIsNotNone(_validate_requirements({"requirements": []}))
        self.assertIsNotNone(_validate_requirements({}))

    def test_accepts_valid_requirements(self):
        error = _validate_requirements({"requirements": [
            {"name": "Splunk", "type": "tool", "importance": "critical", "source_text": "..."},
            {"name": "Leadership", "type": "soft_skill", "importance": "desirable"},
        ]})
        self.assertIsNone(error)


class NormalizeTypeTests(unittest.TestCase):
    def test_passes_through_a_real_type_unchanged(self):
        self.assertEqual(_normalize_type("hard_skill"), "hard_skill")

    def test_normalizes_case_and_spacing_of_a_real_type(self):
        self.assertEqual(_normalize_type("HARD_SKILL"), "hard_skill")
        self.assertEqual(_normalize_type("Soft Skill"), "soft_skill")

    def test_returns_none_for_unrecognised_type(self):
        self.assertIsNone(_normalize_type("banana"))

    def test_returns_none_for_non_string_input(self):
        self.assertIsNone(_normalize_type(None))
        self.assertIsNone(_normalize_type(123))


class BucketByImportanceTests(unittest.TestCase):
    def test_buckets_all_levels_present_even_when_empty(self):
        buckets = bucket_by_importance([])
        self.assertEqual(set(buckets.keys()), {"critical", "important", "desirable"})
        self.assertEqual(buckets["critical"], [])

    def test_groups_by_importance(self):
        reqs = [
            {"name": "A", "importance": "critical"},
            {"name": "B", "importance": "desirable"},
            {"name": "C", "importance": "critical"},
        ]
        buckets = bucket_by_importance(reqs)
        self.assertEqual([r["name"] for r in buckets["critical"]], ["A", "C"])
        self.assertEqual([r["name"] for r in buckets["desirable"]], ["B"])
        self.assertEqual(buckets["important"], [])


if __name__ == "__main__":
    unittest.main()
