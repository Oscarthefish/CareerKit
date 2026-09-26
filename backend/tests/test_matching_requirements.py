import unittest

from app.services.matching.requirements import _validate_requirements, bucket_by_importance


class RequirementValidationTests(unittest.TestCase):
    def test_rejects_invalid_importance(self):
        error = _validate_requirements({"requirements": [
            {"name": "Splunk", "type": "tool", "importance": "mandatory"},
        ]})
        self.assertIsNotNone(error)
        self.assertIn("importance", error)

    def test_rejects_invalid_type(self):
        error = _validate_requirements({"requirements": [
            {"name": "Splunk", "type": "platform", "importance": "critical"},
        ]})
        self.assertIsNotNone(error)
        self.assertIn("type", error)

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
