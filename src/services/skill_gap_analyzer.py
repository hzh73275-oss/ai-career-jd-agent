from __future__ import annotations

import re
from typing import Any

from src.core.schemas import (
  InterviewQuestion,
  JobInfo,
  SkillInsightItem,
  SkillInsights,
)
from src.services.skill_retriever import RetrievedSkill, retrieve_skills_for_job
from src.services.text_utils import clean_text


ACTION_WORDS = [
  "参与",
  "负责",
  "完成",
  "实现",
  "开发",
  "设计",
  "构建",
  "部署",
  "优化",
  "调试",
  "验证",
  "评估",
  "接入",
  "迁移",
  "封装",
]


def split_resume_sentences(resume_text: str) -> list[str]:
  parts = re.split(r"[。；;\n\r]", resume_text or "")
  return [clean_text(part) for part in parts if 6 <= len(clean_text(part)) <= 220]


def _contains_term(text_lower: str, term: str) -> bool:
  term = clean_text(term)
  if not term:
    return False
  term_lower = term.lower()
  if re.search(r"[a-zA-Z0-9]", term_lower):
    return bool(re.search(rf"(?<![a-zA-Z0-9]){re.escape(term_lower)}(?![a-zA-Z0-9])", text_lower))
  return term_lower in text_lower


def _find_evidence(card: dict[str, Any], resume_sentences: list[str]) -> tuple[list[str], list[str]]:
  patterns = []
  patterns.extend(card.get("resume_evidence_patterns", []))
  patterns.extend(card.get("aliases", []))
  patterns.append(card.get("name", ""))

  evidence: list[str] = []
  matched_terms: list[str] = []
  for sentence in resume_sentences:
    sentence_lower = sentence.lower()
    sentence_terms = [
      str(pattern)
      for pattern in patterns
      if _contains_term(sentence_lower, str(pattern))
    ]
    if sentence_terms:
      evidence.append(sentence)
      matched_terms.extend(sentence_terms)
    if len(evidence) >= 3:
      break
  return list(dict.fromkeys(evidence)), list(dict.fromkeys(matched_terms))


def _has_action_evidence(evidence: list[str]) -> bool:
  joined = " ".join(evidence)
  return any(word in joined for word in ACTION_WORDS)


def _build_item(retrieved: RetrievedSkill, status: str, evidence: list[str], evidence_terms: list[str]) -> SkillInsightItem:
  card = retrieved.card
  suggestions = card.get("project_suggestions", [])
  if status == "已覆盖":
    suggestion = "简历中已有相关证据，建议把这段经历放在更靠前的位置，并补充任务、动作和结果。"
  elif status == "证据较弱":
    suggestion = "简历中出现了相关技能词，但项目动作或验证结果不够清楚，建议补充你具体负责的模块和效果。"
  else:
    suggestion = suggestions[0] if suggestions else "建议先补一个真实小项目，再把相关能力写入简历。"

  return SkillInsightItem(
    id=str(card.get("id", "")),
    name=str(card.get("name", "")),
    category=str(card.get("category", "")),
    score=retrieved.score,
    status=status,
    evidence=evidence,
    matched_terms=list(dict.fromkeys([*retrieved.matched_terms, *evidence_terms])),
    definition=str(card.get("definition", "")),
    suggestion=suggestion,
    source_refs=card.get("source_refs", []),
  )


def _collect_project_suggestions(missing: list[SkillInsightItem], weak: list[SkillInsightItem], retrieved: list[RetrievedSkill]) -> list[str]:
  suggestions: list[str] = []
  priority_ids = {item.id for item in [*missing, *weak]}
  for skill in retrieved:
    card = skill.card
    if card.get("id") not in priority_ids and len(suggestions) >= 4:
      continue
    suggestions.extend(str(item) for item in card.get("project_suggestions", []))
  return list(dict.fromkeys(suggestions))[:6]


def _collect_interview_questions(
  matched: list[SkillInsightItem],
  weak: list[SkillInsightItem],
  missing: list[SkillInsightItem],
  retrieved: list[RetrievedSkill],
) -> list[InterviewQuestion]:
  priority = [*missing, *weak, *matched]
  priority_ids = [item.id for item in priority]
  card_by_id = {str(skill.card.get("id", "")): skill.card for skill in retrieved}

  questions: list[InterviewQuestion] = []
  seen: set[str] = set()
  for skill_id in priority_ids:
    card = card_by_id.get(skill_id)
    if not card:
      continue
    for raw in card.get("interview_questions", [])[:3]:
      question = str(raw.get("question", ""))
      if not question or question in seen:
        continue
      seen.add(question)
      questions.append(InterviewQuestion(
        question=question,
        level=str(raw.get("level", "基础")),
        answer_points=[str(point) for point in raw.get("answer_points", [])],
        skill_id=skill_id,
        skill_name=str(card.get("name", "")),
      ))
      if len(questions) >= 12:
        return questions
  return questions


def analyze_skill_gaps(resume_text: str, job: JobInfo) -> SkillInsights:
  retrieved = retrieve_skills_for_job(job)
  resume_sentences = split_resume_sentences(resume_text)

  matched: list[SkillInsightItem] = []
  weak: list[SkillInsightItem] = []
  missing: list[SkillInsightItem] = []

  for skill in retrieved:
    evidence, evidence_terms = _find_evidence(skill.card, resume_sentences)
    if evidence and _has_action_evidence(evidence):
      matched.append(_build_item(skill, "已覆盖", evidence, evidence_terms))
    elif evidence:
      weak.append(_build_item(skill, "证据较弱", evidence, evidence_terms))
    else:
      missing.append(_build_item(skill, "缺失", [], []))

  project_suggestions = _collect_project_suggestions(missing, weak, retrieved)
  interview_questions = _collect_interview_questions(matched, weak, missing, retrieved)

  return SkillInsights(
    matched_skills=matched,
    weak_evidence_skills=weak,
    missing_skills=missing,
    project_suggestions=project_suggestions,
    interview_questions=interview_questions,
  )
