"""OCR một PDF scan bằng mô hình thị giác của OpenAI, từng trang một.

Kết quả chỉ là bản nháp: mọi con số (mức phạt, điểm trừ, số khoản/điểm) phải được
đối chiếu tay với ảnh trang trước khi đưa vào corpus.

Ví dụ:
  .venv/Scripts/python src/ingest/ocr_pdf.py --list-models
  .venv/Scripts/python src/ingest/ocr_pdf.py data/raw/nd238.pdf --model <model-id> --out data/processed/ocr/nd238
"""

import argparse
import base64
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import pymupdf
from dotenv import load_dotenv
from openai import OpenAI

PROMPT = (
    "Đây là ảnh một trang văn bản pháp luật tiếng Việt. Hãy chép lại NGUYÊN VĂN toàn bộ chữ trên trang.\n"
    "- Giữ đầy đủ dấu tiếng Việt, đúng từng ký tự. Không sửa lỗi, không diễn đạt lại, không tóm tắt, không thêm chú thích.\n"
    "- Giữ nguyên số thứ tự (Điều, khoản 1., 2., điểm a), b), đ)...), dấu ngoặc kép và các số tiền (ví dụ 12.000.000).\n"
    "- Mỗi đoạn một dòng; không xuống dòng theo chiều rộng trang.\n"
    "- Bỏ qua số trang ở đầu hoặc cuối trang.\n"
    "- Chỗ không đọc chắc chắn thì ghi [?] thay vì đoán.\n"
    "Chỉ trả về văn bản đã chép, không thêm lời dẫn."
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def list_models(client: OpenAI) -> None:
    for m in sorted(client.models.list(), key=lambda m: m.id):
        print(m.id)


def ocr_page(client: OpenAI, model: str, png: bytes) -> tuple[str, dict]:
    b64 = base64.b64encode(png).decode()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{b64}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
    )
    usage = resp.usage.model_dump() if resp.usage else {}
    return (resp.choices[0].message.content or "").strip(), usage


def main() -> int:
    # Console Windows mặc định cp1252 không in được tiếng Việt
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("pdf", nargs="?", type=Path)
    ap.add_argument("--model", help="ID model có khả năng đọc ảnh")
    ap.add_argument("--out", type=Path, help="thư mục ghi kết quả")
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--pages", help="ví dụ 1-3,7 (mặc định: tất cả)")
    ap.add_argument(
        "--force", action="store_true", help="chạy lại cả trang đã có kết quả"
    )
    ap.add_argument("--list-models", action="store_true")
    args = ap.parse_args()

    load_dotenv()  # đọc OPENAI_API_KEY từ .env hoặc biến môi trường, không in ra
    client = OpenAI()

    if args.list_models:
        list_models(client)
        return 0
    if not (args.pdf and args.model and args.out):
        ap.error("cần pdf, --model và --out")

    doc = pymupdf.open(args.pdf)
    wanted = set(range(1, len(doc) + 1))
    if args.pages:
        wanted = set()
        for part in args.pages.split(","):
            a, _, b = part.partition("-")
            wanted.update(range(int(a), int(b or a) + 1))

    pages_dir = args.out / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    meta_path = args.out / "meta.json"
    meta = (
        json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    )
    meta.update(
        {
            "pdf": str(args.pdf),
            "pdf_sha256": sha256(args.pdf),
            "model": args.model,
            "dpi": args.dpi,
            "prompt": PROMPT,
            "updated": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        }
    )
    meta.setdefault("pages", {})

    for i, page in enumerate(doc, start=1):
        if i not in wanted:
            continue
        txt_path = pages_dir / f"p{i:02d}.txt"
        if txt_path.exists() and not args.force:
            print(f"trang {i}: đã có, bỏ qua")
            continue
        png = page.get_pixmap(dpi=args.dpi).tobytes("png")
        (pages_dir / f"p{i:02d}.png").write_bytes(png)
        text, usage = ocr_page(client, args.model, png)
        txt_path.write_text(text + "\n", encoding="utf-8")
        meta["pages"][str(i)] = {"chars": len(text), "usage": usage}
        meta_path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"trang {i}: {len(text)} ký tự", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
