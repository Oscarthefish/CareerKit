import json
import unittest
from types import SimpleNamespace

from app.services.matching.grounding import (
    JobText, ground_scorecard, ground_job_analysis, ground_requirements, grounded_scorecard,
)

# A synthetic advert (this repo is public). The regression it guards: a
# scorecard listed "Fraud Intelligence" under Do Not Claim for an advert
# like this one - a phrase that only appears in match_scorecard.md's own
# illustrative examples, never in the job.
JD = """Example Security Analyst
You will triage, investigate and respond to Level 1 and Level 2 alerts, incidents and risks.
You will coordinate vulnerability management, including remediation tracking and reporting.
You will contribute to uplift programmes, assurance activities and risk management initiatives.
You will support penetration testing and help maintain policies, standards and procedures.
We value strong communication and stakeholder engagement, and you will work closely with the team leader.
Certifications such as SC-200 or CISSP are a plus. You bring an analytical mindset.
You will produce written reports for executives."""


class JobTextTests(unittest.TestCase):
    def setUp(self):
        self.job = JobText(JD)

    def test_phrases_from_the_advert_are_grounded_despite_paraphrase(self):
        for phrase in ("Risk Management", "Triage and Investigation", "Vulnerability Remediation",
                       "Penetration Testing", "Security Standards and Procedures", "Report writing",
                       "Team leadership", "Analytical skills",
                       "SC-200", "Stakeholder Engagement"):
            self.assertTrue(self.job.grounds(phrase), phrase)

    def test_phrases_absent_from_the_advert_are_not_grounded(self):
        for phrase in ("Fraud Intelligence", "Microsoft Sentinel", "Cloud Infrastructure Security",
                       "insurance claims management", "Splunk Enterprise Security", "SIEM", "EDR"):
            self.assertFalse(self.job.grounds(phrase), phrase)

    def test_short_stems_need_an_exact_match(self):
        self.assertFalse(JobText("Invoices were sent weekly").grounds("Sentinel"))
        self.assertFalse(JobText("Our security team").grounds("SOC"))

    def test_purely_generic_phrase_is_kept(self):
        self.assertTrue(self.job.grounds("Security experience"))

    def test_long_requirement_tolerates_one_paraphrased_word_in_three(self):
        self.assertTrue(self.job.grounds("Coordinate vulnerability remediation programmes with stakeholders"))


class GroundScorecardTests(unittest.TestCase):
    SCORECARD = {
        "overall_fit": "good",
        "strong_matches": [{"skill": "Incident Response", "evidence": "x"},
                           {"skill": "Microsoft Sentinel", "evidence": "y"}],
        "genuine_gaps": [{"skill": "Security Standards and Procedures", "impact": "z"}],
        "do_not_claim": ["Security Standards and Procedures", "Fraud Intelligence", "Risk Management"],
        "ats_keywords_to_include": ["Vulnerability Management", "Cortex XDR"],
        "safe_claims": ["has worked with Splunk"],  # free text about the candidate - untouched
    }

    def test_removes_only_entries_the_advert_never_mentions(self):
        out = ground_scorecard(self.SCORECARD, JD)
        self.assertEqual([m["skill"] for m in out["strong_matches"]], ["Incident Response"])
        self.assertEqual(out["do_not_claim"], ["Security Standards and Procedures", "Risk Management"])
        self.assertEqual(out["ats_keywords_to_include"], ["Vulnerability Management"])
        self.assertEqual(out["genuine_gaps"], self.SCORECARD["genuine_gaps"])
        self.assertEqual(out["safe_claims"], self.SCORECARD["safe_claims"])

    def test_does_not_mutate_the_input(self):
        ground_scorecard(self.SCORECARD, JD)
        self.assertIn("Fraud Intelligence", self.SCORECARD["do_not_claim"])

    def test_no_advert_means_no_filtering(self):
        self.assertEqual(ground_scorecard(self.SCORECARD, ""), self.SCORECARD)
        self.assertEqual(ground_scorecard(self.SCORECARD, None), self.SCORECARD)

    def test_reads_from_a_stored_application(self):
        app = SimpleNamespace(match_scorecard=json.dumps(self.SCORECARD), job_description_raw=JD)
        self.assertNotIn("Fraud Intelligence", grounded_scorecard(app)["do_not_claim"])
        self.assertIsNone(grounded_scorecard(SimpleNamespace(match_scorecard=None, job_description_raw=JD)))


class GroundAnalysisAndRequirementsTests(unittest.TestCase):
    def test_job_analysis_skill_lists_are_grounded(self):
        analysis = {"job_title": "Security Analyst",
                    "required_skills": ["Risk Management", "Microsoft Sentinel"],
                    "preferred_skills": ["Penetration Testing", "Fraud Intelligence"],
                    "red_flags": ["Fraud Intelligence"]}  # not a skill list - untouched
        out = ground_job_analysis(analysis, JD)
        self.assertEqual(out["required_skills"], ["Risk Management"])
        self.assertEqual(out["preferred_skills"], ["Penetration Testing"])
        self.assertEqual(out["red_flags"], ["Fraud Intelligence"])

    def test_job_match_requirements_are_grounded(self):
        reqs = [{"name": "Risk Management"}, {"name": "Microsoft Sentinel"}, {"name": "SC-200"}]
        self.assertEqual([r["name"] for r in ground_requirements(reqs, JD)], ["Risk Management", "SC-200"])


if __name__ == "__main__":
    unittest.main()
