import re

import httpx

from src.core.schemas import JobInfo, SearchResult
from src.services.text_utils import clean_text, clip_text, find_keywords, looks_like_url


def fetch_url_text(url: str) -> str:
  headers = {
    "User-Agent": (
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
    )
  }
  response = httpx.get(url, headers=headers, timeout=20, follow_redirects=True)
  response.raise_for_status()
  text = re.sub(r"<script.*?</script>", " ", response.text, flags=re.I | re.S)
  text = re.sub(r"<style.*?</style>", " ", text, flags=re.I | re.S)
  text = re.sub(r"<[^>]+>", " ", text)
  return clean_text(text)


def _extract_list_by_markers(text: str, markers: list[str]) -> list[str]:
  sentences = re.split(r"[。；;\n]", text)
  results = []
  for sentence in sentences:
    sentence = clean_text(sentence)
    if any(marker in sentence for marker in markers) and 8 <= len(sentence) <= 120:
      results.append(sentence)
  return results[:8]


def parse_job_text(title: str, raw_text: str, keywords: list[str], source_url: str = "") -> JobInfo:
  text = clip_text(raw_text, 7000)
  locations = [item for item in ["北京", "上海", "武汉", "深圳", "广州", "杭州", "南京", "成都", "远程"] if item in text]
  salary_hints = re.findall(r"\d+\s*[-~]\s*\d+\s*(?:元/天|/天|K|k|千|万)", text)
  duration_hints = re.findall(r"\d+\s*(?:个月|天/周|周|月)", text)
  responsibilities = _extract_list_by_markers(text, ["负责", "参与", "完成", "建设", "开发", "优化"])
  requirements = _extract_list_by_markers(text, ["要求", "熟悉", "掌握", "具备", "优先", "本科", "硕士"])

  return JobInfo(
    title=title,
    source_url=source_url,
    raw_text=text,
    locations=list(dict.fromkeys(locations)),
    salary_hints=list(dict.fromkeys(salary_hints[:5])),
    duration_hints=list(dict.fromkeys(duration_hints[:5])),
    keywords=find_keywords(text, keywords),
    responsibilities=responsibilities,
    requirements=requirements,
  )


def extract_job_info(input_text: str, keywords: list[str], search_results: list[SearchResult] | None = None) -> JobInfo:
  value = (input_text or "").strip()
  search_results = search_results or []

  if value.isdigit() and search_results:
    index = int(value) - 1
    if index < 0 or index >= len(search_results):
      raise ValueError(f"岗位编号 {value} 不存在。")
    selected = search_results[index]
    raw_text = selected.summary
    if selected.url:
      try:
        page_text = fetch_url_text(selected.url)
        if len(page_text) > len(raw_text):
          raw_text = page_text
      except Exception:
        raw_text = selected.summary
    return parse_job_text(selected.title, raw_text, keywords, selected.url)

  if looks_like_url(value):
    page_text = fetch_url_text(value)
    return parse_job_text(f"公开岗位页面：{value}", page_text, keywords, value)

  return parse_job_text("用户提供的岗位", value, keywords)
