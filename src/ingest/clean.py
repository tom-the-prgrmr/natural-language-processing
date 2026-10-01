"""Làm sạch văn bản luật từ data/raw/*.html -> data/processed/clean/*.txt.

Mỗi dòng output là một đoạn (paragraph) đã strip, giữ nguyên thứ tự trong văn bản
gốc. Chỉ xử lý luat36 và nd168 (HTML có text layer đầy đủ). ND238 dùng trực tiếp
text OCR ở data/processed/ocr/nd238/pages/, không qua script này.

Chạy: .venv/Scripts/python src/ingest/clean.py
"""

import html
import re
from pathlib import Path

RAW = Path("data/raw")
OUT = Path("data/processed/clean")

# (tên_luật, file nguồn, dòng bắt đầu (Điều 1.), marker kết thúc nội dung)
SOURCES = [
    ("luat36", "luat36.html", "Điều 1.", "Tham khảo thêm"),
    ("nd168", "nd168.html", "Điều 1.", "Tham khảo thêm"),
]

# Các lỗi khoảng trắng lặp lại do bóc tách link nội tuyến trong HTML gốc.
# Không sửa được mọi trường hợp tách từ giữa chữ (ví dụ "k hi" -> "khi"); đây
# là giới hạn đã biết, ghi trong data/raw/SOURCES.md.
SPACING_FIXES = [
    (re.compile(r"\b([a-zđ]{1,2}) \)"), r"\1)"),  # "b )" -> "b)"
    (re.compile(r"\s+([,;.])"), r"\1"),  # "điểm b , điểm d" -> "điểm b, điểm d"
    (re.compile(r'"\s+([a-zđ]\))'), r'"\1'),  # dấu ngoặc kép dính điểm
    # Số tiền bị thẻ nội tuyến cắt đôi: HTML gốc "40.000.<span>000</span>" ->
    # "40.000. 000". Chỉ ghép khi phía trước đã có một nhóm nghìn để không ghép
    # nhầm "khoản 3. 100...". Phát hiện qua experiments/006.
    (re.compile(r"(\d{1,3}\.\d{3})\.\s+(\d{3})(?!\d)"), r"\1.\2"),
]


def strip_html(raw_html: str) -> list[str]:
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw_html)
    h = re.sub(r"(?i)</(p|div|li|h\d|tr)>|<br\s*/?>", "\n", h)
    text = html.unescape(re.sub(r"<[^>]+>", " ", h))
    text = re.sub(r"[ \t\xa0]+", " ", text)
    return [line.strip() for line in text.split("\n") if line.strip()]


def fix_spacing(line: str) -> str:
    for pattern, repl in SPACING_FIXES:
        line = pattern.sub(repl, line)
    return line


def extract_body(lines: list[str], start_marker: str, end_marker: str) -> list[str]:
    start = next(i for i, line in enumerate(lines) if line.startswith(start_marker))
    end = next(
        (i for i, line in enumerate(lines) if line.startswith(end_marker)), len(lines)
    )
    if end <= start:
        raise ValueError(f"marker kết thúc '{end_marker}' nằm trước marker bắt đầu")
    return [fix_spacing(line) for line in lines[start:end]]


def count_dieu(lines: list[str]) -> list[int]:
    nums = []
    for line in lines:
        m = re.match(r"^Điều\s+(\d+)\.", line)
        if m:
            nums.append(int(m.group(1)))
    return nums


def main() -> int:
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, filename, start_marker, end_marker in SOURCES:
        raw_html = (RAW / filename).read_text(encoding="utf-8")
        lines = strip_html(raw_html)
        body = extract_body(lines, start_marker, end_marker)
        out_path = OUT / f"{name}.txt"
        out_path.write_text("\n".join(body) + "\n", encoding="utf-8")
        nums = count_dieu(body)
        gaps = [n for n in range(nums[0], nums[-1] + 1) if n not in nums]
        print(
            f"{name}: {len(body)} dòng, Điều {nums[0]}-{nums[-1]}"
            f" ({len(nums)} điều), thiếu: {gaps or 'không'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
