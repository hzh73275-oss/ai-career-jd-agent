import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_RESUME_PATH = ROOT_DIR / "resume.txt"


@dataclass(frozen=True)
class Settings:
  openai_api_key: str
  openai_base_url: str | None
  model_name: str
  tavily_api_key: str | None
  default_resume_path: Path


def load_settings() -> Settings:
  load_dotenv(ROOT_DIR / ".env", override=True)
  return Settings(
    openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
    openai_base_url=os.environ.get("OPENAI_BASE_URL") or None,
    model_name=os.environ.get("MODEL_NAME", "gpt-3.5-turbo-1106"),
    tavily_api_key=os.environ.get("TAVILY_API_KEY") or None,
    default_resume_path=DEFAULT_RESUME_PATH,
  )
