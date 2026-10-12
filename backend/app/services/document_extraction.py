"""Supports the uploaded-career-document review flow (see
api/profile.py's "Career Documents" section): deterministic duplicate
detection against existing profile data, and mapping a reviewed,
accepted extracted item onto the real model it becomes on commit.

Kept separate from the extraction prompt/AI call - an LLM self-reporting
"this might already exist" is unreliable; a same word-overlap technique
already used elsewhere in this codebase (see api/cv.py's achievement
dedup) is cheap, deterministic and good enough to flag for a human to
decide, which is all this needs to do."""
import json
from sqlalchemy.orm import Session
from ..models.profile import Achievement, Project, Certification, Training

_STOPWORDS = {
    "the", "and", "with", "for", "from", "into", "that", "this", "were",
    "have", "has", "was", "are", "a", "an", "of", "to", "in", "on", "at",
}


def _significant_words(text: str) -> set[str]:
    words = (raw.strip(".,;:()\"'").lower() for raw in (text or "").split())
    return {w for w in words if len(w) > 3 and w not in _STOPWORDS}


def _best_overlap(candidate: str, existing: list[tuple[int, str]]) -> dict | None:
    cw = _significant_words(candidate)
    if not cw:
        return None
    best = None
    for item_id, title in existing:
        tw = _significant_words(title)
        if not tw:
            continue
        overlap = len(cw & tw) / min(len(cw), len(tw))
        if overlap >= 0.6 and (best is None or overlap > best[2]):
            best = (item_id, title, overlap)
    if not best:
        return None
    return {"id": best[0], "title": best[1], "overlap": round(best[2], 2)}


def find_possible_duplicate(db: Session, kind: str, candidate_label: str) -> dict | None:
    """candidate_label is the extracted item's title (achievement/training) or
    name (project/certification). Returns {id, title, overlap} for the
    closest existing match at or above the similarity bar, or None."""
    if not candidate_label:
        return None
    if kind == "achievement":
        existing = [(r.id, r.title) for r in db.query(Achievement.id, Achievement.title).all()]
    elif kind == "project":
        existing = [(r.id, r.name) for r in db.query(Project.id, Project.name).all()]
    elif kind == "certification":
        existing = [(r.id, r.name) for r in db.query(Certification.id, Certification.name).all()]
    elif kind == "training":
        existing = [(r.id, r.title) for r in db.query(Training.id, Training.title).all()]
    else:
        return None
    return _best_overlap(candidate_label, existing)


def find_batch_duplicate(kind: str, candidate_label: str, earlier_items: list[dict]) -> dict | None:
    """Same similarity check as find_possible_duplicate, but against items
    of the same kind already extracted earlier in the SAME upload batch,
    rather than existing profile data - a local model has been observed
    splitting one real achievement into two separate items (e.g. one for
    the work, one for its outcome) within a single extraction, which a
    DB-only check can't catch since neither item is saved yet."""
    if not candidate_label:
        return None
    same_kind = [
        (it["local_id"], it.get("title") or it.get("name"))
        for it in earlier_items
        if it.get("kind") == kind and (it.get("title") or it.get("name"))
    ]
    match = _best_overlap(candidate_label, same_kind)
    if not match:
        return None
    return {"local_id": match["id"], "title": match["title"], "overlap": match["overlap"]}


# Which extracted fields map onto each real model's constructor, and which
# of those fields are JSON array columns needing json.dumps before saving.
_KIND_FIELDS = {
    "achievement": (Achievement, {
        "title", "situation", "action", "result", "tools_involved",
        "measurable_outcome", "employer", "date_range", "ownership", "confidence",
    }),
    "project": (Project, {
        "name", "description", "role", "technologies", "outcomes", "url",
        "date_range", "confidence",
    }),
    "certification": (Certification, {"name", "issuer", "date_obtained", "in_progress"}),
    "training": (Training, {"title", "provider", "date", "completion_status", "confidence"}),
}
_LIST_FIELDS = {"tools_involved", "technologies"}


def commit_item(db: Session, item: dict, original_filename: str) -> int | None:
    """Creates the real profile row for one accepted, reviewed extracted
    item and returns its id - or None if the item's kind isn't recognised.
    Does not commit the session; the caller controls the transaction so
    multiple items can be committed together."""
    kind = item.get("kind")
    mapping = _KIND_FIELDS.get(kind)
    if not mapping:
        return None
    model, fields = mapping

    kwargs = {}
    for field in fields:
        value = item.get(field)
        if value is None or value == "":
            continue
        if field in _LIST_FIELDS and isinstance(value, list):
            value = json.dumps(value)
        elif field == "in_progress" and isinstance(value, str):
            # The extraction model occasionally writes "true"/"false" as a
            # JSON string instead of a real boolean - coerce rather than let
            # a truthy non-empty string silently mark every certification as
            # in progress.
            value = value.strip().lower() in ("true", "1", "yes")
        kwargs[field] = value

    source_note = f"Extracted from uploaded document: {original_filename}"
    if kind == "achievement":
        kwargs["source"] = source_note
    elif kind in ("certification", "training"):
        existing_notes = kwargs.get("notes")
        kwargs["notes"] = f"{existing_notes}\n{source_note}" if existing_notes else source_note

    row = model(**kwargs)
    db.add(row)
    db.flush()
    return row.id
