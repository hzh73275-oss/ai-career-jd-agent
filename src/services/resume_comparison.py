import re

from src.core.schemas import JDResumeComparison, JDResumeComparisonItem, JobInfo, RoleProfile
from src.services.text_utils import clean_text


EVIDENCE_WORDS = [
  "参与",
  "负责",
  "完成",
  "实现",
  "开发",
  "调试",
  "验证",
  "排查",
  "部署",
  "优化",
  "构建",
  "设计",
]


def _split_resume_sentences(resume_text: str) -> list[str]:
  parts = re.split(r"[。；;\n]", resume_text or "")
  return [clean_text(part) for part in parts if 8 <= len(clean_text(part)) <= 180]


def _collect_requirements(job: JobInfo, profile: RoleProfile) -> list[str]:
  requirements: list[str] = []
  requirements.extend(job.keywords)
  requirements.extend(job.requirements[:5])
  requirements.extend(job.responsibilities[:5])
  for keyword in profile.keywords:
    if keyword in job.raw_text and keyword not in requirements:
      requirements.append(keyword)
  return list(dict.fromkeys([item for item in requirements if item]))[:12]


def _find_evidence(requirement: str, resume_sentences: list[str]) -> str:
  requirement_lower = requirement.lower()
  for sentence in resume_sentences:
    if requirement_lower in sentence.lower():
      return sentence

  tokens = [token for token in re.split(r"[\s,，/、]+", requirement) if len(token) >= 2]
  for sentence in resume_sentences:
    if any(token.lower() in sentence.lower() for token in tokens):
      return sentence
  return ""


def _has_action_evidence(text: str) -> bool:
  return any(word in text for word in EVIDENCE_WORDS)


def _build_item(requirement: str, evidence: str) -> JDResumeComparisonItem:
  if not evidence:
    return JDResumeComparisonItem(
      jd_requirement=requirement,
      resume_evidence="简历中暂未找到明确证据",
      status="简历缺失",
      suggestion="不要直接写成熟练掌握。建议先补真实项目或在补强计划中说明准备补齐。",
      priority="高",
    )

  if not _has_action_evidence(evidence) or len(evidence) < 24:
    return JDResumeComparisonItem(
      jd_requirement=requirement,
      resume_evidence=evidence,
      status="写得不清楚",
      suggestion="建议补充业务场景、你负责的技术动作、验证方式或最终结果，避免只堆关键词。",
      priority="中",
    )

  return JDResumeComparisonItem(
    jd_requirement=requirement,
    resume_evidence=evidence,
    status="已匹配",
    suggestion="建议把这段经历放到更靠前的位置，并保持表达真实、可被面试追问。",
    priority="中",
  )


def compare_resume_to_jd(resume_text: str, job: JobInfo, profile: RoleProfile) -> JDResumeComparison:
  resume_sentences = _split_resume_sentences(resume_text)
  requirements = _collect_requirements(job, profile)
  items = []
  for requirement in requirements:
    evidence = _find_evidence(requirement, resume_sentences)
    items.append(_build_item(requirement, evidence))

  if not items:
    items.append(JDResumeComparisonItem(
      jd_requirement="完整 JD",
      resume_evidence="岗位信息不足",
      status="不建议硬写",
      suggestion="建议粘贴完整 JD 后再做最终简历修改。",
      priority="高",
    ))
  return JDResumeComparison(items=items)
