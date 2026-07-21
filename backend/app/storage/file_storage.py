import json
from pathlib import Path
from datetime import datetime
from ..core.config import DATA_DIR


def get_application_folder(company: str, role: str) -> Path:
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_company = "".join(c if c.isalnum() or c in "-_" else "_" for c in (company or "unknown"))
    safe_role = "".join(c if c.isalnum() or c in "-_" else "_" for c in (role or "role"))
    folder_name = f"{date_str}_{safe_company[:30]}_{safe_role[:30]}"
    applications_dir = DATA_DIR / "applications"
    folder = applications_dir / folder_name
    suffix = 2
    while folder.exists():
        folder = applications_dir / f"{folder_name}_{suffix}"
        suffix += 1
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "exports").mkdir(exist_ok=True)
    return folder


def save_application_file(folder: Path, filename: str, content: str) -> Path:
    path = folder / filename
    path.write_text(content, encoding="utf-8")
    return path


def save_application_json(folder: Path, filename: str, data: dict) -> Path:
    path = folder / filename
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def save_example_cv_files(filename: str, analysis_md: str, structure: dict) -> tuple[Path, Path]:
    folder = DATA_DIR / "examples" / Path(filename).stem
    folder.mkdir(parents=True, exist_ok=True)
    analysis_path = folder / "analysis.md"
    structure_path = folder / "structure.json"
    analysis_path.write_text(analysis_md, encoding="utf-8")
    structure_path.write_text(json.dumps(structure, indent=2, ensure_ascii=False), encoding="utf-8")
    return analysis_path, structure_path


def get_exports_dir() -> Path:
    p = DATA_DIR / "exports"
    p.mkdir(parents=True, exist_ok=True)
    return p
