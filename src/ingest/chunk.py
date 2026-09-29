"""Chunk văn bản luật đã làm sạch -> data/processed/chunks.jsonl.

- luat36, nd168: đọc từ data/processed/clean/*.txt (một dòng = một đoạn),
  chunk ở mức khoản (kèm điểm gộp trong text), theo docs/legal-data.md.
- nd238 (Nghị định sửa đổi ND168, còn ảnh scan): đọc trực tiếp từ
  data/processed/ocr/nd238/pages/p*.txt (bản OCR đã đối chiếu tay các số
  liệu quan trọng, xem data/raw/SOURCES.md). Chunk ở mức "Điều của ND238"
  và mục con đánh số bên trong (mỗi mục là một chỉ thị sửa đổi), KHÔNG dựng
  văn bản hợp nhất ND168+ND238 (quyết định cắt phạm vi, xem docs/plan.md).
  Việc chọn ưu tiên bản sửa đổi khi trả lời do prompt sinh câu trả lời xử lý
  ở tầng generation, dựa vào effective_date và amends_dieu.

Chạy: .venv/Scripts/python src/ingest/chunk.py
"""

import json
import re
import sys
from pathlib import Path

CLEAN = Path("data/processed/clean")
OCR_PAGES = Path("data/processed/ocr/nd238/pages")
OUT = Path("data/processed/chunks.jsonl")

DIEU_RE = re.compile(r"^Điều\s+(\d+)\.\s*(.*)$")
KHOAN_RE = re.compile(r"^(\d+[a-zđ]?)\.\s*(.*)$")
DIEM_RE = re.compile(r"^([a-zđ]{1,2}\d?)\)\s*(.*)$")

LAW_META = {
    "L36": {
        "name": "Luật Trật tự, an toàn giao thông đường bộ 36/2024/QH15",
        "effective_date": "2025-01-01",
        "status": "goc",
    },
    "168": {
        "name": "Nghị định 168/2024/NĐ-CP",
        "effective_date": "2025-01-01",
        "status": "goc",
    },
    "238": {
        "name": "Nghị định 238/2026/NĐ-CP (sửa đổi ND168)",
        "effective_date": "2026-08-15",
        "status": "sua_doi",
    },
}


def split_dieu_blocks(lines: list[str]) -> list[tuple[int, str, list[str]]]:
    """Trả về [(so_dieu, tieu_de, [dòng nội dung])]."""
    blocks = []
    cur = None
    for line in lines:
        m = DIEU_RE.match(line)
        if m:
            if cur:
                blocks.append(cur)
            cur = (int(m.group(1)), m.group(2).strip(), [])
        elif cur:
            cur[2].append(line)
    if cur:
        blocks.append(cur)
    return blocks


def chunk_khoan_level(law: str, lines: list[str]) -> list[dict]:
    """luat36 / nd168: chunk mức khoản, gộp các điểm bên trong."""
    chunks = []
    for dieu_num, dieu_title, body in split_dieu_blocks(lines):
        # Nếu Điều không có khoản đánh số (ví dụ Điều chỉ 1 đoạn văn),
        # coi cả Điều là một chunk "khoản 0".
        khoan_items: list[tuple[str, list[str]]] = []
        for line in body:
            m = KHOAN_RE.match(line)
            if m and not DIEM_RE.match(line):
                khoan_items.append((m.group(1), [m.group(2)]))
            elif khoan_items:
                khoan_items[-1][1].append(line)
            else:
                # dòng trước khoản đầu tiên (Điều không mở đầu bằng "1.")
                khoan_items.append(("0", [line]))
        for khoan_no, khoan_lines in khoan_items:
            text = "\n".join(khoan_lines).strip()
            if not text:
                continue
            chunk_id = f"{law}_D{dieu_num}_K{khoan_no}"
            chunks.append(
                {
                    "id": chunk_id,
                    "law": law,
                    "dieu": dieu_num,
                    "dieu_title": dieu_title,
                    "khoan": khoan_no,
                    "diem": None,
                    "text": f"Điều {dieu_num}. {dieu_title}\n{text}",
                    **LAW_META[law],
                }
            )
            # sub-chunk theo điểm, lặp lại câu dẫn của khoản (dòng đầu)
            intro = khoan_lines[0]
            for pl in khoan_lines[1:]:
                dm = DIEM_RE.match(pl)
                if dm:
                    chunks.append(
                        {
                            "id": f"{chunk_id}_{dm.group(1)}",
                            "law": law,
                            "dieu": dieu_num,
                            "dieu_title": dieu_title,
                            "khoan": khoan_no,
                            "diem": dm.group(1),
                            "text": f"Điều {dieu_num}. {dieu_title}\n{intro}\n{pl}",
                            **LAW_META[law],
                        }
                    )
    return chunks


def load_nd238_lines() -> list[str]:
    pages = sorted(OCR_PAGES.glob("p*.txt"))
    lines: list[str] = []
    for p in pages:
        lines.extend(
            line.strip()
            for line in p.read_text(encoding="utf-8").split("\n")
            if line.strip()
        )
    start = next(i for i, line in enumerate(lines) if line.startswith("Điều 1."))
    return lines[start:]


def chunk_nd238(lines: list[str]) -> list[dict]:
    """Chunk theo Điều của ND238 (chỉ thị sửa đổi) + mục con đánh số."""
    chunks = []
    amend_re = re.compile(r"Điều\s+(\d+)\b")
    for dieu_num, dieu_title, body in split_dieu_blocks(lines):
        # Điều X của ND238 sửa "...Điều N" của ND168 -> lấy số Điều cuối cùng
        # nhắc tới trong tiêu đề (ví dụ "một số điểm của khoản 3 Điều 3").
        found = amend_re.findall(dieu_title)
        amends_dieu = int(found[-1]) if found else None
        items: list[tuple[str, list[str]]] = []
        for line in body:
            m2 = KHOAN_RE.match(line)
            if m2 and not DIEM_RE.match(line) and len(m2.group(1)) <= 2:
                items.append((m2.group(1), [m2.group(2)]))
            elif items:
                items[-1][1].append(line)
            else:
                items.append(("0", [line]))
        if not items:
            continue
        for i, (item_no, item_lines) in enumerate(items):
            text = "\n".join(item_lines).strip()
            if not text:
                continue
            chunks.append(
                {
                    "id": f"238_D{dieu_num}_{item_no}",
                    "law": "238",
                    "dieu": dieu_num,
                    "dieu_title": dieu_title,
                    "khoan": item_no,
                    "diem": None,
                    "amends_dieu": amends_dieu,
                    "text": f"Điều {dieu_num} ND238. {dieu_title}\n{text}",
                    **LAW_META["238"],
                }
            )
    return chunks


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    all_chunks: list[dict] = []
    for law, fname in [("L36", "luat36.txt"), ("168", "nd168.txt")]:
        lines = (CLEAN / fname).read_text(encoding="utf-8").split("\n")
        cs = chunk_khoan_level(law, [line for line in lines if line])
        print(f"{law}: {len(cs)} chunk")
        all_chunks.extend(cs)
    nd238_lines = load_nd238_lines()
    cs238 = chunk_nd238(nd238_lines)
    print(f"238: {len(cs238)} chunk")
    all_chunks.extend(cs238)

    empty = [c["id"] for c in all_chunks if not c["text"].strip()]
    dup = len(all_chunks) - len({c["id"] for c in all_chunks})
    print(f"tổng: {len(all_chunks)} chunk, rỗng: {len(empty)}, id trùng: {dup}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"đã ghi {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
