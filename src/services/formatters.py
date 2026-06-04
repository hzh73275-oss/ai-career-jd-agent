from collections import defaultdict

from src.core.schemas import (
  JDResumeComparison,
  JobInfo,
  MatchReport,
  ResumeAdvice,
  ResumeTranslationAdvice,
  SearchResult,
)


TIER_ORDER = ["冲刺岗", "主投岗", "保底岗", "不建议"]


def group_search_results(results: list[SearchResult]) -> dict[str, list[SearchResult]]:
  grouped = defaultdict(list)
  for result in results:
    grouped[result.tier].append(result)
  return {tier: grouped.get(tier, []) for tier in TIER_ORDER}


def format_job_info(job: JobInfo) -> str:
  return "\n".join([
    f"岗位标题：{job.title}",
    f"来源链接：{job.source_url or '无'}",
    f"可能地点：{', '.join(job.locations) or '未识别'}",
    f"可能薪资：{', '.join(job.salary_hints) or '未识别'}",
    f"实习周期/频率线索：{', '.join(job.duration_hints) or '未识别'}",
    f"关键词：{', '.join(job.keywords) or '未识别'}",
    f"岗位职责线索：{'; '.join(job.responsibilities) or '未识别'}",
    f"任职要求线索：{'; '.join(job.requirements) or '未识别'}",
    f"岗位原文摘要：{job.raw_text[:1200]}",
  ])


def format_match_report(report: MatchReport) -> str:
  return "\n".join([
    f"综合匹配等级：{report.level}",
    f"参考匹配分：{report.score}/100（启发式评分，仅用于排序，不代表真实录用概率）",
    f"匹配关键词：{', '.join(report.matched_keywords) or '暂无明显匹配'}",
    f"待补关键词：{', '.join(report.missing_keywords[:12]) or '暂无明显缺口'}",
    f"简历已有亮点：{', '.join(report.resume_highlights) or '未识别到明显亮点'}",
    f"投递建议：{report.recommendation}",
    f"风险提示：{'; '.join(report.risk_notes) or '暂无明显风险'}",
  ])


def format_resume_advice(advice: ResumeAdvice) -> str:
  lines = ["简历优化建议："]
  lines.extend(f"{index}. {item}" for index, item in enumerate(advice.rewrite_suggestions, start=1))
  lines.append("\n项目补强建议：")
  lines.extend(f"{index}. {item}" for index, item in enumerate(advice.project_plan, start=1))
  lines.append("\n不要夸大的地方：")
  lines.extend(f"{index}. {item}" for index, item in enumerate(advice.caution_notes, start=1))
  return "\n".join(lines)


def format_resume_translation(advice: ResumeTranslationAdvice) -> str:
  lines = ["岗位想看到什么："]
  lines.extend(f"{index}. {item}" for index, item in enumerate(advice.target_capabilities or ["暂未识别到明确能力"], start=1))

  lines.append("\n你简历里可以重点写什么：")
  lines.extend(f"{index}. {item}" for index, item in enumerate(advice.priority_experiences, start=1))

  lines.append("\n建议改写成这样：")
  lines.extend(f"{index}. {item}" for index, item in enumerate(advice.rewrite_examples, start=1))

  lines.append("\n这些不要硬写：")
  lines.extend(f"{index}. {item}" for index, item in enumerate(advice.do_not_overclaim, start=1))

  lines.append("\n建议放在简历哪里：")
  lines.extend(f"{index}. {item}" for index, item in enumerate(advice.placement_suggestions, start=1))

  if advice.llm_notice:
    lines.append(f"\n大模型润色状态：{advice.llm_notice}")
  if advice.polished_text:
    lines.append("\n大模型润色版本：")
    lines.append(advice.polished_text)
  return "\n".join(lines)


def comparison_to_rows(comparison: JDResumeComparison, limit: int | None = None) -> list[dict[str, str]]:
  items = comparison.items[:limit] if limit else comparison.items
  return [
    {
      "JD 要求": item.jd_requirement,
      "简历证据": item.resume_evidence,
      "状态": item.status,
      "修改建议": item.suggestion,
      "优先级": item.priority,
    }
    for item in items
  ]


def format_comparison(comparison: JDResumeComparison) -> str:
  lines = ["JD-简历点对点对比："]
  for index, item in enumerate(comparison.items, start=1):
    lines.extend([
      f"\n{index}. JD 要求：{item.jd_requirement}",
      f"简历证据：{item.resume_evidence}",
      f"状态：{item.status}",
      f"修改建议：{item.suggestion}",
      f"优先级：{item.priority}",
    ])
  return "\n".join(lines)


def format_full_report(
  report_text: str,
  comparison_text: str,
  translation_text: str,
  advice_text: str,
) -> str:
  return "\n\n".join([
    "一、完整匹配分析\n" + (report_text or "暂无"),
    "二、完整点对点对比\n" + (comparison_text or "暂无"),
    "三、完整简历翻译润色\n" + (translation_text or "暂无"),
    "四、完整补强计划\n" + (advice_text or "暂无"),
  ])
