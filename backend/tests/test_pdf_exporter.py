import tempfile
import unittest
from pathlib import Path

import pdfplumber

from app.exporters import pdf_exporter

_FIRST_ACH_MARKER = "FIRSTACHIEVEMENTMARKER"

_FILLER_BULLET = (
    "- A filler bullet of moderate length used only to push the layout toward a page "
    "boundary for testing purposes."
)

_ACHIEVEMENT_BULLET = (
    f"- {_FIRST_ACH_MARKER} Owned Security Operations workstreams during a global ransomware "
    "response. Contributed hands-on investigation and containment work through a high-pressure, "
    "multi-week response at real enterprise scale, working across the global environment rather "
    "than solely on local systems."
)


def _build_cv(filler_bullets: int) -> str:
    """A synthetic CV (no real user data - this repo is public) shaped to land
    "## SELECTED ACHIEVEMENTS" exactly at a page boundary once filler_bullets
    is tuned right, reproducing the real reported bug: a long achievement
    bullet wraps to several lines, so a heading that just barely fit under a
    flat reserve got drawn with its first bullet pushed to the next page."""
    lines = [
        "# Alex Example",
        "alex@example.com | 021 000 0000 | Auckland, New Zealand",
        "",
        "## PROFESSIONAL EXPERIENCE",
        "",
        "### Senior Analyst | Example Company | Jan 2020 - Present",
        "",
    ]
    lines.extend([_FILLER_BULLET] * filler_bullets)
    lines.append("")
    lines.append("## SELECTED ACHIEVEMENTS")
    lines.append(_ACHIEVEMENT_BULLET)
    lines.append("- Another achievement bullet with a real outcome attached to it too.")
    lines.append("")
    lines.append("## CERTIFICATIONS & TRAINING")
    lines.append("Some Certification, Some Issuer, 2020")
    lines.append("")
    lines.append("## COMMUNITY INVOLVEMENT")
    lines.append("- A single short community involvement line about volunteering.")
    return "\n".join(lines)


def _pages_of(content: str) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        path = pdf_exporter.export(content, Path(tmp) / "test.pdf")
        with pdfplumber.open(path) as pdf:
            return [(page.extract_text() or "") for page in pdf.pages]


class SectionHeadingNeverOrphanedTests(unittest.TestCase):
    def test_real_regression_heading_lands_with_its_first_bullet_not_alone(self):
        # filler_bullets=35 is the exact calibrated point where the OLD flat
        # 20mm reserve let "## SELECTED ACHIEVEMENTS" fit at the bottom of a
        # page while its first (long, wrapping) bullet got pushed to the
        # next page entirely - reproducing the real reported bug verbatim.
        pages = _pages_of(_build_cv(35))
        heading_page_idx = next(i for i, t in enumerate(pages) if "SELECTED ACHIEVEMENTS" in t)
        self.assertIn(
            _FIRST_ACH_MARKER, pages[heading_page_idx],
            "SELECTED ACHIEVEMENTS heading landed without its first bullet on the same page - orphaned heading.",
        )

    def test_heading_never_orphaned_across_a_range_of_nearby_boundary_positions(self):
        # A few filler counts either side of the exact calibrated boundary,
        # so this doesn't only guard the one exact number above.
        for filler_bullets in range(30, 42):
            with self.subTest(filler_bullets=filler_bullets):
                pages = _pages_of(_build_cv(filler_bullets))
                heading_page_idx = next(i for i, t in enumerate(pages) if "SELECTED ACHIEVEMENTS" in t)
                self.assertIn(_FIRST_ACH_MARKER, pages[heading_page_idx])

    def test_a_single_short_trailing_section_does_not_get_its_own_lonely_page(self):
        # The real complaint: Community Involvement (two short lines)
        # spilling alone onto a 4th page while Certifications & Training
        # fit comfortably on page 3.
        pages = _pages_of(_build_cv(35))
        last_page = pages[-1]
        if "COMMUNITY INVOLVEMENT" in last_page:
            self.assertIn("CERTIFICATIONS", last_page)


if __name__ == "__main__":
    unittest.main()
