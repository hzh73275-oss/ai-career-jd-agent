from __future__ import annotations

import base64
import tempfile
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.core.config import load_settings
from src.services.formatters import (
  comparison_to_rows,
  format_comparison,
  format_full_report,
  format_job_info,
  format_match_report,
  format_resume_advice,
  format_resume_translation,
  format_skill_insights,
)
from src.services.job_search import build_platform_notices, build_source_stats
from src.services.skill_retriever import (
  load_skill_library,
  search_skill_library,
  skill_categories,
)
from src.services.skill_vector_store import (
  rebuild_skill_vector_index,
  vector_store_status,
)
from src.graphs.resume_jd_graph import run_resume_jd_graph
from src.workflows.resume_jd_workflow import ResumeJDWorkflow


workflow = ResumeJDWorkflow(settings=load_settings(), profile_name="ai_intern")
app = FastAPI(
  title="AI Career JD Agent API",
  description="Local API for resume-JD matching, public job search, and resume polish suggestions.",
  version="0.1.0",
)

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=False,
  allow_methods=["*"],
  allow_headers=["*"],
)


class ResumePayload(BaseModel):
  text: str = ""
  filename: str = ""
  content_base64: str = ""


class SearchPayload(BaseModel):
  query: str = ""
  max_results: int = 30
  source_keys: list[str] | None = None
  mode: str = "fast"


class JobPayload(BaseModel):
  input_text: str = ""


class PolishPayload(BaseModel):
  use_llm: bool = False


class SkillSearchPayload(BaseModel):
  query: str = ""
  category: str = ""
  limit: int = 50
  mode: str = "hybrid"


class GraphMatchPayload(BaseModel):
  resume_text: str = ""
  jd_text: str = ""


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


def normalize_mode(mode: str) -> str:
  if mode in ["快速搜索", "quick", "fast"]:
    return "fast"
  if mode in ["深度搜索", "deep"]:
    return "deep"
  return "fast"


@app.get("/api/health")
def health() -> dict[str, Any]:
  settings = load_settings()
  return ok({
    "service": "AI 求职决策工作台本地 API",
    "api_framework": "FastAPI",
    "has_tavily_key": bool(settings.tavily_api_key),
    "has_openai_key": bool(settings.openai_api_key),
  })


@app.post("/api/resume")
def load_resume(payload: ResumePayload) -> dict[str, Any]:
  text = payload.text.strip()

  if payload.content_base64:
    path = save_upload(payload.filename, payload.content_base64)
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


@app.post("/api/search")
def search_jobs(payload: SearchPayload) -> dict[str, Any]:
  query = payload.query.strip()
  if not query:
    return fail("请先输入岗位关键词。")

  max_results = max(5, min(int(payload.max_results or 30), 100))
  source_keys = payload.source_keys or None
  mode = normalize_mode(payload.mode)

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


@app.post("/api/job")
def extract_job(payload: JobPayload) -> dict[str, Any]:
  input_text = payload.input_text.strip()
  if not input_text:
    return fail("请先选择岗位或粘贴 JD。")
  job = workflow.extract_job(input_text)
  return ok({
    "job": to_jsonable(job),
    "job_text": format_job_info(job),
  })


@app.post("/api/match")
def build_match() -> dict[str, Any]:
  report = workflow.match()
  advice = workflow.advise()
  comparison = workflow.compare()
  skill_insights = workflow.analyze_skills()
  translation = workflow.translate_resume(polish=False)
  report_text = format_match_report(report)
  advice_text = format_resume_advice(advice)
  comparison_text = format_comparison(comparison)
  skill_text = format_skill_insights(skill_insights)
  translation_text = format_resume_translation(translation)

  return ok({
    "report": to_jsonable(report),
    "advice": to_jsonable(advice),
    "comparison": to_jsonable(comparison),
    "skill_insights": to_jsonable(skill_insights),
    "translation": to_jsonable(translation),
    "comparison_rows": comparison_to_rows(comparison),
    "report_text": report_text,
    "advice_text": advice_text,
    "comparison_text": comparison_text,
    "skill_text": skill_text,
    "translation_text": translation_text,
    "full_report": format_full_report(
      report_text,
      comparison_text,
      skill_text,
      translation_text,
      advice_text,
    ),
  })


@app.post("/api/graph/match")
def build_graph_match(payload: GraphMatchPayload) -> dict[str, Any]:
  resume_text = payload.resume_text.strip()
  jd_text = payload.jd_text.strip()
  if not resume_text:
    return fail("请先上传或粘贴简历。")
  if not jd_text:
    return fail("请先选择岗位或粘贴 JD。")

  try:
    result = run_resume_jd_graph(
      resume_text=resume_text,
      jd_text=jd_text,
      settings=load_settings(),
      profile_name="ai_intern",
    )
  except Exception as exc:
    return fail(f"LangGraph 匹配分析失败：{exc}")
  return ok({
    "graph_mode": True,
    "graph_trace": result.get("trace", []),
    "report": to_jsonable(result.get("match_report")),
    "advice": to_jsonable(result.get("advice")),
    "comparison": to_jsonable(result.get("comparison")),
    "skill_insights": to_jsonable(result.get("skill_insights")),
    "translation": to_jsonable(result.get("translation")),
    "comparison_rows": result.get("comparison_rows", []),
    "report_text": result.get("report_text", ""),
    "advice_text": result.get("advice_text", ""),
    "comparison_text": result.get("comparison_text", ""),
    "skill_text": result.get("skill_text", ""),
    "translation_text": result.get("translation_text", ""),
    "full_report": result.get("full_report", ""),
  })


@app.post("/api/polish")
def polish_resume(payload: PolishPayload) -> dict[str, Any]:
  translation = workflow.translate_resume(polish=payload.use_llm)
  return ok({
    "translation": to_jsonable(translation),
    "translation_text": format_resume_translation(translation),
  })


@app.get("/api/skills")
def list_skills() -> dict[str, Any]:
  skills = load_skill_library()
  return ok({
    "skills": skills,
    "count": len(skills),
    "categories": skill_categories(skills),
    "vector_status": vector_store_status(),
    "source": "local_skill_library",
  })


@app.get("/api/skills/categories")
def list_skill_categories() -> dict[str, Any]:
  return ok({
    "categories": skill_categories(),
  })


@app.get("/api/skills/vector-status")
def skill_vector_status() -> dict[str, Any]:
  return ok({
    "vector_status": vector_store_status(),
  })


@app.post("/api/skills/reindex")
def reindex_skills() -> dict[str, Any]:
  try:
    return ok({
      "vector_status": rebuild_skill_vector_index(),
    })
  except Exception as exc:
    return fail(f"本地向量索引构建失败：{exc}")


@app.post("/api/skills/search")
def search_skills(payload: SkillSearchPayload) -> dict[str, Any]:
  limit = max(1, min(int(payload.limit or 50), 100))
  mode = payload.mode if payload.mode in {"keyword", "vector", "hybrid"} else "hybrid"
  results = search_skill_library(
    query=payload.query,
    category=payload.category,
    limit=limit,
    mode=mode,
  )
  return ok({
    "skills": [
      {
        **item.card,
        "score": item.score,
        "keyword_score": item.keyword_score,
        "vector_score": item.vector_score,
        "matched_terms": item.matched_terms,
        "retrieval_reason": item.retrieval_reason,
      }
      for item in results
    ],
    "count": len(results),
    "mode": mode,
    "vector_status": vector_store_status(),
    "source": "local_skill_library",
  })


def run(host: str = "127.0.0.1", port: int = 8765) -> None:
  import uvicorn

  uvicorn.run("src.api.server:app", host=host, port=port)


if __name__ == "__main__":
  run()
