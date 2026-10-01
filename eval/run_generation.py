"""Đánh giá sinh câu trả lời (retrieval top-k + LLM) trên dev hoặc test.

Metric (đơn giản hoá do cắt phạm vi, xem docs/plan.md):
- đúng số liệu: mọi số tiền (và số có đơn vị đặc trưng khác -- km/h, tuổi,
  mét, điểm GPLX...) trong gold_answer có xuất hiện trong answer (so chuỗi
  con, không phải LLM-as-judge). Không tính số Điều/khoản/NĐ -- cái đó đã có
  `citation_ok` kiểm riêng.
- trích dẫn đúng: có ít nhất một gold_chunk nằm trong citations trả về
- từ chối đúng/nhầm: so answerable với refused

Chạy: .venv/Scripts/python eval/run_generation.py --split dev
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.generation import GEN_MODEL, TOP_K, answer
from src.retrieval import EMBED_MODEL, Retriever

MONEY_RE = re.compile(r"\d{1,3}(?:\.\d{3})+")

# Số có đơn vị đặc trưng, không phải tiền -- bản v1 (chỉ MONEY_RE) bỏ sót các
# câu phân biệt bằng ngưỡng khác (vd "vượt quá tốc độ 20-35 km/h"), khiến
# correct_numbers=True ngay cả khi model trả lời/từ chối sai với các câu này
# (gold_answer không có số tiền để so). Bắt thêm nhưng loại trừ số Điều/khoản/
# NĐ/năm (đã có citation_ok kiểm riêng, không phải "số liệu câu trả lời").
# Lưu ý: KHÔNG gộp "điểm" (đơn vị trừ điểm GPLX) vào UNIT_NUM_RE -- cụm trích
# dẫn "khoản 9 điểm b" cũng có số đứng ngay trước chữ "điểm" nhưng là số
# khoản, không phải số điểm bị trừ; phải khớp riêng qua POINT_DEDUCT_RE (yêu
# cầu có chữ "trừ" phía trước) để không nhầm.
UNIT_NUM_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:km/h|miligam|mililít|mg/lít|mg|tuổi|mét|m\b)"
)
POINT_DEDUCT_RE = re.compile(r"trừ\s+(\d+)\s*điểm")


def _num_variants(num: str) -> set[str]:
    """ "04" và "4" nên coi là khớp nhau (model hay bỏ số 0 đệm đầu)."""
    stripped = num.lstrip("0") or "0"
    return {num, stripped}


def load_eval(split: str) -> list[dict]:
    path = Path(f"data/eval/{split}.jsonl")
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _context_covered(gold_answer: str, generated: str, regex: re.Pattern) -> bool:
    """Số có ngữ cảnh (đơn vị/điểm trừ) phải xuất hiện CÙNG ngữ cảnh đó ở
    answer -- không chỉ chữ số đó có mặt ở đâu đó trong text (dễ trùng ngẫu
    nhiên, vd số "4" là một phần của "4.000.000"; đây là lỗi đã bắt được khi
    viết test, sửa bằng cách dùng lại chính regex đã trích xuất để kiểm tra
    answer, thay vì so chuỗi con số trần)."""
    gold_nums = {m.group(1) for m in regex.finditer(gold_answer)}
    if not gold_nums:
        return True
    gen_variants: set[str] = set()
    for m in regex.finditer(generated):
        gen_variants |= _num_variants(m.group(1))
    return all(any(v in gen_variants for v in _num_variants(n)) for n in gold_nums)


def numbers_covered(gold_answer: str, generated: str) -> bool:
    money_required = set(MONEY_RE.findall(gold_answer))
    money_ok = all(n in generated for n in money_required)
    return (
        money_ok
        and _context_covered(gold_answer, generated, UNIT_NUM_RE)
        and _context_covered(gold_answer, generated, POINT_DEDUCT_RE)
    )


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=["dev", "test"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument(
        "--k", type=int, default=TOP_K, help="top-k cho retrieval (ablation)"
    )
    ap.add_argument("--tag", default="", help="hậu tố thư mục kết quả, vd _k12")
    ap.add_argument("--mode", default="hybrid", choices=["dense", "hybrid"])
    ap.add_argument(
        "--no-expand",
        dest="expand",
        action="store_false",
        help="tắt mở rộng truy vấn văn nói -> thuật ngữ luật (baseline trước 007)",
    )
    args = ap.parse_args()

    items = load_eval(args.split)
    if args.limit:
        items = items[: args.limit]
    print(f"{args.split}: {len(items)} câu")

    retriever = Retriever(mode=args.mode, expand=args.expand)
    predictions = []
    for item in items:
        t0 = time.perf_counter()
        r = answer(item["question"], retriever=retriever, k=args.k)
        total_ms = (time.perf_counter() - t0) * 1000

        if item["answerable"]:
            correct_numbers = numbers_covered(item["gold_answer"], r.answer)
            citation_ok = bool(set(r.citations) & set(item["gold_chunks"]))
            refusal_ok = not r.refused  # nên trả lời, không nên từ chối
        else:
            correct_numbers = None
            citation_ok = None
            refusal_ok = r.refused  # nên từ chối

        predictions.append(
            {
                "id": item["id"],
                "group": item["group"],
                "question": item["question"],
                "answerable": item["answerable"],
                "gold_answer": item["gold_answer"],
                "gold_chunks": item["gold_chunks"],
                "answer": r.answer,
                "citations": r.citations,
                "refused": r.refused,
                "needs_clarification": r.needs_clarification,
                "hallucinated_citations": r.hallucinated_citations,
                "ungrounded_amounts": r.ungrounded_amounts,
                "raw_answer": r.raw.get("answer"),
                "raw_refused": r.raw.get("refused"),
                "retrieved_ids": r.retrieved_ids,
                "correct_numbers": correct_numbers,
                "citation_ok": citation_ok,
                "refusal_ok": refusal_ok,
                "retrieval_ms": round(r.retrieval_ms, 1),
                "generation_ms": round(r.generation_ms, 1),
                "total_ms": round(total_ms, 1),
            }
        )
        print(
            f"  {item['id']}: refused={r.refused} correct_numbers={correct_numbers} citation_ok={citation_ok}"
        )

    answerable = [p for p in predictions if p["answerable"]]
    unanswerable = [p for p in predictions if not p["answerable"]]

    def rate(preds, key):
        vals = [p[key] for p in preds if p[key] is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    metrics = {
        "n": len(predictions),
        "n_answerable": len(answerable),
        "n_unanswerable": len(unanswerable),
        "model": GEN_MODEL,
        "embed_model": EMBED_MODEL,
        "top_k": args.k,
        "retrieval_mode": args.mode,
        "query_expansion": args.expand,
        "correct_numbers_rate": rate(answerable, "correct_numbers"),
        "citation_ok_rate": rate(answerable, "citation_ok"),
        "refusal_ok_rate_answerable": rate(answerable, "refusal_ok"),
        "refusal_ok_rate_unanswerable": rate(unanswerable, "refusal_ok"),
        "latency_ms": {
            "retrieval_p50": sorted(p["retrieval_ms"] for p in predictions)[
                len(predictions) // 2
            ],
            "generation_p50": sorted(p["generation_ms"] for p in predictions)[
                len(predictions) // 2
            ],
            "total_p50": sorted(p["total_ms"] for p in predictions)[
                len(predictions) // 2
            ],
            "total_max": max(p["total_ms"] for p in predictions),
        },
    }
    by_group: dict[str, dict] = {}
    for p in predictions:
        g = by_group.setdefault(p["group"], {"n": 0, "ok": 0})
        g["n"] += 1
        is_ok = (
            p["refusal_ok"]
            if not p["answerable"]
            else (p["correct_numbers"] and p["citation_ok"])
        )
        g["ok"] += 1 if is_ok else 0
    metrics["by_group"] = {
        g: {**v, "rate": round(v["ok"] / v["n"], 4)} for g, v in by_group.items()
    }

    out_dir = Path(f"eval/results/generation_{args.split}{args.tag}")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "config.json").write_text(
        json.dumps(
            {
                "split": args.split,
                "model": GEN_MODEL,
                "embed_model": EMBED_MODEL,
                "top_k": args.k,
                "retrieval_mode": args.mode,
                "query_expansion": args.expand,
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
