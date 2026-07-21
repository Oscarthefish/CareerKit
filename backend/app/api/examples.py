import json
import tempfile
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models.profile import ExampleCV
from ..parsers.router import extract_text, SUPPORTED_EXTENSIONS
from ..services.prompt_service import fill_prompt
from ..ai.provider_factory import get_provider
from ..storage.file_storage import save_example_cv_files, DATA_DIR

router = APIRouter(prefix="/api/examples", tags=["examples"])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@router.get("")
def list_examples(db: Session = Depends(get_db)):
    rows = db.query(ExampleCV).order_by(ExampleCV.id.desc()).all()
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "original_filename": r.original_filename,
            "tone": r.tone,
            "bullet_style": r.bullet_style,
            "sections": json.loads(r.sections or "[]"),
            "section_order": json.loads(r.section_order or "[]"),
            "strengths": json.loads(r.strengths or "[]"),
            "weaknesses": json.loads(r.weaknesses or "[]"),
            "layout_ideas": json.loads(r.layout_ideas or "[]"),
            "formatting_notes": r.formatting_notes,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/{example_id}")
def get_example(example_id: int, db: Session = Depends(get_db)):
    row = db.query(ExampleCV).filter(ExampleCV.id == example_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "id": row.id,
        "filename": row.filename,
        "original_filename": row.original_filename,
        "tone": row.tone,
        "bullet_style": row.bullet_style,
        "sections": json.loads(row.sections or "[]"),
        "section_order": json.loads(row.section_order or "[]"),
        "strengths": json.loads(row.strengths or "[]"),
        "weaknesses": json.loads(row.weaknesses or "[]"),
        "layout_ideas": json.loads(row.layout_ideas or "[]"),
        "formatting_notes": row.formatting_notes,
        "analysis_path": row.analysis_path,
    }


@router.delete("/{example_id}")
def delete_example(example_id: int, db: Session = Depends(get_db)):
    row = db.query(ExampleCV).filter(ExampleCV.id == example_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.post("/upload")
async def upload_example(file: UploadFile = File(...), db: Session = Depends(get_db)):
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is larger than the 10 MB upload limit")

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        raw_text = extract_text(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    prompt = fill_prompt("example_cv_analysis", CV_TEXT=raw_text[:6000])
    provider = get_provider()
    analysis = await provider.generate_json(prompt)

    safe_name = Path(filename).stem

    # Build analysis markdown
    analysis_md = f"# Example CV Analysis: {filename}\n\n"
    for key, value in analysis.items():
        label = key.replace("_", " ").title()
        if isinstance(value, list):
            analysis_md += f"## {label}\n"
            for item in value:
                analysis_md += f"- {item}\n"
            analysis_md += "\n"
        else:
            analysis_md += f"**{label}:** {value}\n\n"

    analysis_path, structure_path = save_example_cv_files(
        filename, analysis_md, analysis
    )

    row = ExampleCV(
        filename=safe_name,
        original_filename=filename,
        analysis_path=str(analysis_path),
        structure_path=str(structure_path),
        sections=json.dumps(analysis.get("sections", [])),
        section_order=json.dumps(analysis.get("section_order", [])),
        tone=analysis.get("tone", ""),
        bullet_style=analysis.get("bullet_style", ""),
        formatting_notes=analysis.get("formatting_notes", ""),
        strengths=json.dumps(analysis.get("strengths", [])),
        weaknesses=json.dumps(analysis.get("weaknesses", [])),
        layout_ideas=json.dumps(analysis.get("layout_ideas", [])),
        raw_text=raw_text[:10000],
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "id": row.id,
        "filename": row.filename,
        "original_filename": row.original_filename,
        "analysis": analysis,
    }
