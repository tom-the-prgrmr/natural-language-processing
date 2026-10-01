# Chatbot tra cứu mức phạt giao thông đường bộ Việt Nam (RAG)

Mini project cuối module NLP (AI Engineer K08). Hỏi đáp về mức phạt vi phạm
giao thông đường bộ, dựa trên Luật Trật tự an toàn giao thông đường bộ
36/2024/QH15, Nghị định 168/2024/NĐ-CP và Nghị định 238/2026/NĐ-CP (sửa đổi
một số điều của ND168). Trả lời có trích dẫn điều/khoản, từ chối khi câu hỏi
ngoài phạm vi.

**Đây là công cụ tham khảo, không phải tư vấn pháp lý.**

Ý tưởng và ràng buộc đầy đủ: [`docs/00-idea.md`](docs/00-idea.md). Kế hoạch
thực hiện và các việc đã cắt khỏi phạm vi ban đầu:
[`docs/plan.md`](docs/plan.md). Báo cáo (vấn đề, dữ liệu, phương pháp, đánh
giá, phân tích lỗi): [`docs/report.md`](docs/report.md). Sơ đồ kiến trúc và
luồng xử lý end to end: [`docs/architecture.md`](docs/architecture.md). Slide
tóm tắt (mở bằng trình duyệt): [`docs/slides.html`](docs/slides.html).

## Cấu trúc thư mục

```
data/raw/        văn bản gốc, bất biến (nguồn, ngày lấy, hash — xem SOURCES.md)
data/processed/  văn bản đã làm sạch (clean/) + chunk theo điều/khoản/điểm (chunks.jsonl)
data/eval/       tập đánh giá dev.jsonl (16 câu) / test.jsonl (24 câu, đóng băng)
src/ingest/      clean.py (làm sạch HTML->text), chunk.py (chunk theo điều/khoản/điểm),
                 ocr_pdf.py (OCR bản scan ND238 bằng API vision OpenAI)
src/             retrieval.py (embedding + cosine), generation.py (prompt + sinh câu trả lời),
                 app.py (FastAPI)
web/             demo chat tối giản (index.html, gọi /chat)
eval/            run_retrieval.py, run_generation.py, run_api_latency.py, validate_eval.py,
                 results/ (số liệu các lần chạy thật)
experiments/     log thí nghiệm (một biến mỗi lần, có cả kết quả âm tính)
tests/           test_chunk.py
docs/            tài liệu dự án (ý tưởng, kế hoạch, quy ước dữ liệu/eval, báo cáo, checklist)
```

## Cài đặt

Yêu cầu Python 3.11+, khoá API OpenAI (dùng cho embedding + sinh câu trả lời).

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt   # Windows
# source .venv/bin/activate && pip install -r requirements-dev.txt   # Linux/macOS

cp .env.example .env
# Mở .env, điền OPENAI_API_KEY=<khoá thật của bạn>
```

Luôn dùng python của venv dự án (`.venv/Scripts/python` trên Windows,
`.venv/bin/python` trên Linux/macOS); không cài gì vào Python toàn cục.

## Chạy lại toàn bộ từ đầu

Thứ tự: **ingest → index → eval → serve**. `data/raw/` đã có sẵn trong repo
(văn bản gốc + bản OCR nháp ND238) nên không cần chạy lại bước thu thập/OCR.

### 1. Ingest: làm sạch + chunk

```bash
.venv/Scripts/python -m src.ingest.clean   # data/raw/*.html -> data/processed/clean/*.txt
.venv/Scripts/python -m src.ingest.chunk   # -> data/processed/chunks.jsonl (2200 chunk)
```

### 2. Build index (embedding corpus)

Gọi API OpenAI embedding cho toàn bộ 2200 chunk (một lần, có cache):

```bash
.venv/Scripts/python -m src.retrieval          # dùng cache nếu chunks.jsonl không đổi
.venv/Scripts/python -m src.retrieval --rebuild  # ép embed lại từ đầu
```

Kết quả cache ở `data/processed/embeddings.npz` (không commit, quá lớn —
tái tạo bằng lệnh trên).

### 3. Đánh giá

```bash
.venv/Scripts/python eval/validate_eval.py                 # kiểm schema dev/test.jsonl
.venv/Scripts/python eval/run_retrieval.py --split dev --k 12
.venv/Scripts/python eval/run_generation.py --split dev --k 12
```

`--split test` chỉ nên chạy khi đã chốt cấu hình (xem quy tắc "tập test đóng
băng" trong [`CLAUDE.md`](CLAUDE.md)) — test đã được chạy và đóng băng, kết
quả ở `eval/results/retrieval_test/`, `eval/results/generation_test/` (prompt cũ)
và `eval/results/generation_test_v3c_natural_style/` (prompt hiện tại, xem
`experiments/003-...md`).

### 4. Chạy API + demo web

```bash
.venv/Scripts/uvicorn src.app:app --reload --port 8000
```

Mở `http://127.0.0.1:8000/` để dùng demo chat (giữ lịch sử hội thoại phía
trình duyệt, hỏi được nhiều lượt). Gọi trực tiếp API:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Xe máy vượt đèn đỏ phạt bao nhiêu?", "history": []}'
```

Đo latency thật (cần server đang chạy):

```bash
.venv/Scripts/python eval/run_api_latency.py --base-url http://127.0.0.1:8000
```

### 5. Lint, format, test

```bash
.venv/Scripts/ruff check .
.venv/Scripts/ruff format .
.venv/Scripts/pytest
```

## Giới hạn đã biết

- **Retrieval còn yếu** (Recall@5 ~0.23–0.31 trên dev/test): corpus luật tiếng
  Việt ngắn, nhiều thuật ngữ hành chính lặp lại khiến embedding khó phân biệt
  ở cấp điểm/khoản. Đã thử 2 hướng rút gọn text embed, cả hai đều tệ hơn
  baseline (xem `experiments/001-...md`). Bù lại bằng cách tăng k ở bước sinh
  câu trả lời (`experiments/002-...md`).
- **Tập đánh giá 40 câu** phần lớn do LLM soạn nháp, tra trực tiếp
  `chunks.jsonl` để lấy số liệu, **chưa được người dùng duyệt tay toàn bộ**
  (ghi rõ trong trường `verified_by` của từng câu) — cắt phạm vi do thời gian,
  xem `docs/plan.md`.
- **Không có bản hợp nhất ND168 + ND238**: hệ thống chọn văn bản/phiên bản
  theo `effective_date` ở tầng retrieval + prompt tại thời điểm trả lời, không
  dựng văn bản hợp nhất riêng.
- **Không cố định seed/temperature** cho lời gọi LLM sinh câu trả lời, nên có
  nhiễu nhỏ giữa các lần chạy cùng cấu hình.
- README này đã tự chạy thử từng lệnh riêng lẻ trên máy hiện tại; **chưa thử
  trọn vẹn từ venv trống trên một máy sạch hoàn toàn khác**.

## Không được làm (xem đầy đủ ở `CLAUDE.md`)

Không commit `.env`; không sửa `data/raw/` hay `data/eval/test.jsonl` sau khi
đóng băng; không gọi API OpenAI thật trong test (dùng mock).
