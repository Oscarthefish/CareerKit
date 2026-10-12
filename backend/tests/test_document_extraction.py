import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.profile import Achievement, Project, Certification, Training
from app.services.document_extraction import find_possible_duplicate, find_batch_duplicate, commit_item


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


class FindPossibleDuplicateTests(unittest.TestCase):
    def test_finds_a_close_paraphrase(self):
        db = _make_session()
        db.add(Achievement(title="Helped build a global 24/7 SOC across three locations"))
        db.commit()
        result = find_possible_duplicate(
            db, "achievement",
            "Contributed to building a global 24/7 SOC across three locations"
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Helped build a global 24/7 SOC across three locations")

    def test_no_match_for_an_unrelated_title(self):
        db = _make_session()
        db.add(Achievement(title="Helped build a global 24/7 SOC across three locations"))
        db.commit()
        result = find_possible_duplicate(db, "achievement", "Migrated a legacy billing system to AWS")
        self.assertIsNone(result)

    def test_unrecognised_kind_returns_none(self):
        db = _make_session()
        self.assertIsNone(find_possible_duplicate(db, "not_a_real_kind", "Something"))

    def test_empty_candidate_label_returns_none(self):
        db = _make_session()
        db.add(Achievement(title="Something"))
        db.commit()
        self.assertIsNone(find_possible_duplicate(db, "achievement", ""))


class FindBatchDuplicateTests(unittest.TestCase):
    def test_catches_a_model_splitting_one_achievement_into_two_items(self):
        # Real-world case: the extraction model wrote the same underlying
        # achievement as two separate items in one batch (one for the work,
        # one for its measurable outcome) - neither is saved yet, so the
        # DB-backed check alone can't catch this.
        earlier = [{"local_id": 0, "kind": "achievement", "title": "Honeypot Deception Project"}]
        result = find_batch_duplicate("achievement", "Honeypot Deception Project", earlier)
        self.assertIsNotNone(result)
        self.assertEqual(result["local_id"], 0)

    def test_does_not_match_a_different_kind_with_the_same_title(self):
        earlier = [{"local_id": 0, "kind": "project", "name": "Honeypot Deception Project"}]
        result = find_batch_duplicate("achievement", "Honeypot Deception Project", earlier)
        self.assertIsNone(result)

    def test_no_earlier_items_returns_none(self):
        self.assertIsNone(find_batch_duplicate("achievement", "Anything", []))


class CommitItemTests(unittest.TestCase):
    def test_commits_an_achievement_with_source_note_and_list_fields(self):
        db = _make_session()
        item = {
            "kind": "achievement",
            "title": "Reduced false positives",
            "action": "Tuned detection rules",
            "tools_involved": ["Splunk", "Cortex XDR"],
            "ownership": "significant_contributor",
            "confidence": "working_knowledge",
        }
        new_id = commit_item(db, item, "career-timeline.pdf")
        db.commit()
        row = db.query(Achievement).filter(Achievement.id == new_id).first()
        self.assertIsNotNone(row)
        self.assertEqual(row.title, "Reduced false positives")
        self.assertEqual(json.loads(row.tools_involved), ["Splunk", "Cortex XDR"])
        self.assertEqual(row.ownership, "significant_contributor")
        self.assertIn("career-timeline.pdf", row.source)

    def test_commits_a_project(self):
        db = _make_session()
        item = {
            "kind": "project",
            "name": "SOC Analyst Toolbox",
            "technologies": ["Python", "Flask"],
        }
        new_id = commit_item(db, item, "timeline.docx")
        db.commit()
        row = db.query(Project).filter(Project.id == new_id).first()
        self.assertEqual(row.name, "SOC Analyst Toolbox")
        self.assertEqual(json.loads(row.technologies), ["Python", "Flask"])

    def test_commits_a_certification_with_notes_traceability(self):
        db = _make_session()
        item = {"kind": "certification", "name": "GPEN", "issuer": "GIAC", "in_progress": False}
        new_id = commit_item(db, item, "timeline.pdf")
        db.commit()
        row = db.query(Certification).filter(Certification.id == new_id).first()
        self.assertEqual(row.name, "GPEN")
        self.assertIn("timeline.pdf", row.notes)

    def test_commits_training(self):
        db = _make_session()
        item = {"kind": "training", "title": "SEC504", "provider": "SANS", "completion_status": "completed"}
        new_id = commit_item(db, item, "timeline.pdf")
        db.commit()
        row = db.query(Training).filter(Training.id == new_id).first()
        self.assertEqual(row.title, "SEC504")
        self.assertEqual(row.completion_status, "completed")

    def test_unrecognised_kind_returns_none_and_commits_nothing(self):
        db = _make_session()
        self.assertIsNone(commit_item(db, {"kind": "not_a_real_kind"}, "x.pdf"))

    def test_coerces_a_string_in_progress_value_to_a_real_boolean(self):
        # The extraction model sometimes writes "false"/"true" as a JSON
        # string rather than a real boolean - a plain non-empty string like
        # "false" is truthy in Python, so without coercion this would mark
        # every certification as in progress regardless of the real value.
        db = _make_session()
        new_id = commit_item(db, {"kind": "certification", "name": "GPEN", "in_progress": "false"}, "x.pdf")
        db.commit()
        row = db.query(Certification).filter(Certification.id == new_id).first()
        self.assertIs(row.in_progress, False)

        new_id2 = commit_item(db, {"kind": "certification", "name": "OSCP", "in_progress": "true"}, "x.pdf")
        db.commit()
        row2 = db.query(Certification).filter(Certification.id == new_id2).first()
        self.assertIs(row2.in_progress, True)


if __name__ == "__main__":
    unittest.main()
