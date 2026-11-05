"""Entry points the API uses, so every CV view and export goes through the
same preparation and fitting."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from .fit import FitResult, choose_spacing, prepare
from .normalize import normalize_structure, section_names
from .options import LayoutOptions


def credential_records(db: Session) -> tuple[list[dict], list[dict]]:
    """Structured certification/training records, used to restructure CVs
    saved in the older free-text format. "full" mode so a record excluded
    from a narrower CV mode can still be recognised in older text."""
    from ..profile_service import build_profile_summary
    profile = build_profile_summary(db, mode="full")
    return profile.get("certifications", []), profile.get("training", [])


def normalize_for_display(db: Session, md: str | None) -> str | None:
    if not md:
        return md
    certs, training = credential_records(db)
    return normalize_structure(md, certs, training)


def layout(db: Session, md: str, options: LayoutOptions) -> tuple[str, FitResult, list[str]]:
    """(markdown exactly as rendered, fit result, all section names in the
    document before any were hidden - for the ordering/inclusion control)."""
    certs, training = credential_records(db)
    full = normalize_structure(md, certs, training)
    prepared = prepare(full, options, certs, training)
    return prepared, choose_spacing(prepared, options), section_names(full)


def export(db: Session, md: str, fmt: str, path: Path, options: LayoutOptions) -> tuple[Path, FitResult | None]:
    from ...exporters import docx_exporter, markdown_exporter, pdf_exporter
    prepared, fit, _ = layout(db, md, options)
    if fmt == "md":
        return markdown_exporter.export(prepared, path), fit
    if fmt == "docx":
        return docx_exporter.export(prepared, path, spacing=fit.spacing_values), fit
    if fmt == "pdf":
        return pdf_exporter.export(prepared, path, spacing=fit.spacing_values), fit
    raise ValueError(f"Unsupported format: {fmt}")
