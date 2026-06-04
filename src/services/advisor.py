from src.core.schemas import MatchReport, ResumeAdvice, RoleProfile


def build_resume_advice(report: MatchReport, profile: RoleProfile) -> ResumeAdvice:
  suggestions = [
    "把与 JD 直接相关的项目放在项目经历前 1-2 位。",
    "实习经历优先写清楚业务场景、你负责的技术动作、最终验证结果。",
    "技术能力只补你确实用过或能解释清楚的关键词。",
    "改写时使用“参与/完成/实现/验证/排查”等真实稳妥动词，避免夸大。",
  ]

  if profile.name == "ai_intern":
    suggestions.extend([
      "大模型岗位优先突出 Prompt 调优、LLM API、模型微调、Agent 工具调用等经历。",
      "如果 JD 提到 RAG 或 LangGraph，而简历没有相关项目，应放入补强计划，不要直接写成熟练掌握。",
    ])

  project_plan = []
  for template in profile.gap_project_templates:
    if any(keyword in template for keyword in report.missing_keywords):
      project_plan.append(template)
  if not project_plan:
    project_plan = profile.gap_project_templates[:2]

  caution_notes = [
    "不要编造上线、用户量、准确率提升等未验证成果。",
    "不要把只了解的技术写成熟练掌握。",
    "如果岗位硬性要求地点、实习时长或学历不满足，应降低投递优先级。",
  ]

  return ResumeAdvice(
    rewrite_suggestions=suggestions,
    project_plan=project_plan[:2],
    caution_notes=caution_notes,
  )
