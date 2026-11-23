"""Page-break placement, page targets and the Projects section.

Synthetic data only (this repo is public). Guards against the real defects:
a section starting with a few lines at the bottom of a page, a role or a
project split across pages, a fixed two-page target for job CVs when the
profile asks for three, and an empty PROJECTS heading once a profile has
more than two projects.
"""
import tempfile
import unittest
from pathlib import Path

from docx import Document

from app.api.cv import _force_correct_projects
from app.exporters import docx_exporter, pdf_exporter
from app.services.cv_layout import blocks as cvblocks
from app.services.cv_layout.normalize import normalize_structure
from app.services.cv_layout.options import PRESETS, LayoutOptions
from app.services.matching.selection import select_projects

SP = PRESETS["standard"]
HEAD = ["# Alex Example", "alex@example.com | 021 000 0000 | Auckland, New Zealand", "", "## PROFESSIONAL PROFILE"]
FILL = ("- Filler line about investigation and response work across several platforms and teams "
        "with enough words to wrap onto a second line.")


def _role(n: int, bullets: int) -> list[str]:
    return [f"### Analyst Role {n} | Example Company {n} | Jan 2015 - Feb 2016"] + [
        f"- Role {n} bullet {b} covering triage, containment and reporting across several platforms "
        "with enough words to wrap." for b in range(bullets)]


def _render(md: str):
    blocks = cvblocks.parse(md)
    r = pdf_exporter._Renderer(SP)
    r.render(blocks)
    return r, blocks


def _room_after(lines: list[str]) -> float:
    """Fraction of the usable page left on page 1 after these lines."""
    r, _ = _render("\n".join(lines))
    return r._remaining() / r._usable if r.pdf.page_no() == 1 else -1.0


def _filler_for(low: float, high: float, before=(), after=()) -> int:
    """Filler bullet count that leaves between low and high of the page free
    once `before` + filler + `after` are laid out."""
    for n in range(1, 60):
        if low <= _room_after(HEAD + list(before) + [FILL] * n + list(after)) <= high:
            return n
    raise AssertionError("no filler count gives that much room")


def _index(blocks, kind: str, text: str) -> int:
    return next(j for j, b in enumerate(blocks) if b.kind == kind and text in (b.text or " ".join(b.parts or [])))


def _page_of(r, blocks, j: int) -> int:
    """1-based page block j starts on, from the recorded breaks."""
    return 1 + sum(1 for k in r.breaks if k <= j)


class SectionStartTests(unittest.TestCase):
    def test_section_with_little_room_left_starts_on_a_new_page(self):
        # Real regression: PROFESSIONAL EXPERIENCE began with one role and 3
        # bullets at the bottom of page 1.
        filler = _filler_for(0.12, 0.22)
        md = "\n".join(HEAD + [FILL] * filler + ["", "## PROFESSIONAL EXPERIENCE"] + _role(1, 6) + _role(2, 6))
        r, blocks = _render(md)
        self.assertEqual(_page_of(r, blocks, _index(blocks, "section", "PROFESSIONAL EXPERIENCE")), 2)

    def test_section_with_plenty_of_room_starts_on_the_same_page(self):
        filler = _filler_for(0.42, 0.55)
        md = "\n".join(HEAD + [FILL] * filler + ["", "## PROFESSIONAL EXPERIENCE"] + _role(1, 4) + _role(2, 8)
                       + _role(3, 8))
        r, blocks = _render(md)
        self.assertEqual(_page_of(r, blocks, _index(blocks, "section", "PROFESSIONAL EXPERIENCE")), 1)

    def test_short_section_that_fits_stays_put(self):
        filler = _filler_for(0.12, 0.22)
        md = "\n".join(HEAD + [FILL] * filler + ["", "## COMMUNITY INVOLVEMENT", "- Volunteer researcher, 2026."])
        r, blocks = _render(md)
        self.assertEqual(r.breaks, [])


class KeepTogetherTests(unittest.TestCase):
    def test_short_role_moves_whole_instead_of_splitting(self):
        # Real regression: a role's last two bullets were carried overleaf.
        # Room for the role header and its first three bullets, not all five.
        before = ["", "## PROFESSIONAL EXPERIENCE"] + _role(1, 2)
        filler = _filler_for(0.10, 0.13, before=before)
        md = "\n".join(HEAD + before + [FILL] * filler + _role(2, 5))
        r, blocks = _render(md)
        role2 = _index(blocks, "role", "Analyst Role 2")
        self.assertIn(role2, r.breaks)
        first, last = role2 + 1, role2 + 5
        self.assertEqual({_page_of(r, blocks, k) for k in range(role2, last + 1)}, {_page_of(r, blocks, first)})

    def test_project_detail_lines_stay_with_their_project(self):
        # Real regression: a page opened with a project's "Outcomes:" and "URL:" lines.
        # Room for the project line and a detail line or two, not all of it.
        before = ["", "## PROJECTS", "- **First Tool** - A small utility."]
        filler = _filler_for(0.03, 0.05, before=before)
        md = "\n".join(HEAD + before[:2] + [FILL] * filler + [before[2],
                                                 "- **Example Tool** - A local triage tool for analysts.",
                                                 "  Role: Creator", "  Technologies: Python",
                                                 "  Outcomes: Built and published it.", "  URL: https://example.com/tool"])
        r, blocks = _render(md)
        project = _index(blocks, "bullet", "Example Tool")
        pages = {_page_of(r, blocks, k) for k in range(project, project + 5)}
        self.assertEqual(len(pages), 1)


class DocxMirrorsPdfTests(unittest.TestCase):
    def test_docx_breaks_before_the_same_section(self):
        filler = _filler_for(0.12, 0.22)
        md = "\n".join(HEAD + [FILL] * filler + ["", "## PROFESSIONAL EXPERIENCE"] + _role(1, 6) + _role(2, 6))
        with tempfile.TemporaryDirectory() as tmp:
            doc = Document(str(docx_exporter.export(md, Path(tmp) / "cv.docx", spacing=SP)))
        broken = [p.text for p in doc.paragraphs if p.paragraph_format.page_break_before]
        self.assertEqual(broken, ["PROFESSIONAL EXPERIENCE"])


class TargetTests(unittest.TestCase):
    def test_page_targets(self):
        for target, pages in (("one_page", 1), ("two_page", 2), ("three_page", 3), ("unrestricted", None)):
            self.assertEqual(LayoutOptions(target=target).target_pages, pages)

    def test_preferred_follows_the_profile_length(self):
        from app.services.cv_layout import service

        class _Style:
            preferred_cv_length = "3-pages"

        class _Query:
            def first(self):
                return _Style()

        class _Db:
            def query(self, model):
                return _Query()

        resolved = service.resolve_target(_Db(), LayoutOptions.from_params("preferred"))
        self.assertEqual(resolved.target_pages, 3)
        self.assertEqual(LayoutOptions.from_params(None, default_target="preferred").target, "preferred")


class ProjectsTests(unittest.TestCase):
    PROJECTS = [
        {"name": "Card Cloner", "description": "Desktop app for RFID card reading.", "technologies": []},
        {"name": "Mail Triage", "description": "Phishing email investigation and IOC extraction.", "technologies": []},
        {"name": "Recon Tool", "description": "Passive domain reconnaissance.", "technologies": []},
        {"name": "Intel Feed", "description": "Threat intelligence briefing platform.", "technologies": []},
    ]
    COVERAGE = [{"name": "Perform email investigations to identify threats", "coverage": "PARTIAL_EVIDENCE",
                 "importance": "important", "sources": []}]

    def test_uncited_projects_are_backfilled_by_relevance(self):
        # Real regression: with more than two projects and none cited, the
        # CV got an empty PROJECTS heading.
        chosen = [p["name"] for p in select_projects(self.PROJECTS, {}, self.COVERAGE)]
        self.assertEqual(len(chosen), 3)
        self.assertIn("Mail Triage", chosen)
        self.assertIn("Intel Feed", chosen)

    def test_cited_projects_come_first_and_are_all_kept(self):
        scores = {"project: recon tool": 2.0, "project: card cloner": 1.0, "project: intel feed": 1.0}
        chosen = [p["name"] for p in select_projects(self.PROJECTS, scores, self.COVERAGE)]
        self.assertEqual(chosen, ["Card Cloner", "Recon Tool", "Intel Feed"])

    def test_empty_projects_section_is_removed_without_eating_the_next(self):
        md = "## A\nx\n\n## PROJECTS\n\n## CERTIFICATIONS & TRAINING\ny\n"
        self.assertEqual(_force_correct_projects(md, []), "## A\nx\n\n## CERTIFICATIONS & TRAINING\ny\n")

    def test_job_cv_projects_are_compact(self):
        # Three projects in the full labelled format ran to ~30 lines and
        # pushed a 3-page CV onto a fourth page.
        project = {"name": "Mail Triage", "url": "https://github.com/example/mail-triage",
                   "description": "A local email triage tool. It parses headers and extracts IOCs. "
                                  "It also checks SPF, DKIM and DMARC. A fourth sentence that is dropped.",
                   "technologies": ["Python", "YARA", "SPF", "DKIM", "DMARC", "Streamlit"],
                   "role": "Creator", "outcomes": "Built it."}
        out = _force_correct_projects("## PROJECTS\n- x\n\n## NEXT\ny\n", [project], compact=True)
        self.assertEqual(out, "## PROJECTS\n- **Mail Triage** — A local email triage tool. It parses headers and "
                              "extracts IOCs.\n  Python, YARA, SPF, DKIM, DMARC · github.com/example/mail-triage\n"
                              "\n## NEXT\ny\n")
        full = _force_correct_projects("## PROJECTS\n- x\n", [project])
        self.assertIn("  Role: Creator", full)

    def test_layout_drops_any_empty_section(self):
        md = "# A\nx@example.com\n\n## PROFILE\nHi\n\n## PROJECTS\n\n## COMMUNITY INVOLVEMENT\n- T\n"
        self.assertNotIn("PROJECTS", normalize_structure(md))


if __name__ == "__main__":
    unittest.main()
