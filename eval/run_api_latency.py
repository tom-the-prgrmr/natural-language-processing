"""Đo latency thật của endpoint /chat (round-trip HTTP, không phải latency nội
bộ hàm answer()) bằng cách gọi lại các câu hỏi trong dev.jsonl.

Cần server đang chạy (`uvicorn src.app:app`). Không dùng thêm thư viện HTTP
ngoài stdlib (urllib) để không phải thêm phụ thuộc mới.

Chạy: .venv/Scripts/python eval/run_api_latency.py --base-url http://127.0.0.1:8000
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

DEV_PATH = Path("data/eval/dev.jsonl")
OUT_DIR = Path("eval/results/api_latency")


def load_questions(limit: int | None) -> list[str]:
    items = [
        json.loads(line)
        for line in DEV_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    qs = [it["question"] for it in items]
    return qs[:limit] if limit else qs


def call_chat(base_url: str, question: str) -> tuple[float, int]:
    body = json.dumps({"question": question, "history": []}).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp.read()
            status = resp.status
    except urllib.error.HTTPError as e:
        status = e.code
    ms = (time.perf_counter() - t0) * 1000
    return ms, status


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    questions = load_questions(args.limit)
    latencies_ms: list[float] = []
    errors = 0
    for q in questions:
        ms, status = call_chat(args.base_url, q)
        if status != 200:
            errors += 1
            print(f"[{status}] {q[:40]}... -> {ms:.0f}ms (lỗi)")
            continue
        latencies_ms.append(ms)
        print(f"{ms:.0f}ms  {q[:50]}")

    if not latencies_ms:
        print("Không có lần gọi thành công nào, dừng.")
        sys.exit(1)

    arr = np.array(latencies_ms)
    metrics = {
        "n_calls": len(questions),
        "n_ok": len(latencies_ms),
        "n_errors": errors,
        "p50_ms": float(np.percentile(arr, 50)),
        "p90_ms": float(np.percentile(arr, 90)),
        "max_ms": float(arr.max()),
        "min_ms": float(arr.min()),
        "mean_ms": float(arr.mean()),
    }
    print(json.dumps(metrics, ensure_ascii=False, indent=2))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "raw_ms.json").write_text(
        json.dumps(latencies_ms, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
