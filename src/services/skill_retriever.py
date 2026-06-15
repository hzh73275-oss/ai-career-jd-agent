from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.core.config import ROOT_DIR
from src.core.schemas import JobInfo
from src.services.text_utils import clean_text


SKILL_LIBRARY_PATH = ROOT_DIR / "data" / "skill_library.json"


@dataclass
class RetrievedSkill:
  card: dict[str, Any]
  score: int
  matched_terms: list[str]
  keyword_score: int = 0
  vector_score: float = 0.0
  retrieval_reason: str = "关键词检索"


def load_skill_library(path: Path = SKILL_LIBRARY_PATH) -> list[dict[str, Any]]:
  if not path.exists():
    return []
  with path.open("r", encoding="utf-8") as file:
    data = json.load(file)
  return data if isinstance(data, list) else []


def build_job_skill_query(job: JobInfo) -> str:
  parts = [
    job.title,
    " ".join(job.keywords),
    " ".join(job.requirements),
    " ".join(job.responsibilities),
    job.raw_text,
  ]
  return clean_text(" ".join(part for part in parts if part))


def _contains_term(text_lower: str, term: str) -> bool:
  term = clean_text(term)
  if not term:
    return False
  term_lower = term.lower()
  if re.search(r"[a-zA-Z0-9]", term_lower):
    return bool(re.search(rf"(?<![a-zA-Z0-9]){re.escape(term_lower)}(?![a-zA-Z0-9])", text_lower))
  return term_lower in text_lower


def _score_card(text_lower: str, card: dict[str, Any]) -> RetrievedSkill | None:
  score = 0
  matched_terms: list[str] = []

  weighted_groups = [
    ([card.get("name", "")], 8),
    (card.get("aliases", []), 6),
    (card.get("jd_phrases", []), 10),
  ]

  for terms, weight in weighted_groups:
    for term in terms:
      if _contains_term(text_lower, str(term)):
        score += weight
        matched_terms.append(str(term))

  # A light category hint prevents generic words like "API" from dominating.
  category = str(card.get("category", ""))
  if category and _contains_term(text_lower, category):
    score += 2
    matched_terms.append(category)

  if score <= 0:
    return None
  terms = list(dict.fromkeys(matched_terms))
  return RetrievedSkill(
    card=card,
    score=score,
    matched_terms=terms,
    keyword_score=score,
    retrieval_reason=f"关键词命中：{'、'.join(terms[:5])}",
  )


def retrieve_skills_for_job(
  job: JobInfo,
  limit: int = 8,
  library: list[dict[str, Any]] | None = None,
) -> list[RetrievedSkill]:
  text = build_job_skill_query(job)
  text_lower = text.lower()
  cards = library if library is not None else load_skill_library()
  return search_skill_library(
    query=text,
    limit=limit,
    library=cards,
    mode="hybrid",
  )


def search_skill_library(
  query: str = "",
  category: str = "",
  limit: int = 50,
  library: list[dict[str, Any]] | None = None,
  mode: str = "keyword",
) -> list[RetrievedSkill]:
  cards = library if library is not None else load_skill_library()
  category = clean_text(category)
  if category:
    cards = [card for card in cards if str(card.get("category", "")) == category]

  query = clean_text(query)
  if not query:
    return [
      RetrievedSkill(card=card, score=0, matched_terms=[], retrieval_reason="浏览全部技能")
      for card in cards[:limit]
    ]

  text_lower = query.lower()
  ranked_by_id: dict[str, RetrievedSkill] = {}
  if mode in {"keyword", "hybrid"}:
    for card in cards:
      match = _score_card(text_lower, card)
      if match is not None:
        ranked_by_id[str(card.get("id", ""))] = match

    # Also search interview questions and project suggestions for browsing mode.
    query_terms = [
      term
      for term in re.split(r"[\s,，、/]+", query)
      if len(clean_text(term)) >= 2
    ]
    for card in cards:
      card_id = str(card.get("id", ""))
      extra_text = " ".join([
        str(card.get("name", "")),
        str(card.get("category", "")),
        " ".join(str(item) for item in card.get("aliases", [])),
        " ".join(str(item) for item in card.get("jd_phrases", [])),
        " ".join(str(item) for item in card.get("resume_evidence_patterns", [])),
        " ".join(str(item) for item in card.get("project_suggestions", [])),
        " ".join(str(item.get("question", "")) for item in card.get("interview_questions", [])),
      ])
      extra_lower = extra_text.lower()
      matched_terms = [
        term
        for term in query_terms
        if _contains_term(extra_lower, term)
      ]
      if query.lower() in extra_lower:
        matched_terms.append(query)
      if matched_terms:
        existing = ranked_by_id.get(card_id)
        if existing:
          existing.score += len(matched_terms) * 3
          existing.keyword_score += len(matched_terms) * 3
          existing.matched_terms = list(dict.fromkeys([*existing.matched_terms, *matched_terms]))
          existing.retrieval_reason = f"关键词命中：{'、'.join(existing.matched_terms[:5])}"
        else:
          terms = list(dict.fromkeys(matched_terms))
          score = len(terms) * 3
          ranked_by_id[card_id] = RetrievedSkill(
            card=card,
            score=score,
            matched_terms=terms,
            keyword_score=score,
            retrieval_reason=f"关键词命中：{'、'.join(terms[:5])}",
          )

  if mode in {"vector", "hybrid"}:
    try:
      from src.services.skill_vector_store import search_skill_vectors

      card_by_id = {str(card.get("id", "")): card for card in cards}
      vector_hits = search_skill_vectors(query, limit=max(limit, 20))
      for hit in vector_hits:
        card = card_by_id.get(hit.skill_id)
        if not card:
          continue
        vector_points = int(round(hit.score * 20))
        existing = ranked_by_id.get(hit.skill_id)
        if existing:
          existing.vector_score = hit.score
          existing.score += vector_points
          existing.retrieval_reason = f"混合命中：{existing.retrieval_reason}；{hit.reason}"
        else:
          ranked_by_id[hit.skill_id] = RetrievedSkill(
            card=card,
            score=vector_points,
            matched_terms=[],
            keyword_score=0,
            vector_score=hit.score,
            retrieval_reason=hit.reason,
          )
    except Exception:
      if mode == "vector":
        return []

  ranked = list(ranked_by_id.values())
  ranked.sort(key=lambda item: (item.score, item.vector_score, len(item.matched_terms)), reverse=True)
  return ranked[:limit]


def skill_categories(library: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
  cards = library if library is not None else load_skill_library()
  counts: dict[str, int] = {}
  for card in cards:
    category = str(card.get("category", "未分类"))
    counts[category] = counts.get(category, 0) + 1
  return [
    {"name": name, "count": count}
    for name, count in sorted(counts.items(), key=lambda item: item[0])
  ]
