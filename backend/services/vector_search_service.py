"""Vector search over data/embeddings.db using a pre-loaded BGE model."""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from backend.config import BASE

logger = logging.getLogger(__name__)

EMBEDDINGS_DB = BASE / "data" / "embeddings.db"
MODEL_NAME = "BAAI/bge-small-en-v1.5"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

_model: SentenceTransformer | None = None
_ids: np.ndarray | None = None
_matrix: np.ndarray | None = None
_meta: dict[int, dict] | None = None


def load() -> None:
    """Load the BGE model and the full embedding matrix into memory."""
    global _model, _ids, _matrix, _meta
    _model = SentenceTransformer(MODEL_NAME)

    conn = sqlite3.connect(str(EMBEDDINGS_DB))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, act, section, section_title, embedding_text, embedding FROM embeddings"
        ).fetchall()
    finally:
        conn.close()

    ids = np.empty(len(rows), dtype=np.int64)
    vecs = np.empty((len(rows), 384), dtype=np.float32)
    meta = {}
    for i, row in enumerate(rows):
        ids[i] = row["id"]
        vecs[i] = np.frombuffer(row["embedding"], dtype=np.float32)
        meta[row["id"]] = {
            "act": row["act"],
            "section": row["section"],
            "section_title": row["section_title"],
            "embedding_text": row["embedding_text"],
        }

    _ids, _matrix, _meta = ids, vecs, meta
    logger.info(f"Vector search loaded: {len(rows)} embeddings")


def _ensure_loaded() -> None:
    if _model is None:
        load()


def get_cross_references(embedding_id: int) -> list[dict]:
    conn = sqlite3.connect(str(EMBEDDINGS_DB))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT ref_type, ref_text, ref_target FROM cross_references WHERE embedding_id = ?",
            (embedding_id,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def search(query: str, limit: int = 50) -> list[dict]:
    """Embed the query and return the top-K nearest chunks by cosine similarity."""
    _ensure_loaded()
    query_vec = _model.encode(QUERY_PREFIX + query, normalize_embeddings=True).astype(np.float32)
    scores = _matrix @ query_vec
    top_idx = np.argsort(-scores)[:limit]

    results = []
    for idx in top_idx:
        emb_id = int(_ids[idx])
        m = _meta[emb_id]
        results.append({
            "embedding_id": emb_id,
            "act": m["act"],
            "section": m["section"],
            "title": m["section_title"],
            "score": float(scores[idx]),
            "snippet": m["embedding_text"][:300],
        })
    return results
