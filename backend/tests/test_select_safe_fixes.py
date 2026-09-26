import unittest

from app.services.matching.recommendations import select_safe_fixes

JOB_MATCH_RESULT = {
    "priority_fixes": {
        "top": [
            {"requirement": "SIEM", "tier": "SAFE_OPTIMISATION", "message": "use the term SIEM"},
            {"requirement": "CISSP", "tier": "DO_NOT_ADD", "message": "do not add"},
        ],
        "more": [
            {"requirement": "Microsoft Sentinel", "tier": "EVIDENCE_NEEDED", "message": "needs evidence"},
            {"requirement": "Job title alignment", "tier": "SAFE_OPTIMISATION", "message": "add alias"},
        ],
    }
}


class SelectSafeFixesTests(unittest.TestCase):
    def test_selects_only_requested_safe_optimisation_items(self):
        result = select_safe_fixes(JOB_MATCH_RESULT, ["SIEM", "Job title alignment"])
        names = {f["requirement"] for f in result}
        self.assertEqual(names, {"SIEM", "Job title alignment"})

    def test_searches_both_top_and_more(self):
        result = select_safe_fixes(JOB_MATCH_RESULT, ["Job title alignment"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["requirement"], "Job title alignment")

    def test_never_returns_a_do_not_add_item_even_if_requested(self):
        # The critical safety property: even a client that (maliciously or by
        # bug) requests a DO_NOT_ADD requirement never gets it approved.
        result = select_safe_fixes(JOB_MATCH_RESULT, ["CISSP"])
        self.assertEqual(result, [])

    def test_never_returns_an_evidence_needed_item_even_if_requested(self):
        result = select_safe_fixes(JOB_MATCH_RESULT, ["Microsoft Sentinel"])
        self.assertEqual(result, [])

    def test_mixed_request_only_keeps_safe_ones(self):
        result = select_safe_fixes(JOB_MATCH_RESULT, ["SIEM", "CISSP", "Microsoft Sentinel"])
        self.assertEqual([f["requirement"] for f in result], ["SIEM"])

    def test_unrequested_safe_item_is_not_included(self):
        result = select_safe_fixes(JOB_MATCH_RESULT, [])
        self.assertEqual(result, [])

    def test_unknown_requirement_name_ignored(self):
        result = select_safe_fixes(JOB_MATCH_RESULT, ["Something not in the report"])
        self.assertEqual(result, [])

    def test_missing_priority_fixes_key_returns_empty(self):
        self.assertEqual(select_safe_fixes({}, ["SIEM"]), [])


if __name__ == "__main__":
    unittest.main()
