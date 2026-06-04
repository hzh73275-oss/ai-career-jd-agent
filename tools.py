from src.core.config import load_settings
from src.services.formatters import (
  format_job_info,
  format_match_report,
  format_resume_advice,
  format_search_results,
)
from src.workflows.resume_jd_workflow import ResumeJDWorkflow


WORKFLOW = ResumeJDWorkflow(load_settings(), profile_name="ai_intern")


def search_jobs(query):
  """
  search_jobs:
  e.g. search_jobs: 大模型 Agent 实习 北京 上海 武汉
  使用 Tavily 搜索多来源公开岗位，默认最多返回 30 个候选岗位。
  """
  try:
    return format_search_results(WORKFLOW.search_jobs(query, max_results=30))
  except Exception as exc:
    return f"错误：岗位搜索失败：{exc}"


def extract_job_info(input_text):
  """
  extract_job_info:
  e.g. extract_job_info: 1
  从搜索结果编号、公开岗位链接或用户粘贴的岗位描述中提取岗位信息。
  """
  try:
    return format_job_info(WORKFLOW.extract_job(input_text))
  except Exception as exc:
    return f"错误：岗位解析失败：{exc}"


def read_resume(input_text=None):
  """
  read_resume:
  e.g. read_resume: none
  读取默认 resume.txt，或读取用户提供的文本、Word 路径、PDF 路径。
  """
  try:
    value = "" if input_text in (None, "none") else str(input_text)
    return WORKFLOW.load_resume(value)
  except Exception as exc:
    return f"错误：简历读取失败：{exc}"


def match_resume_to_job(input_text=None):
  """
  match_resume_to_job:
  e.g. match_resume_to_job: none
  对比简历和最近一次提取的岗位信息，输出匹配点、缺口和风险提示。
  """
  try:
    return format_match_report(WORKFLOW.match())
  except Exception as exc:
    return f"错误：匹配分析失败：{exc}"


def suggest_resume_edits(input_text=None):
  """
  suggest_resume_edits:
  e.g. suggest_resume_edits: none
  根据最近一次匹配报告给出简历优化建议和项目补强计划。
  """
  try:
    return format_resume_advice(WORKFLOW.advise())
  except Exception as exc:
    return f"错误：建议生成失败：{exc}"
