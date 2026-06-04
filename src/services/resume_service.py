from pathlib import Path

from src.parsers.document_parser import read_document
from src.services.text_utils import clip_text


def load_resume_from_default(path: Path) -> str:
  if not path.exists():
    raise FileNotFoundError(f"未找到默认简历文件：{path}")
  return clip_text(path.read_text(encoding="utf-8", errors="ignore"), 7000)


def load_resume(input_text_or_path: str, default_path: Path) -> str:
  if input_text_or_path and input_text_or_path.strip():
    return clip_text(read_document(input_text_or_path), 7000)
  return load_resume_from_default(default_path)
