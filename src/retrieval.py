"""Dense retrieval bằng embedding API OpenAI + cosine similarity numpy, có thêm
chế độ hybrid (+ BM25) thử nghiệm -- xem experiments/004-hybrid-bm25.md.

Không dùng vector database (corpus ~2200 chunk, đủ nhỏ để giữ trong RAM và
tính cosine trực tiếp).

Cache embedding của corpus ra data/processed/embeddings.npz để không phải gọi
lại API mỗi lần chạy (chỉ gọi lại khi chunks.jsonl đổi, kiểm bằng số lượng +
hash nội dung nhẹ).
"""

import hashlib
import json
import os
import re
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from rank_bm25 import BM25Okapi

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


def cosine_scores(query_vec: np.ndarray, corpus_vecs: np.ndarray) -> np.ndarray:
    q = query_vec / (np.linalg.norm(query_vec) + 1e-8)
    c = corpus_vecs / (np.linalg.norm(corpus_vecs, axis=1, keepdims=True) + 1e-8)
    return c @ q


def cosine_topk(query_vec: np.ndarray, corpus_vecs: np.ndarray, k: int) -> list[int]:
    sims = cosine_scores(query_vec, corpus_vecs)
    return list(np.argsort(-sims)[:k])


_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


# Cách nói đời thường -> thuật ngữ văn bản luật dùng. Lệch từ vựng làm cả
# embedding lẫn BM25 trượt (experiments/006: "xe máy vượt đèn đỏ" lấy nhầm điều
# khoản xe đạp vì luật viết "xe mô tô, xe gắn máy" và "không chấp hành hiệu
# lệnh của đèn tín hiệu giao thông", còn Điều 9 lại có chữ "xe đạp máy").
# Chỉ thiết kế từ câu dev + câu mẫu README + từ đồng nghĩa phổ thông, KHÔNG từ
# cách diễn đạt của câu test (xem experiments/007).
COLLOQUIAL_TO_LEGAL = [
    (re.compile(r"\bxe máy\b"), "xe mô tô, xe gắn máy"),
    (re.compile(r"\bxe hơi\b"), "xe ô tô"),
    (
        re.compile(r"vượt đèn|đèn đỏ|đèn vàng"),
        "không chấp hành hiệu lệnh của đèn tín hiệu giao thông",
    ),
    (
        re.compile(r"rượu|bia|nhậu|\bxỉn\b|\bsay\b"),
        "trong máu hoặc hơi thở có nồng độ cồn",
    ),
    (re.compile(r"bằng lái|tước bằng"), "tước quyền sử dụng giấy phép lái xe"),
]


def expand_query(question: str) -> str:
    """Nối thêm thuật ngữ luật tương ứng với cách nói đời thường trong câu hỏi
    (chỉ cho truy vấn retrieval, LLM vẫn nhận câu hỏi gốc)."""
    q = question.lower()
    extra = [legal for pat, legal in COLLOQUIAL_TO_LEGAL if pat.search(q)]
    return " ".join([question, *dict.fromkeys(extra)])


def _minmax(scores: np.ndarray) -> np.ndarray:
    lo, hi = scores.min(), scores.max()
    if hi - lo < 1e-9:
        return np.zeros_like(scores)
    return (scores - lo) / (hi - lo)


class Retriever:
    """Embed câu hỏi và tìm top-k chunk. Dùng lại corpus đã embed một lần.

    mode="hybrid" (mặc định, chốt sau experiments/004-hybrid-bm25.md): cộng
    điểm cosine (đã chuẩn hoá min-max) với điểm BM25 trên text thô (cũng chuẩn
    hoá min-max), trọng số bằng nhau -- dense một mình nhầm lẫn mạnh giữa các
    Điều có tiêu đề hành chính giống hệt nhau (vd Điều 6/7 với Điều 20/21/32),
    trong khi BM25 bắt được từ khoá đặc trưng (vd "nồng độ cồn", "đỗ xe") hiếm
    khi lặp lại giữa các Điều khác chủ đề.
    mode="dense": chỉ cosine trên embedding (baseline cũ, giữ lại để so sánh).
    expand=True (mặc định, chốt sau experiments/007): nối thuật ngữ luật cho
    cách nói đời thường trước khi tìm (`expand_query`).
    """

    def __init__(
        self, force_rebuild: bool = False, mode: str = "hybrid", expand: bool = True
    ):
        self.mode = mode
        self.expand = expand
        self.chunks, self.vecs = build_or_load_index(force=force_rebuild)
        self.client = _client()
        self._bm25 = (
            BM25Okapi([_tokenize(c["text"]) for c in self.chunks])
            if mode == "hybrid"
            else None
        )

    def search(self, question: str, k: int = 5) -> list[dict]:
        if self.expand:
            question = expand_query(question)
        qvec = embed_texts(self.client, [question])[0]
        if self.mode != "hybrid":
            idx = cosine_topk(qvec, self.vecs, k)
            return [self.chunks[i] for i in idx]

        dense = _minmax(cosine_scores(qvec, self.vecs))
        bm25 = _minmax(np.array(self._bm25.get_scores(_tokenize(question))))
        combined = 0.5 * dense + 0.5 * bm25
        idx = np.argsort(-combined)[:k]
        return [self.chunks[i] for i in idx]


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    force = "--rebuild" in sys.argv
    chunks, vecs = build_or_load_index(force=force)
    print(f"corpus: {len(chunks)} chunk, vector dim={vecs.shape[1]}")
    print(f"đã lưu {EMB_PATH}" if os.path.exists(EMB_PATH) else "chưa lưu (lỗi?)")
