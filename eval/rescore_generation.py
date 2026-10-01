"""Tính lại correct_numbers_rate (và "ok" theo nhóm) từ predictions.jsonl đã
có sẵn, dùng matcher số mới (bắt thêm số có đơn vị km/h, tuổi, mét, điểm GPLX
-- không chỉ số tiền). KHÔNG gọi lại LLM/API -- chỉ xử lý lại text đã lưu,
nên không tốn tiền và không đổi câu trả lời thật của model.

Ghi ra thư mục mới (hậu tố _v2metric), giữ nguyên thư mục cũ để đối chiếu
trước/sau -- không ghi đè kết quả gốc.

Chạy: .venv/Scripts/python eval/rescore_generation.py eval/results/generation_test_hybrid
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_generation import (
    numbers_covered,
)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        print("Dùng: eval/rescore_generation.py <thư_mục_kết_quả_cũ>")
        return 1
    in_dir = Path(sys.argv[1])
    predictions = [
        json.loads(line)
        for line in (in_dir / "predictions.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]

    n_changed = 0
    for p in predictions:
        if not p["answerable"]:
            continue
        old = p["correct_numbers"]
        new = numbers_covered(p["gold_answer"], p["answer"])
        if old != new:
            n_changed += 1
        p["correct_numbers"] = new

    answerable = [p for p in predictions if p["answerable"]]

    def rate(preds: list[dict], key: str) -> float | None:
        vals = [p[key] for p in preds if p[key] is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    old_metrics = json.loads((in_dir / "metrics.json").read_text(encoding="utf-8"))
    metrics = dict(old_metrics)
    metrics["correct_numbers_rate"] = rate(answerable, "correct_numbers")
    metrics["rescore_note"] = (
        f"correct_numbers tính lại bằng matcher bắt thêm số có đơn vị "
        f"(km/h, tuổi, mét, điểm...), không chỉ số tiền -- xem eval/rescore_generation.py. "
        f"{n_changed}/{len(answerable)} câu đổi kết quả correct_numbers so với "
        f"{in_dir.name}/metrics.json gốc (correct_numbers_rate cũ: "
        f"{old_metrics.get('correct_numbers_rate')})."
    )

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

    out_dir = in_dir.parent / f"{in_dir.name}_v2metric"
    out_dir.mkdir(parents=True, exist_ok=True)
    config = json.loads((in_dir / "config.json").read_text(encoding="utf-8"))
    config["rescored_from"] = str(in_dir)
    (out_dir / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (out_dir / "predictions.jsonl").open("w", encoding="utf-8") as f:
        for p in predictions:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(
        f"correct_numbers_rate: {old_metrics.get('correct_numbers_rate')} -> {metrics['correct_numbers_rate']}"
    )
    print(f"{n_changed}/{len(answerable)} câu đổi kết quả")
    print(f"đã ghi {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
