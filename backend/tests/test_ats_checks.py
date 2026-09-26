import unittest

from app.services.ats.checks import (
    check_content_structure,
    check_document_format,
    find_unsupported_export_characters,
    run_ats_check,
)
from app.services.ats.render import render_ats_view
from app.services.ats.sections import parse, section_present

ISO_DATES_CV = """# Jane Doe

jane@example.com | 021 555 0100

## PROFESSIONAL EXPERIENCE

### Senior Analyst | Acme Ltd | 2022-01 - 2026-08

- Did the work.

### Analyst | Acme Ltd | 2018-01 - 2022-01

- Did other work.
"""

GOOD_CV = """# Alex Example

alex@example.com | 021 555 0100 | Auckland, NZ

## PROFESSIONAL PROFILE

A senior security operations analyst with a track record of incident response.

## KEY SKILLS

- SIEM, EDR, threat hunting

## PROFESSIONAL EXPERIENCE

### Senior Security Operations Analyst | Example Technology Ltd | Jan 2022 - Present

- Led containment and investigation of a major ransomware incident.
- Built a 6-person SOC team from 2 people.

### Security Operations Analyst | Example Technology Ltd | Jan 2018 - Jan 2022

- Triaged phishing and malware alerts.

## CERTIFICATIONS

- GIAC Penetration Tester (GPEN), GIAC/SANS, 2018

## EDUCATION

- Diploma in Information Technology
"""

BAD_CV = """# Alex Example

## Where I've Made an Impact

Led lots of incidents and did a lot of great work across many different environments and \
platforms including SIEM and EDR and cloud and endpoint and network and identity and email \
and a whole lot of other things that go on for a very long sentence without any bullet points \
at all which makes it hard to scan quickly as a recruiter or an ATS system trying to parse it.

### Senior Security Operations Analyst | Example Technology Ltd

Some role with no dates at all.
"""


class SectionParsingTests(unittest.TestCase):
    def test_parses_name_and_contact(self):
        parsed = parse(GOOD_CV)
        self.assertEqual(parsed.name, "Alex Example")
        self.assertTrue(parsed.has_email)
        self.assertTrue(parsed.has_phone)

    def test_recognises_standard_headings(self):
        parsed = parse(GOOD_CV)
        self.assertTrue(section_present(parsed, "professional_summary"))
        self.assertTrue(section_present(parsed, "work_experience"))
        self.assertTrue(section_present(parsed, "skills"))
        self.assertEqual(parsed.unrecognised_headings, [])

    def test_flags_unusual_heading(self):
        parsed = parse(BAD_CV)
        self.assertIn("Where I've Made an Impact", parsed.unrecognised_headings)

    def test_detects_missing_role_dates(self):
        parsed = parse(BAD_CV)
        missing = [r for r in parsed.role_date_ranges if not r[1] or not r[2]]
        self.assertEqual(len(missing), 1)

    def test_detects_present_role_dates(self):
        parsed = parse(GOOD_CV)
        complete = [r for r in parsed.role_date_ranges if r[1] and r[2]]
        self.assertEqual(len(complete), 2)

    def test_recognises_iso_year_month_dates(self):
        # CareerKit's own profile/CV data stores dates as "YYYY-MM" (see
        # models/profile.py WorkExperience.start_date/end_date) - this is the
        # actual format real CVs use, not just "Month YYYY".
        parsed = parse(ISO_DATES_CV)
        complete = [r for r in parsed.role_date_ranges if r[1] and r[2]]
        self.assertEqual(len(complete), 2)
        self.assertEqual(complete[0][1], "2022-01")
        self.assertEqual(complete[0][2], "2026-08")


class ContentStructureChecksTests(unittest.TestCase):
    def test_good_cv_passes_the_core_checks(self):
        checks = {c.id: c for c in check_content_structure(GOOD_CV)}
        self.assertEqual(checks["name"].status, "pass")
        self.assertEqual(checks["email"].status, "pass")
        self.assertEqual(checks["phone"].status, "pass")
        self.assertEqual(checks["professional_summary"].status, "pass")
        self.assertEqual(checks["work_experience"].status, "pass")
        self.assertEqual(checks["missing_dates"].status, "pass")
        self.assertEqual(checks["unusual_headings"].status, "pass")

    def test_bad_cv_fails_missing_dates_and_flags_heading(self):
        checks = {c.id: c for c in check_content_structure(BAD_CV)}
        self.assertEqual(checks["missing_dates"].status, "fail")
        self.assertEqual(checks["unusual_headings"].status, "warn")
        self.assertEqual(checks["email"].status, "fail")

    def test_bad_cv_flags_long_paragraph_and_no_bullets(self):
        checks = {c.id: c for c in check_content_structure(BAD_CV)}
        self.assertEqual(checks["paragraph_length"].status, "warn")
        self.assertEqual(checks["bullet_structure"].status, "warn")

    def test_inconsistent_date_styles_detected(self):
        mixed = GOOD_CV.replace("Jan 2018 - Jan 2022", "2018 - 2022")
        checks = {c.id: c for c in check_content_structure(mixed)}
        self.assertEqual(checks["date_consistency"].status, "warn")

    def test_iso_dates_pass_missing_and_consistency_checks(self):
        checks = {c.id: c for c in check_content_structure(ISO_DATES_CV)}
        self.assertEqual(checks["missing_dates"].status, "pass")
        self.assertEqual(checks["date_consistency"].status, "pass")


class DocumentFormatChecksTests(unittest.TestCase):
    def test_static_checks_always_pass(self):
        # These describe CareerKit's own exporter, not the content, so they
        # never vary with CV text (except the character-safety one).
        checks = {c.id: c for c in check_document_format(GOOD_CV)}
        for check_id in ("single_column", "no_tables", "no_images_graphics", "standard_fonts", "no_text_boxes", "reading_order"):
            self.assertEqual(checks[check_id].status, "pass", check_id)

    def test_unsupported_character_detected(self):
        text_with_emoji = GOOD_CV + "\n🚀 launched a rocket\n"
        problems = find_unsupported_export_characters(text_with_emoji)
        self.assertIn("🚀", problems)

    def test_no_false_positive_on_known_smart_punctuation(self):
        problems = find_unsupported_export_characters("En dash – and em dash — and “quotes” and ‘apostrophe’…")
        self.assertEqual(problems, [])


class ScoringTests(unittest.TestCase):
    def test_good_cv_scores_higher_than_bad_cv(self):
        good = run_ats_check(GOOD_CV)
        bad = run_ats_check(BAD_CV)
        self.assertGreater(good["score"], bad["score"])

    def test_score_bounded(self):
        for cv in (GOOD_CV, BAD_CV, ""):
            result = run_ats_check(cv)
            self.assertGreaterEqual(result["score"], 0)
            self.assertLessEqual(result["score"], 100)

    def test_deterministic(self):
        self.assertEqual(run_ats_check(GOOD_CV), run_ats_check(GOOD_CV))


class RenderAtsViewTests(unittest.TestCase):
    def test_headings_rendered_in_caps(self):
        view = render_ats_view(GOOD_CV)
        self.assertIn("PROFESSIONAL PROFILE", view)
        self.assertIn("PROFESSIONAL EXPERIENCE", view)

    def test_bullets_flattened_to_plain_lines(self):
        view = render_ats_view(GOOD_CV)
        self.assertIn("Led containment and investigation of a major ransomware incident.", view)
        self.assertNotIn("- Led containment", view)

    def test_markdown_emphasis_stripped(self):
        view = render_ats_view("# Name\n\n## SKILLS\n\n- **Bold** and *italic* text\n")
        self.assertIn("Bold and italic text", view)


if __name__ == "__main__":
    unittest.main()
