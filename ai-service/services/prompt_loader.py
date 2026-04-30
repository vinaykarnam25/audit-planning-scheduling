from pathlib import Path

from services.config import settings


def load_prompt_template(filename: str) -> str:
    prompt_path = Path(settings.prompts_path) / filename
    return prompt_path.read_text(encoding="utf-8").strip()
