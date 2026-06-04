from dataclasses import dataclass, field

from src.core.config import Settings
from src.core.profiles import get_profile
from src.core.schemas import (
  JDResumeComparison,
  JobInfo,
  MatchReport,
  ResumeAdvice,
  ResumeTranslationAdvice,
  SearchResult,
)
from src.services.advisor import build_resume_advice
from src.services.jd_parser import extract_job_info
from src.services.job_search import search_public_jobs
from src.services.matcher import match_resume_to_job
from src.services.resume_comparison import compare_resume_to_jd
from src.services.resume_service import load_resume
from src.services.resume_translator import build_resume_translation_advice, polish_resume_translation


@dataclass
class ResumeJDWorkflow:
  settings: Settings
  profile_name: str = "ai_intern"
  search_results: list[SearchResult] = field(default_factory=list)
  current_job: JobInfo | None = None
  current_resume: str = ""
  current_report: MatchReport | None = None
  current_advice: ResumeAdvice | None = None
  current_translation: ResumeTranslationAdvice | None = None
  current_comparison: JDResumeComparison | None = None

  @property
  def profile(self):
    return get_profile(self.profile_name)

  def search_jobs(
    self,
    query: str,
    max_results: int = 30,
    source_keys: list[str] | None = None,
    mode: str = "fast",
  ) -> list[SearchResult]:
    self.search_results = search_public_jobs(
      query,
      self.settings.tavily_api_key,
      max_results=max_results,
      source_keys=source_keys,
      mode=mode,
    )
    return self.search_results

  def extract_job(self, input_text: str) -> JobInfo:
    self.current_job = extract_job_info(input_text, self.profile.keywords, self.search_results)
    return self.current_job

  def load_resume(self, input_text_or_path: str = "") -> str:
    self.current_resume = load_resume(input_text_or_path, self.settings.default_resume_path)
    return self.current_resume

  def match(self) -> MatchReport:
    if not self.current_job:
      raise RuntimeError("还没有岗位信息，请先提取 JD。")
    if not self.current_resume:
      self.load_resume()
    self.current_report = match_resume_to_job(self.current_resume, self.current_job, self.profile)
    return self.current_report

  def advise(self) -> ResumeAdvice:
    if not self.current_report:
      self.match()
    self.current_advice = build_resume_advice(self.current_report, self.profile)
    return self.current_advice

  def translate_resume(self, polish: bool = False) -> ResumeTranslationAdvice:
    if not self.current_job:
      raise RuntimeError("还没有岗位信息，请先提取 JD。")
    if not self.current_resume:
      self.load_resume()
    if not self.current_report:
      self.match()

    self.current_translation = build_resume_translation_advice(
      self.current_resume,
      self.current_job,
      self.current_report,
      self.profile,
    )
    if polish:
      self.current_translation = polish_resume_translation(
        self.current_resume,
        self.current_job,
        self.current_translation,
        self.settings,
      )
    return self.current_translation

  def compare(self) -> JDResumeComparison:
    if not self.current_job:
      raise RuntimeError("还没有岗位信息，请先提取 JD。")
    if not self.current_resume:
      self.load_resume()
    self.current_comparison = compare_resume_to_jd(
      self.current_resume,
      self.current_job,
      self.profile,
    )
    return self.current_comparison
