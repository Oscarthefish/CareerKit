from pathlib import Path
from . import pdf_parser, docx_parser, text_parser


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".markdown"}


def extract_text(path: str | Path) -> str:
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".pdf":
        return pdf_parser.extract_text(p)
    elif ext == ".docx":
        return docx_parser.extract_text(p)
    elif ext in {".txt", ".md", ".markdown"}:
        return text_parser.extract_text(p)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
