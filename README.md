# Chatbot tra cứu mức phạt giao thông đường bộ Việt Nam (RAG)

> [!IMPORTANT]
> ### 🚀 Dùng thử ngay: **[natural-language-processing-2yg6.onrender.com](https://natural-language-processing-2yg6.onrender.com)**
>
> Bản deploy trên Render (gói miễn phí): server ngủ sau ~15 phút không có ai
> truy cập, lần mở đầu tiên có thể mất 30–60 giây để khởi động.

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
src/             retrieval.py (hybrid: embedding + cosine kết hợp BM25, mở rộng truy vấn
                 văn nói -> thuật ngữ luật), generation.py (prompt + sinh câu trả lời +
                 kiểm tra trích dẫn 2 mức), app.py (FastAPI)
web/             demo chat tối giản (index.html, gọi /chat)
eval/            run_retrieval.py, run_generation.py, run_api_latency.py, validate_eval.py,
                 rescore_generation.py, run_repeat.py (chạy lặp 1 câu N lần),
                 results/ (số liệu các lần chạy thật)
experiments/     log thí nghiệm (một biến mỗi lần, có cả kết quả âm tính)
tests/           test_chunk.py, test_retrieval.py, test_generation.py, test_app.py,
                 test_eval_metrics.py
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
băng" trong [`CLAUDE.md`](CLAUDE.md)) — test đã được chạy và đóng băng. Kết
quả cấu hình hiện tại (prompt v3c + retrieval hybrid + mở rộng truy vấn):
`eval/results/retrieval_test_007_expand/` và
`eval/results/generation_test_007_expand/`. Các thư mục khác trong
`eval/results/` là kết quả các cấu hình cũ, giữ lại để đối chiếu (xem
`experiments/`).

Mặc định `--mode hybrid` và có mở rộng truy vấn; thêm `--mode dense` hoặc
`--no-expand` để chạy lại các baseline cũ so sánh.

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

### 5. Deploy lên Render (tuỳ chọn)

Repo có sẵn `render.yaml`. Trên [render.com](https://render.com): **New → Blueprint**,
chọn repo này, nhập `OPENAI_API_KEY` khi được hỏi. Render tự cài phụ thuộc,
dựng sẵn cache embedding lúc build, rồi chạy
`uvicorn src.app:app --host 0.0.0.0 --port $PORT`; mỗi lần push lên `main` sẽ
tự deploy lại.

- **Gói miễn phí tự ngủ sau ~15 phút không có ai dùng**; lần truy cập tiếp
  theo phải chờ server khởi động lại (thường dưới 1 phút). Nếu đang mở trang
  mà câu hỏi chờ quá 8 giây, trang báo "server có thể đang khởi động lại", và
  sau khi có câu trả lời thì xác nhận bằng `uptime_s` của `/health`. Lần mở
  link đầu tiên khi server đang ngủ thì trình duyệt chỉ quay chờ — trang chưa
  tải được nên không tự hiện thông báo được.
- **Giới hạn request** để link công khai không đốt hết tiền API:
  `RATE_LIMIT_PER_MINUTE` (mặc định trong `render.yaml`: 10/phút mỗi IP) và
  `DAILY_REQUEST_LIMIT` (300/ngày toàn hệ thống). Chạy local không đặt biến
  này thì không giới hạn. Nên đặt thêm giới hạn chi tiêu trong trang quản trị
  OpenAI.

### 6. Lint, format, test

```bash
.venv/Scripts/ruff check .
.venv/Scripts/ruff format .
.venv/Scripts/pytest
```

## Giới hạn đã biết

- **Retrieval đã cải thiện nhiều nhưng chưa hoàn hảo**: dense đơn thuần ban
  đầu chỉ đạt Recall@5 0.23 (test); hybrid cosine + BM25 nâng lên 0.73
  (`experiments/004-...md`); mở rộng truy vấn văn nói nâng MRR 0.43 -> 0.61
  (`experiments/007-...md`). Bảng mở rộng chỉ có 5 mục viết tay (xe máy, xe
  hơi, vượt đèn đỏ, rượu bia, bằng lái) — cách nói đời thường khác chưa có
  trong bảng vẫn có thể trượt (vd "con nít" thay vì "trẻ em").
- **Bộ kiểm tra trích dẫn không bắt được ngữ cảnh sai**: hệ thống chặn trích
  dẫn bịa id và số tiền không có trong chunk được trích, nhưng nếu retrieval
  đưa nhầm điều khoản thì câu trả lời sai vẫn "có căn cứ". Trước bước mở rộng
  truy vấn, chính câu mẫu ở mục 4 trả lời sai 6/15 lần theo đúng kiểu này
  (áp mức phạt xe đạp cho xe máy); sau đó đúng 15/15 lần
  (`experiments/006-...md`, `007-...md`).
- **Trích dẫn đôi khi kém chi tiết**: model hay trích cả khoản thay vì đúng
  điểm (vd "Khoản 9, Điều 6" thay vì "Điểm b, khoản 9, Điều 6"); căn cứ vẫn
  đúng nhưng người dùng phải tự tìm điểm trong khoản.
- **Tập đánh giá 40 câu** phần lớn do LLM soạn nháp, tra trực tiếp
  `chunks.jsonl` để lấy số liệu, **chưa được người dùng duyệt tay toàn bộ**
  (ghi rõ trong trường `verified_by` của từng câu) — cắt phạm vi do thời gian,
  xem `docs/plan.md`.
- **Không có bản hợp nhất ND168 + ND238**: hệ thống chọn văn bản/phiên bản
  theo `effective_date` ở tầng retrieval + prompt tại thời điểm trả lời, không
  dựng văn bản hợp nhất riêng.
- **Không cố định seed/temperature** cho lời gọi LLM sinh câu trả lời, nên có
  nhiễu nhỏ giữa các lần chạy cùng cấu hình. **API embedding cũng không tất
  định hoàn toàn**: embed lại cùng corpus cho vector lệch nhẹ ở ~40% chunk
  (lệch tối đa ~0.01), đủ để MRR dao động ~±0.003 giữa hai lần build index;
  Recall@k không đổi.
- **Đã tự chạy lại README từ đầu trên một bản sao sạch** (làm trước các thay
  đổi ở `experiments/006`–`007`; các lệnh không đổi, chỉ đổi code bên trong):
  chỉ gồm đúng các
  file git sẽ đưa lên repo (không `.venv`, không cache `embeddings.npz`),
  venv mới tinh, cài lại từ `requirements-dev.txt`, rồi chạy lần lượt mọi
  lệnh ở trên. Tất cả chạy được: `chunks.jsonl` sinh lại **giống hệt từng
  byte**, build index từ đầu ~17 giây, số liệu eval dev khớp kết quả gốc,
  API/demo/latency/ruff/pytest đều đạt. Chưa kiểm: một máy/hệ điều hành
  khác hẳn (bản sao chạy trên cùng máy Windows, cùng Python 3.11.9, dùng lại
  `.env` sẵn có thay vì tạo mới từ `.env.example`).

## Không được làm (xem đầy đủ ở `CLAUDE.md`)

Không commit `.env`; không sửa `data/raw/` hay `data/eval/test.jsonl` sau khi
đóng băng; không gọi API OpenAI thật trong test (dùng mock).
