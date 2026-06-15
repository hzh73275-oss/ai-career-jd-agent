from __future__ import annotations

from functools import lru_cache

from src.core.config import configure_local_model_cache


DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"


@lru_cache(maxsize=1)
def get_local_embedding_model(model_name: str = DEFAULT_EMBEDDING_MODEL):
  configure_local_model_cache()
  try:
    from sentence_transformers import SentenceTransformer
  except ImportError as exc:
    raise RuntimeError(
      "缺少 sentence-transformers 依赖。请先安装依赖后再构建本地向量索引。"
    ) from exc
  return SentenceTransformer(model_name)


def embed_texts(texts: list[str], model_name: str = DEFAULT_EMBEDDING_MODEL) -> list[list[float]]:
  model = get_local_embedding_model(model_name)
  embeddings = model.encode(
    texts,
    normalize_embeddings=True,
    show_progress_bar=False,
  )
  return embeddings.tolist()
