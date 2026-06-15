from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.core.config import VECTOR_STORE_DIR, configure_local_model_cache
from src.services.embedding_provider import DEFAULT_EMBEDDING_MODEL, embed_texts
from src.services.skill_retriever import load_skill_library
from src.services.text_utils import clean_text


COLLECTION_NAME = "skill_library"
SKILL_VECTOR_DIR = VECTOR_STORE_DIR / "skills_chroma"


@dataclass
class VectorSearchHit:
  skill_id: str
  score: float
  distance: float
  reason: str


def build_skill_document(card: dict[str, Any]) -> str:
  question_text = " ".join(
    f"{item.get('level', '')} {item.get('question', '')} {' '.join(item.get('answer_points', []))}"
    for item in card.get("interview_questions", [])
  )
  parts = [
    card.get("name", ""),
    card.get("category", ""),
    card.get("definition", ""),
    " ".join(str(item) for item in card.get("aliases", [])),
    " ".join(str(item) for item in card.get("jd_phrases", [])),
    " ".join(str(item) for item in card.get("resume_evidence_patterns", [])),
    " ".join(str(item) for item in card.get("project_suggestions", [])),
    question_text,
  ]
  return clean_text(" ".join(str(part) for part in parts if part))


def _import_chromadb():
  configure_local_model_cache()
  try:
    import chromadb
  except ImportError as exc:
    raise RuntimeError("缺少 chromadb 依赖。请先安装依赖后再构建本地向量索引。") from exc
  return chromadb


def _client():
  chromadb = _import_chromadb()
  SKILL_VECTOR_DIR.mkdir(parents=True, exist_ok=True)
  return chromadb.PersistentClient(path=str(SKILL_VECTOR_DIR))


def _collection(create: bool = False):
  client = _client()
  if create:
    return client.get_or_create_collection(
      name=COLLECTION_NAME,
      metadata={"hnsw:space": "cosine"},
    )
  return client.get_collection(name=COLLECTION_NAME)


def vector_store_status() -> dict[str, Any]:
  try:
    collection = _collection(create=False)
    count = collection.count()
    ready = count > 0
    message = "本地向量索引已就绪" if ready else "本地向量索引为空"
  except Exception as exc:
    count = 0
    ready = False
    message = f"本地向量索引未就绪：{exc}"
  return {
    "ready": ready,
    "count": count,
    "path": str(SKILL_VECTOR_DIR),
    "model": DEFAULT_EMBEDDING_MODEL,
    "message": message,
  }


def rebuild_skill_vector_index(library: list[dict[str, Any]] | None = None) -> dict[str, Any]:
  cards = library if library is not None else load_skill_library()
  if not cards:
    return {
      "ready": False,
      "count": 0,
      "path": str(SKILL_VECTOR_DIR),
      "model": DEFAULT_EMBEDDING_MODEL,
      "message": "技能库为空，无法构建向量索引。",
    }

  client = _client()
  try:
    client.delete_collection(COLLECTION_NAME)
  except Exception:
    pass

  collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"},
  )
  ids = [str(card.get("id", "")) for card in cards]
  documents = [build_skill_document(card) for card in cards]
  embeddings = embed_texts(documents)
  metadatas = [
    {
      "name": str(card.get("name", "")),
      "category": str(card.get("category", "")),
    }
    for card in cards
  ]
  collection.add(
    ids=ids,
    documents=documents,
    embeddings=embeddings,
    metadatas=metadatas,
  )
  return {
    "ready": True,
    "count": len(cards),
    "path": str(SKILL_VECTOR_DIR),
    "model": DEFAULT_EMBEDDING_MODEL,
    "message": f"已构建 {len(cards)} 条技能向量索引。",
  }


def search_skill_vectors(query: str, limit: int = 20) -> list[VectorSearchHit]:
  query = clean_text(query)
  if not query:
    return []
  collection = _collection(create=False)
  query_embedding = embed_texts([query])[0]
  results = collection.query(
    query_embeddings=[query_embedding],
    n_results=max(1, min(limit, 100)),
    include=["distances", "documents"],
  )
  ids = results.get("ids", [[]])[0]
  distances = results.get("distances", [[]])[0]
  documents = results.get("documents", [[]])[0]
  hits: list[VectorSearchHit] = []
  for skill_id, distance, document in zip(ids, distances, documents):
    distance_value = float(distance)
    score = max(0.0, 1.0 - distance_value)
    hits.append(VectorSearchHit(
      skill_id=str(skill_id),
      score=score,
      distance=distance_value,
      reason=f"语义相似度 {score:.2f}：{clean_text(str(document))[:60]}",
    ))
  return hits
