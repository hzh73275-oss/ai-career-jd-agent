from __future__ import annotations

import time
from typing import Any, Callable, TypedDict

from langgraph.graph import END, StateGraph

from src.core.config import Settings
from src.core.profiles import get_profile
from src.core.schemas import (
  JDResumeComparison,
  JobInfo,
  MatchReport,
  ResumeAdvice,
  ResumeTranslationAdvice,
  SkillInsights,
)
from src.services.advisor import build_resume_advice
from src.services.formatters import (
  comparison_to_rows,
  format_comparison,
  format_full_report,
  format_match_report,
  format_resume_advice,
  format_resume_translation,
  format_skill_insights,
)
from src.services.jd_parser import extract_job_info
from src.services.matcher import match_resume_to_job
from src.services.resume_comparison import compare_resume_to_jd
from src.services.resume_translator import build_resume_translation_advice
from src.services.skill_gap_analyzer import analyze_skill_gaps


class GraphTraceItem(TypedDict):
  node: str
  status: str
  summary: str
  elapsed_ms: int


class ResumeJDGraphState(TypedDict, total=False):
  resume_text: str
  jd_text: str
  profile_name: str
  settings: Settings
  job_info: JobInfo
  match_report: MatchReport
  comparison: JDResumeComparison
  skill_insights: SkillInsights
  advice: ResumeAdvice
  translation: ResumeTranslationAdvice
  report_text: str
  advice_text: str
  comparison_text: str
  skill_text: str
  translation_text: str
  full_report: str
  comparison_rows: list[dict[str, str]]
  trace: list[GraphTraceItem]
  errors: list[str]


def _summary(value: Any) -> str:
  if isinstance(value, JobInfo):
    return f"识别岗位：{value.title or '未命名岗位'}，关键词 {len(value.keywords)} 个"
  if isinstance(value, MatchReport):
    return f"匹配等级：{value.level}，分数 {value.score}/100"
  if isinstance(value, JDResumeComparison):
    return f"生成 {len(value.items)} 条 JD-简历对比"
  if isinstance(value, SkillInsights):
    total = len(value.matched_skills) + len(value.weak_evidence_skills) + len(value.missing_skills)
    return f"分析 {total} 个岗位技能，推荐 {len(value.interview_questions)} 道面试题"
  if isinstance(value, ResumeAdvice):
    return f"生成 {len(value.rewrite_suggestions)} 条改写建议和 {len(value.project_plan)} 条补强计划"
  if isinstance(value, ResumeTranslationAdvice):
    return f"生成 {len(value.target_capabilities)} 个岗位靶心能力"
  if isinstance(value, str):
    return value[:80]
  return "节点完成"


def _with_trace(
  node: str,
  fn: Callable[[ResumeJDGraphState], dict[str, Any]],
) -> Callable[[ResumeJDGraphState], dict[str, Any]]:
  def wrapped(state: ResumeJDGraphState) -> dict[str, Any]:
    start = time.perf_counter()
    try:
      updates = fn(state)
      elapsed_ms = int((time.perf_counter() - start) * 1000)
      summary_value = next((value for key, value in updates.items() if key != "trace"), "")
      trace = [
        *state.get("trace", []),
        {
          "node": node,
          "status": "success",
          "summary": _summary(summary_value),
          "elapsed_ms": elapsed_ms,
        },
      ]
      return {**updates, "trace": trace}
    except Exception as exc:
      elapsed_ms = int((time.perf_counter() - start) * 1000)
      trace = [
        *state.get("trace", []),
        {
          "node": node,
          "status": "error",
          "summary": str(exc),
          "elapsed_ms": elapsed_ms,
        },
      ]
      errors = [*state.get("errors", []), f"{node}: {exc}"]
      return {"trace": trace, "errors": errors}

  return wrapped


def _profile(state: ResumeJDGraphState):
  return get_profile(state.get("profile_name", "ai_intern"))


def validate_input(state: ResumeJDGraphState) -> dict[str, Any]:
  resume_text = (state.get("resume_text") or "").strip()
  jd_text = (state.get("jd_text") or "").strip()
  if not resume_text:
    raise ValueError("请先上传或粘贴简历。")
  if not jd_text:
    raise ValueError("请先选择岗位或粘贴 JD。")
  return {
    "resume_text": resume_text,
    "jd_text": jd_text,
    "errors": [],
  }


def parse_jd(state: ResumeJDGraphState) -> dict[str, Any]:
  job = extract_job_info(state["jd_text"], _profile(state).keywords, None)
  return {"job_info": job}


def match_resume(state: ResumeJDGraphState) -> dict[str, Any]:
  report = match_resume_to_job(state["resume_text"], state["job_info"], _profile(state))
  return {"match_report": report}


def compare_resume_jd(state: ResumeJDGraphState) -> dict[str, Any]:
  comparison = compare_resume_to_jd(state["resume_text"], state["job_info"], _profile(state))
  return {"comparison": comparison}


def retrieve_and_analyze_skills(state: ResumeJDGraphState) -> dict[str, Any]:
  insights = analyze_skill_gaps(state["resume_text"], state["job_info"])
  return {"skill_insights": insights}


def build_advice(state: ResumeJDGraphState) -> dict[str, Any]:
  advice = build_resume_advice(state["match_report"], _profile(state))
  return {"advice": advice}


def build_translation(state: ResumeJDGraphState) -> dict[str, Any]:
  translation = build_resume_translation_advice(
    state["resume_text"],
    state["job_info"],
    state["match_report"],
    _profile(state),
  )
  return {"translation": translation}


def build_report(state: ResumeJDGraphState) -> dict[str, Any]:
  report_text = format_match_report(state["match_report"])
  advice_text = format_resume_advice(state["advice"])
  comparison_text = format_comparison(state["comparison"])
  skill_text = format_skill_insights(state["skill_insights"])
  translation_text = format_resume_translation(state["translation"])
  full_report = format_full_report(
    report_text,
    comparison_text,
    skill_text,
    translation_text,
    advice_text,
  )
  return {
    "report_text": report_text,
    "advice_text": advice_text,
    "comparison_text": comparison_text,
    "skill_text": skill_text,
    "translation_text": translation_text,
    "comparison_rows": comparison_to_rows(state["comparison"]),
    "full_report": full_report,
  }


def build_resume_jd_graph():
  def route_to(next_node: str):
    def route(state: ResumeJDGraphState) -> str:
      return "end" if state.get("errors") else next_node
    return route

  graph = StateGraph(ResumeJDGraphState)
  graph.add_node("validate_input", _with_trace("validate_input", validate_input))
  graph.add_node("parse_jd", _with_trace("parse_jd", parse_jd))
  graph.add_node("match_resume", _with_trace("match_resume", match_resume))
  graph.add_node("compare_resume_jd", _with_trace("compare_resume_jd", compare_resume_jd))
  graph.add_node("retrieve_and_analyze_skills", _with_trace("retrieve_and_analyze_skills", retrieve_and_analyze_skills))
  graph.add_node("build_advice", _with_trace("build_advice", build_advice))
  graph.add_node("build_translation", _with_trace("build_translation", build_translation))
  graph.add_node("build_full_report", _with_trace("build_full_report", build_report))

  graph.set_entry_point("validate_input")
  graph.add_conditional_edges("validate_input", route_to("parse_jd"), {"parse_jd": "parse_jd", "end": END})
  graph.add_conditional_edges("parse_jd", route_to("match_resume"), {"match_resume": "match_resume", "end": END})
  graph.add_conditional_edges("match_resume", route_to("compare_resume_jd"), {"compare_resume_jd": "compare_resume_jd", "end": END})
  graph.add_conditional_edges("compare_resume_jd", route_to("retrieve_and_analyze_skills"), {"retrieve_and_analyze_skills": "retrieve_and_analyze_skills", "end": END})
  graph.add_conditional_edges("retrieve_and_analyze_skills", route_to("build_advice"), {"build_advice": "build_advice", "end": END})
  graph.add_conditional_edges("build_advice", route_to("build_translation"), {"build_translation": "build_translation", "end": END})
  graph.add_conditional_edges("build_translation", route_to("build_full_report"), {"build_full_report": "build_full_report", "end": END})
  graph.add_edge("build_full_report", END)
  return graph.compile()


def run_resume_jd_graph(
  resume_text: str,
  jd_text: str,
  settings: Settings,
  profile_name: str = "ai_intern",
) -> ResumeJDGraphState:
  app = build_resume_jd_graph()
  result = app.invoke({
    "resume_text": resume_text,
    "jd_text": jd_text,
    "settings": settings,
    "profile_name": profile_name,
    "trace": [],
    "errors": [],
  })
  errors = result.get("errors", [])
  if errors:
    raise RuntimeError(errors[-1])
  return result
