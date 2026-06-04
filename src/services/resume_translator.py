from __future__ import annotations

import httpx

from src.core.config import Settings
from src.core.schemas import JobInfo, MatchReport, ResumeTranslationAdvice, RoleProfile
from src.services.text_utils import clip_text


def _friendly_llm_error(error: Exception) -> str:
  message = str(error)
  return _friendly_llm_message(message)


def _friendly_llm_message(message: str) -> str:
  lowered = message.lower()
  if (
    "not been recharged" in lowered
    or "free quota" in lowered
    or "prevent abuse" in lowered
    or "topup" in lowered
  ):
    return "大模型服务商提示：当前账号免费额度已用完或未充值。本地规则版建议仍可使用；如果想继续用大模型润色，需要更换可用 API Key 或给当前账号充值。"
  if "401" in lowered or "unauthorized" in lowered or "invalid api key" in lowered:
    return "大模型服务商提示：API Key 无效或没有权限。请检查 .env 中的 OPENAI_API_KEY。"
  if "timeout" in lowered or "timed out" in lowered:
    return "大模型服务商响应超时。本地规则版建议仍可使用，可以稍后重试。"
  return f"大模型润色失败，已保留本地规则版建议。失败原因：{message}"


def _pick_target_capabilities(job: JobInfo, report: MatchReport, profile: RoleProfile) -> list[str]:
  candidates: list[str] = []
  candidates.extend(job.keywords)
  candidates.extend(report.matched_keywords)
  for keyword in profile.keywords:
    if keyword in job.raw_text and keyword not in candidates:
      candidates.append(keyword)
  return list(dict.fromkeys(candidates))[:6]


def _pick_priority_experiences(resume_text: str, report: MatchReport, profile: RoleProfile) -> list[str]:
  experiences = []
  for signal in profile.strong_resume_signals:
    if signal.lower() in resume_text.lower():
      experiences.append(f"简历中已有「{signal}」相关经历，建议放在更靠前的位置，并补清楚业务场景、技术动作和验证结果。")

  for keyword in report.matched_keywords:
    if keyword not in profile.strong_resume_signals:
      experiences.append(f"岗位需要「{keyword}」，简历中已有相关线索，建议在项目或实习经历里明确对应到该能力。")

  if not experiences:
    experiences.append("暂未识别到非常明确的岗位对应经历，建议先补充完整简历文本或粘贴更完整的 JD 后再做最终改写。")
  return experiences[:6]


def _build_rewrite_examples(report: MatchReport, job: JobInfo, profile: RoleProfile) -> list[str]:
  examples = []
  matched = report.matched_keywords[:5]
  if matched:
    examples.append(
      f"围绕岗位要求的「{'、'.join(matched)}」，将相关经历改写为：参与相关模块开发/调试，负责需求拆解、接口调用、结果验证与问题排查。"
    )
  if profile.name == "ai_intern":
    examples.extend([
      "如果你确实做过大模型接口调用，可写为：参与 LLM 接口调用与 Prompt 调优，约束模型输出格式，并对生成结果进行人工验证与异常排查。",
      "如果你确实做过 Agent 项目，可写为：实现基于工具调用的 Agent 流程，完成 Action 解析、Observation 回填和终止条件控制。",
      "如果你确实做过 Docker 或部署测试，可写为：在容器环境中完成服务运行、依赖配置和接口联调，定位并修复运行过程中的异常问题。",
    ])
  else:
    examples.append("将经历改写为：参与岗位相关任务，负责资料整理、流程推进、结果复盘和跨角色沟通，保证任务按要求完成。")

  if job.responsibilities:
    examples.append(f"JD 职责里提到「{job.responsibilities[0]}」，简历中对应经历可以优先使用同类动词：参与、完成、实现、验证、排查。")
  return examples[:6]


def _build_do_not_overclaim(report: MatchReport, job: JobInfo) -> list[str]:
  notes = []
  for keyword in report.missing_keywords[:8]:
    notes.append(f"简历中暂未识别到「{keyword}」的真实经历，不建议直接写成“熟练掌握”或“独立负责”。")
  if not job.raw_text or len(job.raw_text) < 160:
    notes.append("当前岗位信息较少，建议粘贴完整 JD 后再生成最终简历改写版本。")
  notes.append("不要编造上线、用户量、准确率提升、业务收入等无法证明的结果。")
  return notes[:8]


def _build_placement_suggestions(report: MatchReport) -> list[str]:
  suggestions = [
    "把与 JD 直接相关的项目放在项目经历前 1-2 位。",
    "实习经历优先写清楚业务场景、你负责的技术动作和最终验证方式。",
    "技术能力部分只保留你能解释清楚、面试能讲出细节的关键词。",
  ]
  if report.missing_keywords:
    suggestions.append("JD 中缺口明显的能力放进补强计划，不要直接写进简历正文。")
  return suggestions


def build_resume_translation_advice(
  resume_text: str,
  job: JobInfo,
  report: MatchReport,
  profile: RoleProfile,
) -> ResumeTranslationAdvice:
  return ResumeTranslationAdvice(
    target_capabilities=_pick_target_capabilities(job, report, profile),
    priority_experiences=_pick_priority_experiences(resume_text, report, profile),
    rewrite_examples=_build_rewrite_examples(report, job, profile),
    do_not_overclaim=_build_do_not_overclaim(report, job),
    placement_suggestions=_build_placement_suggestions(report),
  )


def _build_polish_prompt(
  resume_text: str,
  job: JobInfo,
  advice: ResumeTranslationAdvice,
) -> str:
  return f"""
你是一名谨慎的中文简历修改助手。请根据岗位 JD 和已有简历，输出“可复制到简历里的改写建议”。

硬性规则：
1. 只能基于已有简历和下方规则建议改写表达。
2. 不得编造项目、公司、指标、上线、用户量、准确率提升、获奖或论文。
3. 没做过的能力只能写进“补强建议”，不能写进简历条目。
4. 输出中文，语气像求职简历，动词明确、表达保守。

岗位标题：
{job.title}

岗位信息摘要：
{clip_text(job.raw_text, 1600)}

已有简历摘要：
{clip_text(resume_text, 2200)}

本地规则建议：
岗位靶心能力：{'、'.join(advice.target_capabilities)}
建议突出经历：{'；'.join(advice.priority_experiences)}
不要硬写：{'；'.join(advice.do_not_overclaim)}

请按以下格式输出：
一、建议放前面的经历
二、可复制的简历改写句
三、不要写进简历的内容
四、如果继续投这个岗位，建议补强什么
""".strip()


def polish_resume_translation(
  resume_text: str,
  job: JobInfo,
  advice: ResumeTranslationAdvice,
  settings: Settings,
) -> ResumeTranslationAdvice:
  if not settings.openai_api_key:
    advice.llm_notice = "未配置 OPENAI_API_KEY，已保留本地规则版建议。大模型润色需要使用你自己配置的 API Key。"
    return advice

  base_url = (settings.openai_base_url or "https://api.openai.com/v1").rstrip("/")
  endpoint = f"{base_url}/chat/completions"
  payload = {
    "model": settings.model_name,
    "messages": [
      {"role": "system", "content": "你只做中文简历表达润色，不能编造事实。"},
      {"role": "user", "content": _build_polish_prompt(resume_text, job, advice)},
    ],
    "temperature": 0.2,
  }
  headers = {
    "Authorization": f"Bearer {settings.openai_api_key}",
    "Content-Type": "application/json",
  }

  try:
    response = httpx.post(endpoint, json=payload, headers=headers, timeout=45)
    response.raise_for_status()
    data = response.json()
    polished_text = data["choices"][0]["message"]["content"].strip()
    if (
      "not been recharged" in polished_text.lower()
      or "free quota" in polished_text.lower()
      or "prevent abuse" in polished_text.lower()
      or "topup" in polished_text.lower()
    ):
      advice.polished_text = ""
      advice.used_llm = False
      advice.llm_notice = _friendly_llm_message(polished_text)
      return advice
    advice.polished_text = polished_text
    advice.used_llm = True
    advice.llm_notice = "已使用你自己配置的 API Key 完成大模型润色。"
  except Exception as exc:
    advice.llm_notice = _friendly_llm_error(exc)
  return advice
