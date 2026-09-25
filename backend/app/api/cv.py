import json
import re
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models.cv import CVVersion
from ..services.profile_service import build_profile_summary
from ..services.prompt_service import fill_prompt
from ..ai.provider_factory import get_provider
from ..exporters import markdown_exporter, docx_exporter, pdf_exporter
from ..storage.file_storage import get_exports_dir

router = APIRouter(prefix="/api/cv", tags=["cv"])


@router.get("/current")
def get_current_cv(db: Session = Depends(get_db)):
    row = db.query(CVVersion).order_by(CVVersion.id.desc()).first()
    if not row:
        return {"content_markdown": None, "id": None}
    return {
        "id": row.id,
        "version_name": row.version_name,
        "content_markdown": row.content_markdown,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/versions")
def list_cv_versions(db: Session = Depends(get_db)):
    rows = db.query(CVVersion).order_by(CVVersion.id.desc()).all()
    return [
        {
            "id": r.id,
            "version_name": r.version_name,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/versions/{version_id}")
def get_cv_version(version_id: int, db: Session = Depends(get_db)):
    row = db.query(CVVersion).filter(CVVersion.id == version_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "id": row.id,
        "version_name": row.version_name,
        "content_markdown": row.content_markdown,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


class CVSaveRequest(BaseModel):
    content_markdown: str
    version_name: str = "Manual save"


@router.post("/save")
def save_cv(body: CVSaveRequest, db: Session = Depends(get_db)):
    row = CVVersion(
        version_name=body.version_name,
        content_markdown=body.content_markdown,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "version_name": row.version_name}


@router.post("/generate")
async def generate_cv(mode: str = "cv_safe", db: Session = Depends(get_db)):
    from ..models.profile import ExampleCV
    profile = build_profile_summary(db, mode=mode)

    # Gather style insights from uploaded example CVs
    examples = db.query(ExampleCV).all()
    style_guidance = ""
    if examples:
        insights = []
        all_layout_ideas = []
        all_strengths = []
        for ex in examples:
            layout = json.loads(ex.layout_ideas or "[]")
            strengths = json.loads(ex.strengths or "[]")
            all_layout_ideas.extend(layout)
            all_strengths.extend(strengths)
            if ex.formatting_notes:
                insights.append(f"- {ex.original_filename}: {ex.formatting_notes}")
        if all_layout_ideas or all_strengths or insights:
            style_guidance = "\n\nSTYLE GUIDANCE FROM EXAMPLE CVs:\n"
            if all_layout_ideas:
                style_guidance += "Layout ideas worth applying:\n"
                for idea in all_layout_ideas[:6]:
                    style_guidance += f"- {idea}\n"
            if all_strengths:
                style_guidance += "Strengths to emulate:\n"
                for s in all_strengths[:5]:
                    style_guidance += f"- {s}\n"
            if insights:
                style_guidance += "Formatting notes from examples:\n"
                style_guidance += "\n".join(insights[:4])

    from ..services.profile_service import get_banned_phrases_instruction, get_banned_phrases_list
    banned = get_banned_phrases_instruction(db)
    banned_list = get_banned_phrases_list(db)
    prompt = fill_prompt(
        "cv_generation",
        PROFILE_JSON=json.dumps(profile, indent=2),
        STYLE_GUIDANCE=style_guidance,
        BANNED_PHRASES=banned,
    )
    provider = get_provider()
    content = await provider.generate(prompt, banned_phrases=banned_list, flag_years_experience=True)
    # Safety net: the local model occasionally emits a bare "-" bullet for a
    # role with no recorded detail. Strip it in code rather than trusting the
    # model to always follow the "no data, no bullet" instruction.
    content = re.sub(r"\n[ \t]*-[ \t]*\n", "\n", content)

    # Safety net: Platforms & Tools is meant to be copied verbatim from
    # platforms_and_tools_display (built deterministically so it can't
    # fabricate or drop a tool), but a long list occasionally gets truncated,
    # merged into the previous line, or dropped by the model anyway. Force the
    # block to the correct value after the fact rather than trust the copy.
    # Laid out as one category per line (the user's preferred layout) rather
    # than a single packed paragraph.
    tools_lines = profile.get("platforms_and_tools_display", [])
    if tools_lines:
        # The model sometimes also leaks the same tool list into the previous
        # ("Security Operations & Incident Response") line before (or instead
        # of) placing it correctly. Strip that leak using the known category
        # names, since the correct copy is guaranteed to exist below regardless.
        categories = [line.split(":", 1)[0].strip() for line in tools_lines]
        cat_pattern = "|".join(re.escape(c) for c in categories if c)
        if cat_pattern:
            leak_pattern = re.compile(
                rf"(\*\*Security Operations & Incident Response:\*\*.*?),?\s*(?:{cat_pattern}):.*$",
                re.MULTILINE,
            )
            content = leak_pattern.sub(lambda m: m.group(1), content, count=1)

        correct_block = "**Platforms & Tools:**\n" + "\n".join(tools_lines)
        # Matches the "**Platforms & Tools:**" line plus every line straight
        # after it that isn't itself a bold label or a heading — covers both
        # the old single-paragraph layout and this new multi-line one.
        pattern = re.compile(r"^\*\*Platforms & Tools:\*\*.*(?:\n(?!\*\*|##).*)*", re.MULTILINE)
        if pattern.search(content):
            content = pattern.sub(lambda m: correct_block, content, count=1)
        else:
            ops_pattern = re.compile(r"^\*\*Security Operations & Incident Response:\*\*.*$", re.MULTILINE)
            if ops_pattern.search(content):
                content = ops_pattern.sub(lambda m: m.group(0) + "\n" + correct_block, content, count=1)
            else:
                heading_pattern = re.compile(r"^## KEY SKILLS\s*$", re.MULTILINE)
                content = heading_pattern.sub(lambda m: m.group(0) + "\n" + correct_block, content, count=1)

    # Safety net: a project's URL occasionally gets dropped even though it was
    # right there in the data. Append it back onto that project's line if the
    # URL string isn't present anywhere in the output.
    for p in profile.get("projects", []):
        url = p.get("url")
        name = p.get("name")
        if not url or not name or url in content:
            continue
        name_line_pattern = re.compile(
            rf"^(- \**{re.escape(name)}\**.*$)", re.MULTILINE
        )
        if name_line_pattern.search(content):
            content = name_line_pattern.sub(lambda m: m.group(1) + f" URL: {url}", content, count=1)

    row = CVVersion(version_name=f"AI Generated ({mode})", content_markdown=content)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "version_name": row.version_name,
        "content_markdown": content,
    }


@router.post("/review")
async def brutal_review(db: Session = Depends(get_db)):
    latest = db.query(CVVersion).order_by(CVVersion.id.desc()).first()
    if not latest or not latest.content_markdown:
        raise HTTPException(status_code=400, detail="No CV found. Generate your CV first.")
    prompt = fill_prompt("brutal_review", CV_CONTENT=latest.content_markdown)
    provider = get_provider()
    result = await provider.generate_json(prompt)
    return result


@router.get("/export/{fmt}")
def export_cv(fmt: str, db: Session = Depends(get_db)):
    latest = db.query(CVVersion).order_by(CVVersion.id.desc()).first()
    if not latest or not latest.content_markdown:
        raise HTTPException(status_code=400, detail="No CV to export.")

    exports_dir = get_exports_dir()
    content = latest.content_markdown

    if fmt == "md":
        path = markdown_exporter.export(content, exports_dir / "master-cv.md")
        return FileResponse(str(path), filename="master-cv.md", media_type="text/markdown")
    elif fmt == "docx":
        path = docx_exporter.export(content, exports_dir / "master-cv.docx")
        return FileResponse(
            str(path),
            filename="master-cv.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    elif fmt == "pdf":
        path = pdf_exporter.export(content, exports_dir / "master-cv.pdf")
        return FileResponse(str(path), filename="master-cv.pdf", media_type="application/pdf")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {fmt}. Use md, docx, or pdf.")
