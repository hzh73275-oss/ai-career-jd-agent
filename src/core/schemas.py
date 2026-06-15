from dataclasses import dataclass, field


@dataclass
class SearchResult:
  index: int
  title: str
  url: str
  summary: str
  source: str = "公开网页"
  tier: str = "主投岗"
  tier_reason: str = "与搜索关键词相关，适合作为候选岗位。"


@dataclass
class JobInfo:
  title: str
  source_url: str = ""
  raw_text: str = ""
  locations: list[str] = field(default_factory=list)
  salary_hints: list[str] = field(default_factory=list)
  duration_hints: list[str] = field(default_factory=list)
  keywords: list[str] = field(default_factory=list)
  responsibilities: list[str] = field(default_factory=list)
  requirements: list[str] = field(default_factory=list)


@dataclass
class MatchReport:
  level: str
  score: int
  matched_keywords: list[str]
  missing_keywords: list[str]
  resume_highlights: list[str]
  risk_notes: list[str]
  recommendation: str


@dataclass
class ResumeAdvice:
  rewrite_suggestions: list[str]
  project_plan: list[str]
  caution_notes: list[str]


@dataclass
class ResumeTranslationAdvice:
  target_capabilities: list[str]
  priority_experiences: list[str]
  rewrite_examples: list[str]
  do_not_overclaim: list[str]
  placement_suggestions: list[str]
  polished_text: str = ""
  used_llm: bool = False
  llm_notice: str = ""


@dataclass
class JDResumeComparisonItem:
  jd_requirement: str
  resume_evidence: str
  status: str
  suggestion: str
  priority: str


@dataclass
class JDResumeComparison:
  items: list[JDResumeComparisonItem]


@dataclass
class InterviewQuestion:
  question: str
  level: str
  answer_points: list[str]
  skill_id: str = ""
  skill_name: str = ""


@dataclass
class SkillInsightItem:
  id: str
  name: str
  category: str
  score: int
  status: str
  evidence: list[str]
  matched_terms: list[str]
  definition: str
  suggestion: str
  source_refs: list[dict[str, str]] = field(default_factory=list)


@dataclass
class SkillInsights:
  matched_skills: list[SkillInsightItem]
  weak_evidence_skills: list[SkillInsightItem]
  missing_skills: list[SkillInsightItem]
  project_suggestions: list[str]
  interview_questions: list[InterviewQuestion]
  source: str = "local_skill_library"
  notice: str = "基于本地岗位技能知识库的混合检索增强分析，优先使用本地向量库，不调用付费 API。"


@dataclass
class RoleProfile:
  name: str
  display_name: str
  keywords: list[str]
  strong_resume_signals: list[str]
  gap_project_templates: list[str]
