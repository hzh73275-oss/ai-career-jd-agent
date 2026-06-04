import re
from urllib.parse import urlparse


def clean_text(text: str) -> str:
  return re.sub(r"\s+", " ", text or "").strip()


def clip_text(text: str, limit: int = 2500) -> str:
  text = clean_text(text)
  if len(text) <= limit:
    return text
  return text[:limit] + "...[内容过长，已截断]"


def looks_like_url(value: str) -> bool:
  try:
    parsed = urlparse((value or "").strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
  except Exception:
    return False


def find_keywords(text: str, keywords: list[str]) -> list[str]:
  lowered = (text or "").lower()
  return [keyword for keyword in keywords if keyword.lower() in lowered]
