"""Dense retrieval bằng embedding API OpenAI + cosine similarity numpy.

Không dùng vector database (corpus ~2200 chunk, đủ nhỏ để giữ trong RAM và
tính cosine trực tiếp) và không dùng BM25/hybrid (cắt phạm vi, xem docs/plan.md).

Cache embedding của corpus ra data/processed/embeddings.npz để không phải gọi
lại API mỗi lần chạy (chỉ gọi lại khi chunks.jsonl đổi, kiểm bằng số lượng +
hash nội dung nhẹ).
"""

import hashlib
import json
import os
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

CHUNKS_PATH = Path("data/processed/chunks.jsonl")
EMB_PATH = Path("data/processed/embeddings.npz")
EMBED_MODEL = "text-embedding-3-small"


def _client() -> OpenAI:
    load_dotenv()
    return OpenAI()


def load_chunks() -> list[dict]:
    return [
        json.loads(line)
        for line in CHUNKS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _content_hash(chunks: list[dict]) -> str:
    h = hashlib.sha256()
    for c in chunks:
        h.update(c["id"].encode("utf-8"))
        h.update(c["text"].encode("utf-8"))
    return h.hexdigest()


def embed_texts(client: OpenAI, texts: list[str], batch_size: int = 100) -> np.ndarray:
    vecs: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        resp = client.embeddings.create(model=EMBED_MODEL, input=batch)
        vecs.extend(d.embedding for d in resp.data)
    return np.array(vecs, dtype=np.float32)


def build_or_load_index(force: bool = False) -> tuple[list[dict], np.ndarray]:
    chunks = load_chunks()
    digest = _content_hash(chunks)
    if not force and EMB_PATH.exists():
        cached = np.load(EMB_PATH, allow_pickle=True)
        if str(cached["digest"]) == digest and len(cached["ids"]) == len(chunks):
            order = {cid: i for i, cid in enumerate(cached["ids"])}
            vecs = cached["vecs"]
            # sắp lại theo thứ tự chunks hiện tại (đề phòng thứ tự đổi)
            idx = [order[c["id"]] for c in chunks]
            return chunks, vecs[idx]
    client = _client()
    vecs = embed_texts(client, [c["text"] for c in chunks])
    EMB_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        EMB_PATH, ids=np.array([c["id"] for c in chunks]), vecs=vecs, digest=digest
    )
    return chunks, vecs


def cosine_topk(query_vec: np.ndarray, corpus_vecs: np.ndarray, k: int) -> list[int]:
    q = query_vec / (np.linalg.norm(query_vec) + 1e-8)
    c = corpus_vecs / (np.linalg.norm(corpus_vecs, axis=1, keepdims=True) + 1e-8)
    sims = c @ q
    return list(np.argsort(-sims)[:k])


class Retriever:
    """Embed câu hỏi và tìm top-k chunk. Dùng lại corpus đã embed một lần."""

    def __init__(self, force_rebuild: bool = False):
        self.chunks, self.vecs = build_or_load_index(force=force_rebuild)
        self.client = _client()

    def search(self, question: str, k: int = 5) -> list[dict]:
        qvec = embed_texts(self.client, [question])[0]
        idx = cosine_topk(qvec, self.vecs, k)
        return [self.chunks[i] for i in idx]


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    force = "--rebuild" in sys.argv
    chunks, vecs = build_or_load_index(force=force)
    print(f"corpus: {len(chunks)} chunk, vector dim={vecs.shape[1]}")
    print(f"đã lưu {EMB_PATH}" if os.path.exists(EMB_PATH) else "chưa lưu (lỗi?)")
