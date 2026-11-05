import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine, text

from app.api.applications import _normalize_job_url
from app.core.database import _backfill_job_urls


class NormalizeJobUrlTests(unittest.TestCase):
    def test_full_https_url_is_kept(self):
        url = "https://www.seek.co.nz/job/12345"
        self.assertEqual(_normalize_job_url(url), url)

    def test_bare_domain_gets_https_prepended(self):
        self.assertEqual(_normalize_job_url("seek.co.nz/job/1"), "https://seek.co.nz/job/1")

    def test_blank_and_none_clear_the_link(self):
        self.assertIsNone(_normalize_job_url(""))
        self.assertIsNone(_normalize_job_url("   "))
        self.assertIsNone(_normalize_job_url(None))

    def test_surrounding_whitespace_is_stripped(self):
        self.assertEqual(_normalize_job_url("  https://hays.net.nz/x  "), "https://hays.net.nz/x")

    def test_non_web_schemes_are_rejected(self):
        for bad in ("javascript:alert(1)", "file:///etc/passwd", "ftp://example.com/x"):
            with self.assertRaises(HTTPException, msg=bad):
                _normalize_job_url(bad)


class BackfillJobUrlTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        with self.engine.begin() as conn:
            conn.execute(text("CREATE TABLE job_applications (id INTEGER PRIMARY KEY, company_research TEXT, job_url TEXT)"))
            conn.execute(text("INSERT INTO job_applications VALUES "
                              "(1, 'Job found via Seek\nURL: https://www.seek.co.nz/job/1', NULL),"
                              "(2, 'My own notes, no link', NULL),"
                              "(3, 'Job found via Hays\nURL: https://hays.net.nz/old', 'https://kept.example/'),"
                              "(4, NULL, NULL)"))

    def _urls(self):
        with self.engine.begin() as conn:
            return dict(conn.execute(text("SELECT id, job_url FROM job_applications")).fetchall())

    def test_lifts_scanner_url_line_into_job_url_without_overwriting(self):
        with self.engine.begin() as conn:
            _backfill_job_urls(conn)
        self.assertEqual(self._urls(), {
            1: "https://www.seek.co.nz/job/1",
            2: None,
            3: "https://kept.example/",
            4: None,
        })

    def test_is_idempotent(self):
        for _ in range(2):
            with self.engine.begin() as conn:
                _backfill_job_urls(conn)
        self.assertEqual(self._urls()[1], "https://www.seek.co.nz/job/1")


if __name__ == "__main__":
    unittest.main()
