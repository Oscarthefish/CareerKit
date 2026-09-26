from pathlib import Path


def extract_text(path: str | Path) -> str:
    with open(str(path), encoding="utf-8", errors="replace") as f:
        return f.read()
