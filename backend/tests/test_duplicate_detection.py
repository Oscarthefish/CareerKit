import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 - registers every table on Base
from app.api.applications import _find_possible_duplicate_applications
from app.core.database import Base
from app.models.job import JobApplication

JD_A = (
    "We are looking for a Security Analyst to join our growing SOC team in Auckland. "
    "You will triage SIEM alerts, investigate phishing campaigns and malware outbreaks, "
    "run endpoint investigations across our global estate, coordinate incident response "
    "and write clear reports for technical and non-technical stakeholders. Experience with "
    "Splunk, modern EDR tooling and firewall administration is required, along with strong "
    "written communication and an analytical, detail-oriented mindset. You will work rotating "
    "shifts covering extended business hours and support escalations from the wider technology "
    "and platform teams, collaborating closely with engineering, risk and compliance "
    "stakeholders across the organisation on vulnerability remediation and audit readiness. "
    "A relevant tertiary qualification or industry certification is preferred but not essential."
)
JD_B = JD_A.replace("stakeholders.", "stakeholders and leadership.")  # near-identical relist
JD_UNRELATED = (
    "We need a Frontend Developer skilled in React, TypeScript and modern CSS tooling to build "
    "customer-facing dashboards for our retail platform. You will work closely with designers on "
    "accessibility and UI polish, write automated component tests, and ship performant interfaces "
    "across our web product. Experience with design systems, GraphQL and continuous delivery "
    "pipelines is a strong advantage, as is comfort collaborating with product managers, backend "
    "engineers and customer support to prioritise a fast-moving roadmap of user-facing features."
)


class DuplicateDetectionTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()

    def tearDown(self):
        self.db.close()

    def _add(self, **kwargs):
        defaults = {"session_folder": "test"}
        app = JobApplication(**{**defaults, **kwargs})
        self.db.add(app)
        self.db.commit()
        return app

    def test_same_job_url_is_flagged_regardless_of_tracking_params_or_scheme(self):
        self._add(company="Acme", role="SOC Analyst", job_url="https://www.seek.co.nz/job/12345")
        matches = _find_possible_duplicate_applications(
            self.db, company=None, role=None,
            job_url="seek.co.nz/job/12345/?utm_source=linkedin", job_description_raw=None,
        )
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["reason"], "same job link")

    def test_same_company_and_same_role_title_is_flagged(self):
        self._add(company="Acme Bank", role="Senior SOC Analyst")
        matches = _find_possible_duplicate_applications(
            self.db, company="acme bank", role="SOC Analyst", job_url=None, job_description_raw=None,
        )
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["reason"], "same company and a very similar role title")

    def test_same_company_different_role_is_not_flagged_on_role_alone(self):
        self._add(company="Acme Bank", role="Frontend Developer")
        matches = _find_possible_duplicate_applications(
            self.db, company="Acme Bank", role="Security Analyst", job_url=None, job_description_raw=None,
        )
        self.assertEqual(matches, [])

    def test_same_company_and_near_identical_relisted_description_is_flagged_even_without_role(self):
        self._add(company="Acme Bank", role=None, job_description_raw=JD_A)
        matches = _find_possible_duplicate_applications(
            self.db, company="Acme Bank", role=None, job_url=None, job_description_raw=JD_B,
        )
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["reason"], "same company and a very similar job description")

    def test_different_company_is_never_flagged_on_job_description_similarity_alone(self):
        # Two genuinely different employers' ads can share plenty of generic
        # boilerplate - company must match too, or this would false-positive
        # constantly across unrelated jobs in the same field.
        self._add(company="Other Co", role=None, job_description_raw=JD_A)
        matches = _find_possible_duplicate_applications(
            self.db, company="Acme Bank", role=None, job_url=None, job_description_raw=JD_B,
        )
        self.assertEqual(matches, [])

    def test_same_company_but_unrelated_job_description_is_not_flagged(self):
        self._add(company="Acme Bank", role=None, job_description_raw=JD_UNRELATED)
        matches = _find_possible_duplicate_applications(
            self.db, company="Acme Bank", role=None, job_url=None, job_description_raw=JD_A,
        )
        self.assertEqual(matches, [])

    def test_real_regression_different_specialisation_suffix_is_not_flagged(self):
        # Real false positive (NZ Transport Agency): "Principal Protective
        # Security Risk Advisor - Cyber" vs "... - PHYSEC/PERSEC" share a
        # long base title and score a high raw word-overlap ratio, but the
        # "- Cyber" / "- PHYSEC/PERSEC" tail is exactly what makes these two
        # deliberately different roles the candidate is tracking separately.
        self._add(company="NZTA", role="Principal Protective Security Risk Advisor - PHYSEC/PERSEC")
        matches = _find_possible_duplicate_applications(
            self.db, company="NZTA", role="Principal Protective Security Risk Advisor - Cyber",
            job_url=None, job_description_raw=None,
        )
        self.assertEqual(matches, [])

    def test_excludes_its_own_id(self):
        existing = self._add(company="Acme Bank", role="SOC Analyst")
        matches = _find_possible_duplicate_applications(
            self.db, company="Acme Bank", role="SOC Analyst", job_url=None, job_description_raw=None,
            exclude_id=existing.id,
        )
        self.assertEqual(matches, [])

    def test_no_identifying_info_returns_no_matches(self):
        self._add(company="Acme Bank", role="SOC Analyst")
        matches = _find_possible_duplicate_applications(
            self.db, company=None, role=None, job_url=None, job_description_raw=None,
        )
        self.assertEqual(matches, [])


if __name__ == "__main__":
    unittest.main()
