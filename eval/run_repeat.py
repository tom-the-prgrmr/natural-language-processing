"""Chạy lặp một câu hỏi N lần, phân loại từng lần theo bộ kiểm tra trích dẫn.

Dùng để đo những lỗi hiếm/không tất định mà tập dev/test không bắt được (vd
model trả lời bằng trí nhớ riêng rồi gắn một trích dẫn có thật nhưng không
liên quan). Mỗi lần gọi API thật.

Phân loại (dựa trên output thô của model, trước hậu xử lý):
- model_refused: model tự từ chối / hỏi lại
- blocked_hallucinated_id: trích id không có trong ngữ cảnh (chặn từ trước)
- blocked_ungrounded_amount: id hợp lệ nhưng số tiền không có trong chunk được
  trích (chỉ bộ kiểm tra mức nội dung mới chặn được, xem experiments/006)
- answered: được hiển thị cho người dùng

Chạy: .venv/Scripts/python eval/run_repeat.py "Xe máy vượt đèn đỏ phạt bao nhiêu?" --n 10 --tag den_do
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.generation import _client, answer
from src.retrieval import Retriever


def classify(r) -> str:
    if r.hallucinated_citations:
        return "blocked_hallucinated_id"
    if r.ungrounded_amounts:
        return "blocked_ungrounded_amount"
    if r.refused or r.needs_clarification:
        return "model_refused"
    return "answered"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--mode", default="hybrid", choices=["dense", "hybrid"])
    ap.add_argument(
        "--no-expand",
        dest="expand",
        action="store_false",
        help="tắt mở rộng truy vấn văn nói -> thuật ngữ luật (baseline trước 007)",
    )
    args = ap.parse_args()

    retriever = Retriever(mode=args.mode, expand=args.expand)
    client = _client()
    runs = []
    for i in range(args.n):
        r = answer(args.question, retriever=retriever, client=client)
        kind = classify(r)
        runs.append(
            {
                "run": i + 1,
                "kind": kind,
                "raw_answer": r.raw.get("answer"),
                "raw_citations": r.raw.get("citations"),
                "hallucinated_citations": r.hallucinated_citations,
                "ungrounded_amounts": r.ungrounded_amounts,
                "final_refused": r.refused,
                "final_answer": r.answer,
                "retrieved_ids": r.retrieved_ids,
            }
        )
        print(f"  lần {i + 1}: {kind} | {str(r.raw.get('answer'))[:90]}")

    summary = {
        "question": args.question,
        "n": args.n,
        "retrieval_mode": args.mode,
        "query_expansion": args.expand,
        "counts": dict(Counter(r["kind"] for r in runs)),
    }
    out_dir = Path(f"eval/results/repeat_{args.tag}")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (out_dir / "runs.jsonl").open("w", encoding="utf-8") as f:
        for r in runs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"đã ghi {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
