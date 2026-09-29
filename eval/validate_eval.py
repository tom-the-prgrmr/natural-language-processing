"""Kiểm tra data/eval/{dev,test}.jsonl: schema, gold_chunks tồn tại, không trùng,
đếm theo nhóm. Chạy: .venv/Scripts/python eval/validate_eval.py"""

import json
import sys
from collections import Counter
from pathlib import Path

GROUPS = {
    "muc_phat_truc_tiep",
    "doi_thuong",
    "phu_thuoc_loai_xe",
    "nhieu_dieu_kien",
    "ngoai_pham_vi",
    "bay_loi_thoi",
}
REQUIRED = {
    "id",
    "split",
    "question",
    "group",
    "vehicle",
    "gold_chunks",
    "gold_answer",
    "answerable",
    "as_of",
    "source",
    "verified_by",
}


def load(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    chunk_ids = {
        json.loads(line)["id"]
        for line in Path("data/processed/chunks.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    }
    errors: list[str] = []
    all_ids: set[str] = set()
    all_questions: set[str] = set()
    counts: Counter = Counter()

    for split in ("dev", "test"):
        path = Path(f"data/eval/{split}.jsonl")
        if not path.exists():
            errors.append(f"thiếu file {path}")
            continue
        for item in load(path):
            missing = REQUIRED - item.keys()
            if missing:
                errors.append(f"{item.get('id', '?')}: thiếu trường {missing}")
            if item.get("split") != split:
                errors.append(
                    f"{item.get('id')}: split khai báo '{item.get('split')}' != tên file {split}"
                )
            if item.get("group") not in GROUPS:
                errors.append(f"{item.get('id')}: group lạ '{item.get('group')}'")
            if item.get("answerable") is False and item.get("gold_chunks"):
                errors.append(
                    f"{item.get('id')}: answerable=false nhưng gold_chunks không rỗng"
                )
            if item.get("answerable") is True and not item.get("gold_chunks"):
                errors.append(
                    f"{item.get('id')}: answerable=true nhưng gold_chunks rỗng"
                )
            for cid in item.get("gold_chunks", []):
                if cid not in chunk_ids:
                    errors.append(
                        f"{item.get('id')}: gold_chunk '{cid}' không có trong chunks.jsonl"
                    )
            if item.get("id") in all_ids:
                errors.append(f"id trùng: {item.get('id')}")
            all_ids.add(item.get("id"))
            q = item.get("question", "").strip().lower()
            if q in all_questions:
                errors.append(f"{item.get('id')}: câu hỏi trùng với câu khác")
            all_questions.add(q)
            counts[(split, item.get("group"))] += 1

    print("Đếm theo split/nhóm:")
    for (split, group), n in sorted(counts.items()):
        print(f"  {split:5s} {group:22s} {n}")

    if errors:
        print(f"\n{len(errors)} lỗi:")
        for e in errors:
            print(" -", e)
        return 1
    print("\nOK, không có lỗi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
