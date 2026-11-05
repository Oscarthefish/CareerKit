"""Regression coverage for CV structure, layout and pagination.

Synthetic data only (this repo is public). Each test names the real defect it
guards against: concatenated Certifications & Training, justified text,
orphaned headings, a final page holding only Community Involvement, footer
collisions, and long titles colliding with dates.
"""
import tempfile
import unittest
from pathlib import Path

import pdfplumber
from docx import Document

from app.exporters import docx_exporter, pdf_exporter
from app.services.cv_layout import credentials
from app.services.cv_layout.fit import choose_spacing, prepare
from app.services.cv_layout.normalize import (
    apply_section_options, normalize_structure, replace_credentials_section, section_names,
)
from app.services.cv_layout.options import PRESETS, LayoutOptions

CERTS = [
    {"name": "Example Penetration Tester (EPT)", "issuer": "Example Body", "date_obtained": "2018",
     "in_progress": False, "status": "active"},
    {"name": "Old Firewall Engineer (OFE)", "issuer": "Vendor Co", "date_obtained": "2012",
     "in_progress": False, "status": "expired"},
    {"name": "Big Security Credential (BSC)", "issuer": "Cert Org", "date_obtained": None,
     "in_progress": True, "status": "active"},
]
TRAINING = [
    {"title": "SEC504: Incident Handling Course", "provider": "SANS", "date": None, "completion_status": "completed"},
    {"title": "SC-200: Security Operations Analyst", "provider": "Microsoft Learn", "date": None,
     "completion_status": "in_progress"},
    {"title": "Platform Basics", "provider": "Splunk", "date": "2021", "completion_status": "completed"},
    {"title": "Bought But Not Started", "provider": "X", "date": None, "completion_status": "purchased_not_started"},
]


def _pdf_pages(md: str, spacing=None):
    with tempfile.TemporaryDirectory() as tmp:
        path = pdf_exporter.export(md, Path(tmp) / "cv.pdf", spacing=spacing or PRESETS["standard"])
        with pdfplumber.open(path) as pdf:
            return [(page.extract_text() or "", page.extract_words(), float(page.height)) for page in pdf.pages]


def _cv(roles: int, bullets_per_role: int = 4, community=True, long_title=False, extra: int = 0) -> str:
    lines = ["# Alex Example", "alex@example.com | 021 000 0000 | Auckland, New Zealand", "",
             "## PROFESSIONAL PROFILE",
             "Security operations analyst with broad experience across investigation, response and "
             "improvement work in enterprise environments, working with distributed teams.", "",
             "## PROFESSIONAL EXPERIENCE"]
    for r in range(roles):
        title = ("Principal Security Operations and Incident Response Analyst, Detection Engineering "
                 "and Threat Intelligence Programme Lead") if long_title and r == 0 else f"Analyst Role {r}"
        lines.append(f"### {title} | Example Company {r} | 2015-01 - 2016-0{(r % 9) + 1}")
        lines += [f"- Bullet {r}.{b} describing investigation and response work across several platforms "
                  "with enough words to wrap onto a second line in the layout." for b in range(bullets_per_role)]
    lines += [f"- Short filler bullet {k}." for k in range(extra)]
    lines += ["", "## CERTIFICATIONS & TRAINING",
              "Example Penetration Tester (EPT), Example Body, 2018 | Big Security Credential (BSC), Cert Org (In Progress)",
              "Relevant training: SEC504: Incident Handling Course, SANS; Platform Basics, Splunk, 2021"]
    if community:
        lines += ["", "## COMMUNITY INVOLVEMENT", "- COMMUNITYMARKER Volunteer researcher at an example event, 2026"]
    return "\n".join(lines) + "\n"


class CredentialEntryTests(unittest.TestCase):
    def test_groups_are_separate_and_honest(self):
        groups = credentials.group_entries(CERTS, TRAINING)
        self.assertEqual(groups["Certifications"], [
            "Example Penetration Tester (EPT) — Example Body | 2018",
            "Old Firewall Engineer (OFE) — Vendor Co | 2012 | Expired",
        ])
        self.assertEqual(groups["Professional Training"], [
            "SANS SEC504 — Incident Handling Course",
            "Platform Basics — Splunk | 2021",
        ])
        self.assertEqual(groups["Currently Studying"], [
            "Big Security Credential (BSC) — Cert Org | In progress",
            "SC-200: Security Operations Analyst — Microsoft Learn | In progress",
        ])

    def test_never_claims_a_certification_is_active_or_current(self):
        body = credentials.build_section(CERTS, TRAINING)
        self.assertNotRegex(body.lower(), r"\bactive\b|\bcurrent\b|\bvalid\b")

    def test_unstarted_training_is_not_listed(self):
        self.assertNotIn("Bought But Not Started", credentials.build_section(CERTS, TRAINING))

    def test_training_never_appears_under_certifications(self):
        body = credentials.build_section(CERTS, TRAINING)
        cert_block = body.split("#### Professional Training")[0]
        self.assertNotIn("SEC504", cert_block)
        self.assertNotIn("Platform Basics", cert_block)

    def test_one_entry_per_line(self):
        body = credentials.build_section(CERTS, TRAINING)
        self.assertNotIn(" | Example", body)  # no pipe-joined concatenation of entries
        self.assertNotIn("Relevant training:", body)
        self.assertEqual(body.count("\n- "), 6)


class LegacyConversionTests(unittest.TestCase):
    CUSTOM = ("## CERTIFICATIONS & TRAINING\n"
              "Example Penetration Tester (EPT), Example Body, 2018 | Hand Typed Cert, Somewhere, 2010 | "
              "Big Security Credential (BSC), Cert Org (In Progress)\n"
              "Relevant training: SEC504: Incident Handling Course, SANS; Unknown Course, Provider; "
              "SC-200: Security Operations Analyst, Microsoft Learn (In Progress)\n")

    def test_pipe_and_semicolon_paragraphs_become_grouped_entries_without_loss(self):
        out = normalize_structure("# A\n\n" + self.CUSTOM, CERTS, TRAINING)
        for expected in ("#### Certifications", "#### Professional Training", "#### Currently Studying",
                         "- Example Penetration Tester (EPT) — Example Body | 2018",
                         "- Hand Typed Cert, Somewhere, 2010",            # unknown: kept verbatim
                         "- SANS SEC504 — Incident Handling Course",
                         "- Unknown Course, Provider",                    # unknown: kept verbatim
                         "- Big Security Credential (BSC) — Cert Org | In progress",
                         "- SC-200: Security Operations Analyst — Microsoft Learn | In progress"):
            self.assertIn(expected, out)

    def test_master_cv_separate_sections_are_merged_in_place(self):
        md = ("# A\n\n## PROJECTS\n- p\n\n## CERTIFICATIONS\n- Example Penetration Tester (EPT), Example Body, 2018\n\n"
              "## PROFESSIONAL TRAINING\n- Platform Basics, Splunk, 2021\n\n## EDUCATION\n- e\n")
        out = normalize_structure(md, CERTS, TRAINING)
        self.assertEqual(section_names(out), ["PROJECTS", "CERTIFICATIONS & TRAINING", "EDUCATION"])
        self.assertIn("- Platform Basics — Splunk | 2021", out)

    def test_idempotent(self):
        once = normalize_structure("# A\n\n" + self.CUSTOM, CERTS, TRAINING)
        self.assertEqual(normalize_structure(once, CERTS, TRAINING), once)

    def test_role_iso_dates_are_written_out(self):
        out = normalize_structure("# A\n\n## EXPERIENCE\n### Analyst | Co | 2022-01 - 2026-08\n- x\n")
        self.assertIn("### Analyst | Co | Jan 2022 – Aug 2026", out)

    def test_generation_safety_net_replaces_wrong_text_in_place(self):
        md = "# A\n\n## PROJECTS\n- p\n\n## CERTIFICATIONS & TRAINING\nGarbled (PJR)\n\n## COMMUNITY INVOLVEMENT\n- c\n"
        out = replace_credentials_section(md, CERTS, TRAINING)
        self.assertNotIn("Garbled", out)
        self.assertEqual(section_names(out), ["PROJECTS", "CERTIFICATIONS & TRAINING", "COMMUNITY INVOLVEMENT"])


class SectionOptionTests(unittest.TestCase):
    MD = "# A\n\n## ONE\n- 1\n\n## TWO\n- 2\n\n## THREE\n- 3\n"

    def test_reorders_and_hides_without_touching_content(self):
        out = apply_section_options(self.MD, ["THREE", "ONE"], ["TWO"])
        self.assertEqual(section_names(out), ["THREE", "ONE"])
        self.assertIn("- 3", out)

    def test_no_options_is_a_no_op(self):
        self.assertEqual(apply_section_options(self.MD, [], []), self.MD)


class PdfTypographyTests(unittest.TestCase):
    def test_body_text_is_left_aligned_not_justified(self):
        # Justified text stretches the gaps between words on every line but
        # the last; left-aligned text keeps them a uniform single space.
        para = " ".join(["investigation"] * 6 + ["of", "a", "b", "suspicious", "login", "pattern"] * 8)
        _, words, _ = _pdf_pages(f"# A\nme@example.com\n\n## PROFILE\n{para}\n")[0]
        lines = {}
        for w in words:
            if w["top"] > 60:
                lines.setdefault(round(w["top"]), []).append(w)
        gaps = []
        for ws in list(lines.values())[:-1]:  # every full line
            ws.sort(key=lambda w: w["x0"])
            gaps += [b["x0"] - a["x1"] for a, b in zip(ws, ws[1:])]
        self.assertTrue(gaps)
        self.assertLess(max(gaps) - min(gaps), 0.5, "word gaps vary - text is being justified")

    def test_long_role_title_wraps_without_colliding_with_dates(self):
        pages = _pdf_pages(normalize_structure(_cv(1, long_title=True)))
        words = pages[0][1]
        date = next(w for w in words if w["text"] == "2015")
        title_words = [w for w in words if abs(w["top"] - date["top"]) < 2 and w["x1"] < date["x0"]]
        self.assertTrue(title_words)
        for w in words:
            if w is date or abs(w["top"] - date["top"]) >= 2:
                continue
            self.assertFalse(w["x0"] < date["x1"] and w["x1"] > date["x0"] and w["text"] not in ("Jan", "–", "Sep", "2015", "2016"),
                             f"'{w['text']}' overlaps the date")
        self.assertIn("Programme Lead", " ".join(p[0] for p in pages))

    def test_text_extracts_in_reading_order(self):
        text = "\n".join(p[0] for p in _pdf_pages(_cv(2)))
        order = [text.index(s) for s in ("Alex Example", "PROFESSIONAL PROFILE", "Analyst Role 0", "Bullet 0.0",
                                          "Analyst Role 1", "CERTIFICATIONS & TRAINING", "COMMUNITYMARKER")]
        self.assertEqual(order, sorted(order))

    def test_unicode_dashes_survive_export(self):
        text = _pdf_pages("# A\nme@example.com\n\n## X\n- Name — Issuer | 2018 – 2020\n")[0][0]
        self.assertIn("Name — Issuer | 2018 – 2020", text)


class PaginationTests(unittest.TestCase):
    """Sweep content length across page boundaries so these hold for every
    break position, not one calibrated layout."""

    def _body_lines(self, page_words, height):
        rows = {}
        for w in page_words:
            if w["bottom"] < height - 20:  # exclude the footer
                rows.setdefault(round(w["top"]), []).append(w["text"])
        return [" ".join(v) for _, v in sorted(rows.items())]

    def test_no_heading_or_role_is_left_alone_at_the_bottom_of_a_page(self):
        for roles in range(5, 14):
            for bullets in (2, 3):
                with self.subTest(roles=roles, bullets=bullets):
                    pages = _pdf_pages(_cv(roles, bullets))
                    for text, words, h in pages[:-1]:
                        last = self._body_lines(words, h)[-1]
                        self.assertFalse(last.startswith("Analyst Role"), f"orphaned role heading: {last}")
                        self.assertNotIn(last, ("PROFESSIONAL EXPERIENCE", "CERTIFICATIONS & TRAINING",
                                                "COMMUNITY INVOLVEMENT", "Certifications",
                                                "Professional Training", "Currently Studying"))

    def test_footer_never_collides_with_body_text(self):
        for roles in (6, 9, 12):
            for _, words, h in _pdf_pages(_cv(roles)):
                footer_top = min(w["top"] for w in words if w["text"] == "Page")
                body_bottom = max(w["bottom"] for w in words if w["top"] < footer_top - 1)
                self.assertGreater(footer_top - body_bottom, 3, "body text runs into the page number")

    def test_lone_community_entry_page_is_pulled_back_when_spacing_allows(self):
        """The original report: a 4th page holding only Community Involvement."""
        seen_sparse = False
        for extra in range(0, 60):
            md = _cv(7, 3, extra=extra)
            standard = _pdf_pages(md)
            last_text = standard[-1][0]
            if len(standard) > 1 and "COMMUNITYMARKER" in last_text and "filler" not in last_text \
                    and "CERTIFICATIONS" not in last_text:
                seen_sparse = True
                fit = choose_spacing(md, LayoutOptions())
                compact_pages = len(_pdf_pages(md, PRESETS["compact"]))
                if compact_pages < len(standard):
                    self.assertTrue(fit.tightened, f"extra={extra}")
                    self.assertLess(fit.pages, len(standard), f"extra={extra}")
        self.assertTrue(seen_sparse, "sweep never produced the sparse-last-page case it is meant to test")


class FitTests(unittest.TestCase):
    def test_overflow_reports_and_suggests_but_never_edits(self):
        md = prepare(_cv(14, 4), LayoutOptions(target="two_page"), CERTS, TRAINING)
        fit = choose_spacing(md, LayoutOptions(target="two_page"))
        self.assertFalse(fit.fits)
        self.assertGreater(fit.pages, 2)
        self.assertIn("Nothing has been shrunk or removed", fit.notice)
        self.assertEqual(prepare(md, LayoutOptions(), CERTS, TRAINING), md)  # stable, content untouched

    def test_fits_within_target_has_no_notice(self):
        fit = choose_spacing(_cv(2, 2), LayoutOptions(target="two_page"))
        self.assertTrue(fit.fits)
        self.assertIsNone(fit.notice)

    def test_spacing_presets_never_change_font_size(self):
        self.assertEqual(pdf_exporter.BODY_PT, 10.5)
        self.assertLess(PRESETS["compact"].line, PRESETS["standard"].line)
        self.assertGreaterEqual(PRESETS["compact"].line / (10.5 * 25.4 / 72), 1.2)  # still >= 1.2 line spacing


class DocxStructureTests(unittest.TestCase):
    def test_single_column_left_aligned_with_keep_with_next(self):
        md = normalize_structure(_cv(3), CERTS, TRAINING)
        with tempfile.TemporaryDirectory() as tmp:
            path = docx_exporter.export(md, Path(tmp) / "cv.docx")
            doc = Document(str(path))
        self.assertEqual(len(doc.tables), 0)
        self.assertEqual(len(doc.inline_shapes), 0)
        self.assertFalse([p for p in doc.paragraphs if not p.text.strip()], "empty spacer paragraphs")
        body = [p for p in doc.paragraphs if p.text not in ("Alex Example",) and "@" not in p.text]
        self.assertTrue(all(str(p.paragraph_format.alignment).startswith("LEFT") for p in body))
        by_text = {p.text: p for p in doc.paragraphs}
        self.assertTrue(by_text["CERTIFICATIONS & TRAINING"].paragraph_format.keep_with_next)
        self.assertTrue(by_text["Certifications"].paragraph_format.keep_with_next)
        role = next(p for p in doc.paragraphs if p.text.startswith("Analyst Role 0"))
        self.assertTrue(role.paragraph_format.keep_with_next)
        self.assertIn("\tJan 2015 – Jan 2016", role.text)


if __name__ == "__main__":
    unittest.main()
