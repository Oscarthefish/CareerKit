from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {name}")
    return path.read_text(encoding="utf-8")


def fill_prompt(name: str, **kwargs) -> str:
    template = load_prompt(name)
    for key, value in kwargs.items():
        template = template.replace(f"{{{{{key}}}}}", str(value) if value is not None else "")
    return template
