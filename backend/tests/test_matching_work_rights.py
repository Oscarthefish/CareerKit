import unittest

from app.services.matching.work_rights import match_work_rights_requirement


class MatchWorkRightsRequirementTests(unittest.TestCase):
    def test_real_regression_citizen_matches_au_nz_citizenship_requirement(self):
        # Verbatim shape of the real bug: "AU / NZ citizenship preferred"
        # came back PARTIAL_EVIDENCE citing completely unrelated skills and
        # work-experience bullets (e.g. "Skill: AlienVault OTX") for a
        # candidate who is, in fact, a recorded NZ citizen.
        result = match_work_rights_requirement("AU / NZ citizenship preferred", {"nz_work_rights": "Citizen/PR"})
        self.assertIsNotNone(result)
        self.assertEqual(result["evidence_level"], "EXPLICIT")
        self.assertIn("Citizen/PR", result["sources"][0])

    def test_matches_various_phrasings(self):
        for phrasing in [
            "Must have NZ work rights",
            "Right to work in New Zealand required",
            "Valid work visa or citizenship",
            "Permanent resident or citizen status",
        ]:
            with self.subTest(phrasing=phrasing):
                result = match_work_rights_requirement(phrasing, {"nz_work_rights": "NZ Citizen"})
                self.assertIsNotNone(result)
                self.assertEqual(result["evidence_level"], "EXPLICIT")

    def test_not_a_work_rights_requirement_returns_none(self):
        result = match_work_rights_requirement("SIEM experience", {"nz_work_rights": "Citizen/PR"})
        self.assertIsNone(result)

    def test_unclear_status_falls_through_to_the_normal_pass(self):
        # Mirrors tenure.py's own discipline: only ever confirm a real
        # match, never assert a shortfall/negative itself - left to the
        # normal LLM-assisted pass instead.
        result = match_work_rights_requirement("AU / NZ citizenship preferred", {"nz_work_rights": "Needs sponsorship"})
        self.assertIsNone(result)

    def test_missing_status_falls_through_to_the_normal_pass(self):
        result = match_work_rights_requirement("AU / NZ citizenship preferred", {})
        self.assertIsNone(result)

    def test_missing_personal_dict_does_not_crash(self):
        result = match_work_rights_requirement("AU / NZ citizenship preferred", None)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
