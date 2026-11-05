"""Layout controls - kept entirely separate from tailoring/content controls.

Two spacing presets, both readable: they change only vertical spacing, never
font size, margins or what is said. Target length is a goal that's measured
and reported on (see fit.py), never enforced by shrinking or cutting content.
"""
from __future__ import annotations

from dataclasses import dataclass, field

TARGET_TWO_PAGE = "two_page"
TARGET_UNRESTRICTED = "unrestricted"
TARGETS = (TARGET_TWO_PAGE, TARGET_UNRESTRICTED)

SPACING_STANDARD = "standard"
SPACING_COMPACT = "compact"
SPACINGS = (SPACING_STANDARD, SPACING_COMPACT)


@dataclass(frozen=True)
class Spacing:
    """All values in millimetres, A4."""
    line: float           # body line height (10.5pt text)
    paragraph_after: float
    bullet_after: float
    section_before: float
    section_after: float  # gap between a section rule and its first content
    role_before: float
    group_before: float   # "#### Certifications" style sub-group labels


# 10.5pt body text on both. Standard ~1.35 line spacing, compact ~1.22 -
# compact is still comfortable to read, it just closes up the gaps.
PRESETS: dict[str, Spacing] = {
    SPACING_STANDARD: Spacing(line=5.0, paragraph_after=1.8, bullet_after=0.9,
                              section_before=4.6, section_after=1.8, role_before=2.6, group_before=1.6),
    SPACING_COMPACT: Spacing(line=4.5, paragraph_after=1.0, bullet_after=0.4,
                             section_before=3.2, section_after=1.4, role_before=1.8, group_before=1.0),
}


def blend(a: Spacing, b: Spacing, t: float) -> Spacing:
    """A spacing t of the way from a to b (0..1) - used to close up a nearly
    empty last page without going past the compact preset."""
    return Spacing(*(x + (y - x) * t for x, y in zip(a.__dict__.values(), b.__dict__.values())))


@dataclass
class LayoutOptions:
    target: str = TARGET_UNRESTRICTED
    spacing: str = SPACING_STANDARD
    # Section headings (as written, case-insensitive) in the order to render.
    # Sections not listed keep their original relative order after these.
    section_order: list[str] = field(default_factory=list)
    hidden_sections: list[str] = field(default_factory=list)

    @property
    def target_pages(self) -> int | None:
        return 2 if self.target == TARGET_TWO_PAGE else None

    @property
    def spacing_values(self) -> Spacing:
        return PRESETS.get(self.spacing, PRESETS[SPACING_STANDARD])

    @classmethod
    def from_params(cls, target: str | None = None, spacing: str | None = None,
                    order: str | None = None, hide: str | None = None,
                    default_target: str = TARGET_UNRESTRICTED) -> "LayoutOptions":
        def _split(v):
            return [s.strip() for s in (v or "").split("||") if s.strip()]
        return cls(
            target=target if target in TARGETS else default_target,
            spacing=spacing if spacing in SPACINGS else SPACING_STANDARD,
            section_order=_split(order),
            hidden_sections=_split(hide),
        )
