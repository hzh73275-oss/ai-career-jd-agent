import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = ROOT_DIR.parent
DEFAULT_RESUME_PATH = ROOT_DIR / "resume.txt"
PROJECT_CACHE_DIR = PROJECT_DIR / ".cache"
VECTOR_STORE_DIR = ROOT_DIR / "data" / "vector_store"


def configure_local_model_cache() -> None:
  cache_map = {
    "HF_HOME": PROJECT_CACHE_DIR / "huggingface",
    "HUGGINGFACE_HUB_CACHE": PROJECT_CACHE_DIR / "huggingface" / "hub",
    "TRANSFORMERS_CACHE": PROJECT_CACHE_DIR / "huggingface" / "transformers",
    "SENTENCE_TRANSFORMERS_HOME": PROJECT_CACHE_DIR / "sentence-transformers",
    "TORCH_HOME": PROJECT_CACHE_DIR / "torch",
  }
  for key, path in cache_map.items():
    os.environ.setdefault(key, str(path))


configure_local_model_cache()


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
