"""Đánh giá retrieval (dense, embedding API + cosine) trên dev hoặc test.

Chạy: .venv/Scripts/python eval/run_retrieval.py --split dev
Kết quả: eval/results/retrieval_<split>/{config.json,metrics.json,predictions.jsonl}
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.retrieval import EMBED_MODEL, Retriever

K_VALUES = (1, 3, 5)


def load_eval(split: str) -> list[dict]:
    path = Path(f"data/eval/{split}.jsonl")
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def best_rank(retrieved_ids: list[str], gold_chunks: list[str]) -> int | None:
    """Hạng (1-based) của gold_chunk được tìm thấy sớm nhất; None nếu không có."""
    for rank, cid in enumerate(retrieved_ids, start=1):
        if cid in gold_chunks:
            return rank
    return None


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=["dev", "test"])
    ap.add_argument("--k", type=int, default=max(K_VALUES), help="top-k tối đa lấy về")
    ap.add_argument("--mode", default="hybrid", choices=["dense", "hybrid"])
    ap.add_argument(
        "--no-expand",
        dest="expand",
        action="store_false",
        help="tắt mở rộng truy vấn văn nói -> thuật ngữ luật (baseline trước 007)",
    )
    ap.add_argument("--tag", default="", help="hậu tố thư mục kết quả, vd _hybrid")
    args = ap.parse_args()

    items = [i for i in load_eval(args.split) if i["answerable"]]
    print(f"{args.split}: {len(items)} câu answerable=true (bỏ qua câu ngoài phạm vi)")

    retriever = Retriever(mode=args.mode, expand=args.expand)
    predictions = []
    ranks = []
    for item in items:
        results = retriever.search(item["question"], k=args.k)
        retrieved_ids = [c["id"] for c in results]
        rank = best_rank(retrieved_ids, item["gold_chunks"])
        ranks.append(rank)
        predictions.append(
            {
                "id": item["id"],
                "group": item["group"],
                "question": item["question"],
                "gold_chunks": item["gold_chunks"],
                "retrieved": retrieved_ids,
                "rank": rank,
            }
        )

    metrics: dict = {
        "n": len(items),
        "model": EMBED_MODEL,
        "mode": args.mode,
        "expand": args.expand,
    }
    for k in K_VALUES:
        hits = sum(1 for r in ranks if r is not None and r <= k)
        metrics[f"recall@{k}"] = round(hits / len(items), 4) if items else None
    mrr = sum((1 / r) for r in ranks if r is not None) / len(items) if items else None
    metrics["mrr"] = round(mrr, 4) if mrr is not None else None

    by_group: dict[str, list[int | None]] = {}
    for p in predictions:
        by_group.setdefault(p["group"], []).append(p["rank"])
    metrics["by_group"] = {}
    for group, rs in by_group.items():
        n = len(rs)
        metrics["by_group"][group] = {
            "n": n,
            "recall@5": round(sum(1 for r in rs if r is not None and r <= 5) / n, 4),
            "not_found": sum(1 for r in rs if r is None),
        }

    out_dir = Path(f"eval/results/retrieval_{args.split}{args.tag}")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "config.json").write_text(
        json.dumps(
            {
                "split": args.split,
                "k": args.k,
                "model": EMBED_MODEL,
                "mode": args.mode,
                "expand": args.expand,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (out_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (out_dir / "predictions.jsonl").open("w", encoding="utf-8") as f:
        for p in predictions:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"đã ghi {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
