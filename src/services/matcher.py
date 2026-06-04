from src.core.schemas import JobInfo, MatchReport, RoleProfile
from src.services.text_utils import find_keywords


def match_resume_to_job(resume_text: str, job: JobInfo, profile: RoleProfile) -> MatchReport:
  resume_keywords = find_keywords(resume_text, profile.keywords)
  job_keywords = job.keywords
  matched = [keyword for keyword in job_keywords if keyword in resume_keywords]
  missing = [keyword for keyword in job_keywords if keyword not in resume_keywords]
  highlights = [
    signal for signal in profile.strong_resume_signals
    if signal.lower() in resume_text.lower()
  ]

  score = 45 + min(len(matched) * 5, 35) + min(len(highlights) * 2, 15)
  score = min(score, 95)

  if score >= 80:
    level = "较匹配"
    recommendation = "建议优先投递，并针对该 JD 做简历定制。"
  elif score >= 65:
    level = "中等匹配"
    recommendation = "建议优化简历后投递，重点补足 JD 中最高频缺口。"
  else:
    level = "匹配度一般"
    recommendation = "建议先补项目或换更贴近当前经历的岗位。"

  risk_notes = []
  if missing:
    risk_notes.append("缺口关键词不要硬写到简历里，除非你确实做过相关项目。")
  if not job.raw_text or len(job.raw_text) < 120:
    risk_notes.append("岗位信息较少，建议粘贴完整 JD 后再做最终判断。")

  return MatchReport(
    level=level,
    score=score,
    matched_keywords=matched,
    missing_keywords=missing,
    resume_highlights=highlights,
    risk_notes=risk_notes,
    recommendation=recommendation,
  )
