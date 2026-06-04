from __future__ import annotations

import base64
import json
import sys
import tempfile
from dataclasses import asdict, is_dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import load_settings
from src.services.formatters import (
  comparison_to_rows,
  format_comparison,
  format_full_report,
  format_job_info,
  format_match_report,
  format_resume_advice,
  format_resume_translation,
)
from src.services.job_search import build_platform_notices, build_source_stats
from src.workflows.resume_jd_workflow import ResumeJDWorkflow


workflow = ResumeJDWorkflow(settings=load_settings(), profile_name="ai_intern")


def to_jsonable(value: Any) -> Any:
  if is_dataclass(value):
    return asdict(value)
  if isinstance(value, Path):
    return str(value)
  if isinstance(value, list):
    return [to_jsonable(item) for item in value]
  if isinstance(value, dict):
    return {key: to_jsonable(item) for key, item in value.items()}
  return value


def ok(data: dict[str, Any] | None = None) -> dict[str, Any]:
  return {"ok": True, **(data or {})}


def fail(message: str) -> dict[str, Any]:
  return {"ok": False, "message": message}


def save_upload(filename: str, content_base64: str) -> str:
  suffix = Path(filename or "resume.txt").suffix or ".txt"
  upload_dir = Path(tempfile.gettempdir()) / "resume_jd_match_uploads"
  upload_dir.mkdir(parents=True, exist_ok=True)
  target = upload_dir / f"resume_upload{suffix}"
  target.write_bytes(base64.b64decode(content_base64))
  return str(target)


def load_resume(payload: dict[str, Any]) -> dict[str, Any]:
  text = (payload.get("text") or "").strip()
  filename = payload.get("filename") or ""
  content_base64 = payload.get("content_base64") or ""

  if content_base64:
    path = save_upload(filename, content_base64)
    resume_text = workflow.load_resume(path)
  elif text:
    resume_text = workflow.load_resume(text)
  else:
    resume_text = workflow.load_resume()

  return ok({
    "resume_text": resume_text,
    "summary": resume_text[:900],
    "length": len(resume_text),
  })


def search_jobs(payload: dict[str, Any]) -> dict[str, Any]:
  query = (payload.get("query") or "").strip()
  if not query:
    return fail("请先输入岗位关键词。")
  max_results = int(payload.get("max_results") or 30)
  max_results = max(5, min(max_results, 100))
  source_keys = payload.get("source_keys") or None
  mode = payload.get("mode") or "fast"
  if mode in ["快速搜索", "quick"]:
    mode = "fast"
  if mode in ["深度搜索", "deep"]:
    mode = "deep"

  results = workflow.search_jobs(
    query=query,
    max_results=max_results,
    source_keys=source_keys,
    mode=mode,
  )
  return ok({
    "results": to_jsonable(results),
    "count": len(results),
    "source_stats": build_source_stats(results),
    "platform_notices": build_platform_notices(results, source_keys or []),
    "strategy": "平台分桶搜索" if mode == "fast" else "平台扩展搜索",
  })


def extract_job(payload: dict[str, Any]) -> dict[str, Any]:
  input_text = (payload.get("input_text") or "").strip()
  if not input_text:
    return fail("请先选择岗位或粘贴 JD。")
  job = workflow.extract_job(input_text)
  return ok({
    "job": to_jsonable(job),
    "job_text": format_job_info(job),
  })


def build_match(_: dict[str, Any]) -> dict[str, Any]:
  report = workflow.match()
  advice = workflow.advise()
  comparison = workflow.compare()
  translation = workflow.translate_resume(polish=False)
  report_text = format_match_report(report)
  advice_text = format_resume_advice(advice)
  comparison_text = format_comparison(comparison)
  translation_text = format_resume_translation(translation)

  return ok({
    "report": to_jsonable(report),
    "advice": to_jsonable(advice),
    "comparison": to_jsonable(comparison),
    "translation": to_jsonable(translation),
    "comparison_rows": comparison_to_rows(comparison),
    "report_text": report_text,
    "advice_text": advice_text,
    "comparison_text": comparison_text,
    "translation_text": translation_text,
    "full_report": format_full_report(
      report_text,
      comparison_text,
      translation_text,
      advice_text,
    ),
  })


def polish_resume(payload: dict[str, Any]) -> dict[str, Any]:
  use_llm = bool(payload.get("use_llm"))
  translation = workflow.translate_resume(polish=use_llm)
  return ok({
    "translation": to_jsonable(translation),
    "translation_text": format_resume_translation(translation),
  })


class Handler(BaseHTTPRequestHandler):
  def log_message(self, format: str, *args: Any) -> None:
    return

  def _send(self, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(to_jsonable(payload), ensure_ascii=False).encode("utf-8")
    self.send_response(status)
    self.send_header("Content-Type", "application/json; charset=utf-8")
    self.send_header("Access-Control-Allow-Origin", "*")
    self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    self.send_header("Access-Control-Allow-Headers", "Content-Type")
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def do_OPTIONS(self) -> None:
    self._send(200, ok())

  def do_GET(self) -> None:
    if self.path.startswith("/api/health"):
      settings = load_settings()
      self._send(200, ok({
        "service": "AI 求职决策工作台本地 API",
        "has_tavily_key": bool(settings.tavily_api_key),
        "has_openai_key": bool(settings.openai_api_key),
      }))
      return
    self._send(404, fail("接口不存在。"))

  def do_POST(self) -> None:
    try:
      length = int(self.headers.get("Content-Length", "0"))
      raw = self.rfile.read(length).decode("utf-8") if length else "{}"
      payload = json.loads(raw or "{}")
      routes = {
        "/api/resume": load_resume,
        "/api/search": search_jobs,
        "/api/job": extract_job,
        "/api/match": build_match,
        "/api/polish": polish_resume,
      }
      handler = routes.get(self.path)
      if not handler:
        self._send(404, fail("接口不存在。"))
        return
      self._send(200, handler(payload))
    except Exception as exc:
      self._send(500, fail(str(exc)))


def run(host: str = "127.0.0.1", port: int = 8765) -> None:
  server = ThreadingHTTPServer((host, port), Handler)
  print(f"本地 API 已启动：http://{host}:{port}")
  server.serve_forever()


if __name__ == "__main__":
  run()
