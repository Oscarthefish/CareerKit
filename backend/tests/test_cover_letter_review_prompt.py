import json
import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 - registers every table on Base
from app.api.applications import cover_letter_review_prompt
from app.core.database import Base
from app.models.job import JobApplication

ADVERT = "Security Analyst. You will triage SIEM alerts, run investigations and write reports. AWS experience desirable."
CV = (
    "# Jane Example\njane@example.com | 021 000 0000 | Auckland\n\n"
    "## PROFESSIONAL PROFILE\nSOC analyst with Splunk SIEM investigation experience.\n\n"
    "## EXPERIENCE\n### Analyst | Acme | 2020 – 2026\n- Investigated SIEM alerts in Splunk ES\n"
)


class CoverLetterReviewPromptTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()
        scorecard = {"do_not_claim": ["SIEMs", "AWS"], "strong_matches": []}
        self.app = JobApplication(
            session_folder="test", company="Acme Bank", role="Security Analyst", job_description_raw=ADVERT,
            cover_letter="Dear Hiring Manager,\n\nI am applying for the role.", custom_cv=CV,
            match_scorecard=json.dumps(scorecard),
        )
        self.db.add(self.app)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def _prompt(self):
        return cover_letter_review_prompt(self.app.id, self.db)["prompt"]

    def test_includes_advert_letter_and_background(self):
        p = self._prompt()
        self.assertIn("Security Analyst role at Acme Bank", p)
        self.assertIn(ADVERT, p)
        self.assertIn("I am applying for the role.", p)
        self.assertIn("Investigated SIEM alerts in Splunk ES", p)
        self.assertIn('greeting "Kia ora"', p)

    def test_contact_details_are_left_out(self):
        p = self._prompt()
        self.assertNotIn("jane@example.com", p)
        self.assertNotIn("021 000 0000", p)
        self.assertNotIn("Jane Example", p)

    def test_do_not_claim_drops_items_the_background_evidences(self):
        p = self._prompt()
        section = p.split("=== DO NOT CLAIM", 1)[1]
        self.assertIn("- AWS", section)
        self.assertNotIn("SIEMs", section)

    def test_recruiter_name_sets_greeting(self):
        self.app.recruiter_name = "Sam"
        self.db.commit()
        self.assertIn('greeting "Dear Sam"', self._prompt())

    def test_requires_a_cover_letter(self):
        self.app.cover_letter = "  "
        self.db.commit()
        with self.assertRaises(HTTPException) as ctx:
            self._prompt()
        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
