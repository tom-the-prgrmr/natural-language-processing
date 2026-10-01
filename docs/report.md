# Báo cáo: Chatbot tra cứu mức phạt giao thông đường bộ (RAG)

Mini project cuối module NLP, AI Engineer K08. Mã nguồn, cách chạy lại:
[`README.md`](../README.md). Sơ đồ kiến trúc: [`architecture.md`](architecture.md).
Số liệu trong báo cáo này đều lấy từ file kết quả chạy thật trong
`eval/results/` hoặc `experiments/` — không có số nào tự ước lượng.

## 1. Problem statement

**Bài toán:** hỏi đáp (question answering) có trích dẫn trên văn bản pháp
luật tiếng Việt — cụ thể là mức phạt vi phạm giao thông đường bộ theo Luật
36/2024/QH15, Nghị định 168/2024/NĐ-CP và Nghị định 238/2026/NĐ-CP (sửa đổi
một phần ND168, hiệu lực từ 15/08/2026).

**Cho ai dùng:** người dân/tài xế tra cứu nhanh mức phạt cho một hành vi cụ
thể, thay vì đọc nguyên văn nghị định (ND168 dài 55 điều). Đây là công cụ
tham khảo, không thay thế tư vấn pháp lý — giao diện luôn hiển thị lưu ý này và hệ thống
chủ động từ chối khi không đủ căn cứ.

**Vì sao chọn đề tài này:** có nhu cầu thực tế (ND238 sửa đổi mức phạt từ
15/08/2026, nhiều người sẽ tra "luật mới phạt bao nhiêu"), có dữ liệu thật
công khai để kiểm chứng số liệu (không phải bài toán mù mờ nhãn), và đúng
dạng "tìm kiếm ngữ nghĩa trên tài liệu, mở rộng thành chatbot" mà đề bài gợi
ý. Chi tiết cân nhắc: [`00-idea.md`](00-idea.md).

**Đo thành công bằng gì:**
- **Retrieval:** Recall@k, MRR — có tìm đúng điều/khoản liên quan không.
- **Sinh câu trả lời:** tỉ lệ số tiền đúng (`correct_numbers_rate`), tỉ lệ
  trích dẫn đúng chunk vàng (`citation_ok_rate`), tỉ lệ từ chối đúng lúc
  (`refusal_ok_rate`) — vì trả lời sai số tiền hoặc bịa căn cứ pháp lý là lỗi
  nghiêm trọng hơn nhiều so với từ chối một câu khó.
- **Triển khai:** API chạy ổn định, latency đo thật, không đo bằng cảm tính.

Lý do không dùng accuracy/F1 đơn thuần: câu trả lời là văn bản tự do (số tiền
+ giải thích + trích dẫn), không phải nhãn phân loại cố định, nên cần tách
riêng "đúng số liệu" và "đúng căn cứ trích dẫn" thay vì gộp vào một điểm số
duy nhất.

## 2. Data

**Nguồn:** 3 văn bản pháp luật công khai, provenance đầy đủ (URL, SHA-256,
ngày lấy) ở [`data/raw/SOURCES.md`](../data/raw/SOURCES.md):
- Luật 36/2024/QH15 (HTML, Luật Trật tự an toàn giao thông đường bộ)
- Nghị định 168/2024/NĐ-CP (HTML)
- Nghị định 238/2026/NĐ-CP (PDF scan — không có bản HTML công khai tại thời
  điểm thu thập — phải OCR, xem phần Method)

**Tiền xử lý:** `src/ingest/clean.py` bóc HTML, chuẩn hoá khoảng trắng.
`src/ingest/chunk.py` chunk theo đơn vị pháp lý tự nhiên — **Điều → Khoản →
Điểm** — thay vì chunk theo độ dài cố định, vì đơn vị khoản/điểm là đơn vị
ngữ nghĩa nhỏ nhất có thể trích dẫn độc lập. Mỗi chunk con (điểm) lặp lại tiêu
đề Điều + câu dẫn khoản để tự chứa đủ ngữ cảnh khi đứng riêng.

**Số lượng:** 2200 chunk — Luật 36: 887, ND168: 1243, ND238: 70 (xem
`data/processed/chunks.jsonl`, sinh lại được bằng script, không chỉnh tay).
Kiểm tra bằng 5 test tự động (`tests/test_chunk.py`): đếm đúng số điều nguồn
(Luật 36: 1–89, ND168: 1–55), không chunk rỗng/trùng id, 2 chunk biết trước
đáp án khớp đúng nội dung, tỉ lệ khoản đánh số "0" (dấu hiệu lỗi parse) dưới
20%.

**Không dựng văn bản hợp nhất** ND168 + ND238: mỗi chunk giữ nguyên
`effective_date` và `status` (`goc`/`sua_doi`) riêng; việc chọn bản nào áp
dụng được đẩy xuống tầng prompt lúc trả lời (xem Method) — quyết định cắt
phạm vi có ghi trong `docs/plan.md`.

**Tập đánh giá:** 40 câu (dev 16 / test 24), chia theo 6 nhóm lỗi dự kiến,
tỉ trọng gộp cả hai tập: `muc_phat_truc_tiep` 12, `doi_thuong` 8 (văn nói,
viết tắt), `phu_thuoc_loai_xe` 6, `nhieu_dieu_kien` 6 (hình phạt bổ sung: trừ
điểm, tước bằng, tịch thu xe), `ngoai_pham_vi` 4 (`answerable=false`),
`bay_loi_thoi` 4 (luật cũ ND100/2019, hoặc thời điểm trước/sau 15/08/2026).
Schema và quy tắc gán nhãn: [`eval-spec.md`](eval-spec.md). `gold_answer`
tra trực tiếp `chunks.jsonl`, không dùng trí nhớ hay để LLM tự sinh rồi dùng
luôn.

**Mất cân bằng và hạn chế biết trước:** 40 câu là **rút gọn mạnh** từ kế
hoạch ban đầu (~100 câu, có thêm nhóm hội thoại nhiều lượt `nhieu_luot`)
do thời gian — xem `docs/plan.md` phần "Quyết định đã chốt". Phần lớn câu có
`source: llm_draft_reviewed` (LLM soạn nháp, tra số liệu thật từ chunks.jsonl)
**chưa được người dùng duyệt tay từng câu** — tự nhận đây là hạn chế, không
coi 40 câu này là tập đánh giá đã kiểm chứng đầy đủ. Tính năng hội thoại
nhiều lượt (xem Method) được triển khai trong code nhưng **không có bộ eval
tự động riêng** cho đa lượt, chỉ kiểm tra thủ công qua demo.

## 3. Method

**Hướng chọn:** dùng LLM có sẵn qua API (OpenAI) theo kiến trúc RAG, không
fine-tune — vì bài toán cần độ chính xác trích dẫn pháp lý cao và dữ liệu
thay đổi theo thời gian (luật sửa đổi), fine-tune một model nhỏ trên 2200
đoạn ngắn khó đạt độ chính xác số liệu bằng việc bắt LLM lớn đọc đúng ngữ
cảnh truy xuất và trích dẫn.

**Retrieval** (`src/retrieval.py`): hybrid — embed toàn bộ chunk bằng
`text-embedding-3-small` (cache vector vào `embeddings.npz`), kết hợp điểm
cosine similarity với điểm BM25 (`rank-bm25`, thuần CPU, không gọi thêm API)
trên text thô, trọng số bằng nhau sau khi chuẩn hoá min-max, lấy top-k theo
điểm cộng (numpy thuần, không dùng vector DB vì corpus đủ nhỏ để giữ trong
RAM). Ban đầu chỉ dùng dense và chủ định cắt hybrid khỏi phạm vi (xem
`docs/plan.md`), sau đó thêm lại giữa chừng vì xác định được nguyên nhân cụ
thể khiến dense yếu và cải thiện đo được rất lớn — xem mục 5 và
`experiments/004-hybrid-bm25.md`. Không dùng reranker — vẫn cắt phạm vi phần
này.

**Mở rộng truy vấn văn nói** (`expand_query` trong `src/retrieval.py`): trước
khi tìm, nối thêm thuật ngữ luật tương ứng với cách nói đời thường trong câu
hỏi — "xe máy" → "xe mô tô, xe gắn máy", "vượt đèn đỏ" → "không chấp hành
hiệu lệnh của đèn tín hiệu giao thông", "say rượu/nhậu" → "nồng độ cồn"...
(bảng 5 mục). Chỉ áp dụng cho truy vấn retrieval; LLM vẫn nhận câu hỏi gốc.
Thêm vào sau khi phát hiện chính câu ví dụ trong README bị trả lời sai do lệch
từ vựng — xem mục 5 và `experiments/007-mo-rong-truy-van-van-noi.md`.

**Sinh câu trả lời** (`src/generation.py`): `gpt-5.4-mini`, `response_format
= json_object` để ép output có cấu trúc (`answer`, `citations`, `refused`,
`needs_clarification`, `clarify_question`). System prompt (nguyên văn trong
code) bắt buộc:
1. Chỉ dùng ngữ cảnh được truyền vào, không dùng kiến thức ngoài.
2. Từ chối (`refused=true`) khi ngữ cảnh không đủ, thay vì đoán.
3. Hỏi lại (`needs_clarification=true`) khi thiếu loại xe (ô tô/xe máy —
   hai khung phạt khác nhau nhiều) thay vì giả định.
4. Khi có cả bản gốc ND168 và bản sửa ND238 cho cùng hành vi, chọn theo
   `effective_date` so với ngày hiện tại (hoặc ngày câu hỏi nêu).
5. Mọi mức phạt phải kèm `citations` (id chunk thực sự dùng).

**Hội thoại nhiều lượt:** không tách một bước "viết lại câu hỏi" bằng LLM
riêng (để tiết kiệm một lượt gọi API và độ trễ) — câu truy vấn dùng cho
retrieval là nối các lượt hỏi trước của người dùng với câu hỏi hiện tại
(`_retrieval_query` trong `src/generation.py`). Đơn giản, không hoàn hảo,
nhưng đủ để mang từ khoá ngữ cảnh (vd "xe máy" nhắc ở lượt 1) sang lượt sau
("còn ô tô thì sao?"). Lịch sử hội thoại đầy đủ vẫn được đưa vào prompt LLM
ở bước sinh câu trả lời.

**OCR cho ND238:** văn bản chỉ có ở dạng PDF scan ảnh (không chọn được text).
Thử RapidOCR (local, miễn phí) trước — kết quả làm mất dấu tiếng Việt (vd
"Phạt tiền" → "Phat tien"), không dùng được. Chuyển sang gọi model có khả
năng đọc ảnh của OpenAI (`gpt-5.4`) qua `src/ingest/ocr_pdf.py`, cho kết quả
giữ đúng dấu. Đánh đổi: tốn phí API, và bản OCR có đối chiếu thủ công một
phần, ghi rõ trạng thái "đã/chưa đối chiếu" trong `docs/legal-data.md`.

**Tham số đã chốt** (và lý do): embedding + sinh câu trả lời đều qua API
OpenAI (bỏ phương án tự host local — không đủ thời gian so sánh có ý nghĩa
trên GPU 4GB VRAM của máy phát triển); `top_k=12` cho bước sinh câu trả lời
(chốt sau thí nghiệm, xem mục 5).

## 4. Evaluation và phân tích lỗi

### Retrieval

| Split | n (answerable) | Mode | Recall@1 | Recall@3 | Recall@5 | MRR |
|---|---|---|---|---|---|---|
| dev | 13 | dense (baseline) | 0.0769 | 0.1538 | 0.3077 | 0.1682 |
| dev | 13 | hybrid | 0.2308 | 0.4615 | 0.5385 | 0.3817 |
| test | 22 | dense (baseline) | 0.0909 | 0.2273 | 0.2273 | 0.1591 |
| test | 22 | hybrid | 0.2727 | 0.5000 | 0.7273 | 0.4289 |
| dev | 13 | **hybrid + mở rộng truy vấn (chốt)** | **0.3846** | **0.7692** | **0.8462** | **0.5911** |
| test | 22 | **hybrid + mở rộng truy vấn (chốt)** | **0.4545** | **0.7273** | **0.7727** | **0.6134** |

(`eval/results/retrieval_{dev,test}/` = dense;
`eval/results/retrieval_{dev,test}_hybrid/` = hybrid;
`eval/results/retrieval_{dev,test}_007_expand/` = hybrid + mở rộng. Bảng
ánh xạ của bước mở rộng thiết kế từ câu dev nên số dev là kết quả trong mẫu;
số test là thước đo giữ riêng.)

Dense đơn thuần ban đầu **yếu** (Recall@5 ~0.23–0.31). Rà lại
`predictions.jsonl` cho thấy đây không phải vấn đề "gold chunk xếp hạng thấp"
mà là **73% câu test (16/22) hoàn toàn không có gold chunk trong top-12**.
Nguyên nhân cụ thể: các câu hỏi mất đều có gold chunk ở Điều 6/Điều 7 (mức
phạt ô tô/xe máy) nhưng bị lấn át bởi Điều 20/21/32 (ô tô khách/tải/máy kéo)
— các Điều này mở đầu bằng một mẫu câu hành chính rất dài và gần giống hệt
nhau, chỉ khác loại xe, trong khi nội dung hành vi cụ thể (nồng độ cồn, đỗ
xe, lạng lách...) nằm ở phần "điểm" rất ngắn so với phần mở đầu lặp lại.
Thêm điểm BM25 (bắt đúng từ khoá đặc trưng, không bị "pha loãng" bởi phần mở
đầu dài như embedding) kết hợp với cosine đã sửa phần lớn vấn đề này — chi
tiết đầy đủ, kể cả hạn chế còn lại, ở `experiments/004-hybrid-bm25.md`.

Lỗi còn lại sau hybrid chủ yếu là **lệch từ vựng văn nói ↔ văn bản luật**:
"xe máy" (luật: "xe mô tô, xe gắn máy"), "vượt đèn đỏ" (luật: "không chấp
hành hiệu lệnh của đèn tín hiệu giao thông"), "nhậu xỉn" (luật: "nồng độ
cồn"). Tệ nhất, Điều 9 (xe đạp, **xe đạp máy**) trùng chữ "máy" nên BM25 kéo
nhầm điều khoản xe đạp lên cho câu hỏi về xe máy. Mở rộng truy vấn
(`experiments/007`) đẩy MRR test 0.43 → 0.61; câu test duy nhất còn không tìm
thấy (q18 "chở con nít...") dùng đúng cách nói đã cố ý không đưa vào bảng ánh
xạ để tránh rò test.

### Sinh câu trả lời (test, k=12)

Mỗi thay đổi được chốt trên dev rồi chạy test một lần (không chỉnh sau khi
xem số test): prompt văn phong (`003`), retrieval hybrid (`004`), sửa dữ liệu
+ kiểm tra trích dẫn mức nội dung (`006`, không đổi số đáng kể nên không tách
cột riêng), mở rộng truy vấn (`007`). Tất cả các lần chạy đều giữ lại.
`correct_numbers_rate` ở bảng dưới là **số đã sửa** sau khi phát hiện lỗ hổng
trong cách đo (xem `experiments/005-fix-correct-numbers-metric.md`) — tính
lại từ `predictions.jsonl` đã lưu, không gọi lại LLM nên không ảnh hưởng các
chỉ số khác.

| Metric | Prompt cũ, dense | Prompt v3c, dense | v3c, hybrid | v3c, hybrid + mở rộng **(chốt)** |
|---|---|---|---|---|
| correct_numbers_rate (answerable, n=22) | 0.4091 | 0.5000 | 0.7273 | **0.7727** |
| citation_ok_rate — strict (answerable, n=22) | 0.2273 | 0.2727 | 0.6818 | 0.6364 |
| citation_ok — đúng khoản* (chỉ số phụ) | 0.3182 | 0.3182 | 0.8182 | **0.9091** |
| refusal_ok_rate (answerable — nên trả lời) | 0.6364 | 0.5455 | 0.9545 | **0.9545** |
| refusal_ok_rate (unanswerable, n=2 — nên từ chối) | 1.0 | 1.0 | 1.0 | 1.0 |
| latency total p50 / max | 2082ms / 3385ms | 1718ms / 2805ms | 1418ms / 2312ms | 1536ms / 2111ms |

(`eval/results/generation_test_v2metric/`,
`eval/results/generation_test_v3c_natural_style_v2metric/`,
`eval/results/generation_test_hybrid_v2metric/` — bản đã sửa metric theo
`005`; `eval/results/generation_test_007_expand/` — chạy sau khi đã sửa
metric. Thư mục không hậu tố `_v2metric` là số gốc trước khi sửa.)

\* `citation_ok` strict đòi đúng id chunk vàng (cấp điểm). Mọi lần trượt
"cùng khoản" trên test đều là model trích **chunk khoản cha** — chunk này
chứa nguyên văn điểm đúng nên căn cứ vẫn đúng, chỉ kém chi tiết; không lần
nào trích nhầm điểm khác trong cùng khoản. Số lần trích khoản cha tăng dần
theo từng cải tiến retrieval (1 → 3 → 4 → 6 câu), vì BM25 và mở rộng truy
vấn ưu tiên chunk khoản (dài, nhiều từ khoá) — đó là lý do strict đi ngang
dù retrieval tốt lên nhiều. Chỉ số "đúng khoản" chấp nhận trích khoản cha,
tính lại offline cho **mọi** cột để so sánh công bằng; chỉ số chính thức vẫn
là strict (không đổi thước đo ngay sau khi thấy kết quả bất lợi).

Theo nhóm (test, cấu hình chốt, tiêu chí "ok" = đúng số liệu VÀ đúng trích
dẫn **strict** với câu answerable, hoặc từ chối đúng với câu unanswerable):
`muc_phat_truc_tiep` 5/7, `doi_thuong` 2/5, `nhieu_dieu_kien` 1/4,
`phu_thuoc_loai_xe` 2/4, `ngoai_pham_vi` 2/2, `bay_loi_thoi` 1/2 — các nhóm
nhiều điều kiện / so sánh loại xe bị chỉ số strict đánh thấp nhiều nhất vì
model hay trích khoản cha khi câu trả lời gộp nhiều điểm.

**Ví dụ lỗi cụ thể** (so sánh dense → hybrid, từ `predictions.jsonl`):
- *"lạng lách xe hơi lần 2 (tái phạm) bị sao không"* — gold: tịch thu xe
  (Điều 6 khoản 14, áp dụng khi tái phạm khoản 12). Ở dense, retrieval không
  đưa được chunk này vào top-12, model phải từ chối. **Ở hybrid, BM25 bắt
  đúng từ "lạng lách"/"tái phạm", retrieval tìm thấy cả khoản 12 lẫn khoản
  14, model trả lời đúng và trích dẫn đúng cả hai** — một ví dụ cụ thể cho
  thấy hybrid sửa đúng loại lỗi mà nó nhắm tới.
- *"chở con nít ngồi ghế trước xe hơi mà không có ghế an toàn giờ phạt
  chưa"* — gold: `238_D2_1` (khoản 1a Điều 6, **do ND238 bổ sung**, hiệu lực
  15/08/2026). Dense trích dẫn nhầm hẳn sang ND168 gốc (sai văn bản áp dụng).
  Hybrid tìm đúng Điều 2 ND238 nhưng trích `238_D2_2` (lệch một mục con) —
  **cải thiện rõ (đúng văn bản/Điều) nhưng chưa hoàn toàn đúng** (sai mục
  con trong cùng Điều), cho thấy giới hạn còn lại nằm ở độ chính xác cấp
  điểm/khoản chứ không còn ở cấp Điều như trước. Sau `007` câu này vẫn trượt
  ở retrieval — cách nói "con nít" cố ý không đưa vào bảng ánh xạ.
- *"Xe máy vượt đèn đỏ phạt bao nhiêu?"* — chính câu ví dụ trong README, nằm
  ngoài tập eval, phát hiện khi tự chạy lại README trên bản sao sạch. Chạy
  lặp 15 lần (`eval/run_repeat.py`): với hybrid, **0/15 đúng; 6/15 trả lời
  sai mà vẫn qua mọi bộ kiểm tra** — model áp mức phạt xe đạp (Điều 9,
  150–250 nghìn) cho xe máy, trích dẫn có thật và chứa đúng số đó. Sau mở
  rộng truy vấn: **15/15 đúng** (4–6 triệu, điểm c khoản 7 Điều 7), chunk
  đúng xếp hạng 1 cả 15 lần. Ví dụ rõ nhất trong dự án cho thấy một câu trả
  lời "có căn cứ" vẫn có thể sai hoàn toàn nếu retrieval đưa nhầm điều khoản.

**Chỉ số `correct_numbers_rate` từng có lỗ hổng, đã sửa qua 2 vòng
(`experiments/005-fix-correct-numbers-metric.md`):** bản đầu chỉ so khớp
chuỗi số tiền dạng `x.xxx.xxx`; các câu hỏi phân biệt bằng ngưỡng khác (tốc
độ km/h, tuổi, số điểm trừ GPLX...) không có số tiền để so nên mặc định tính
`True` ngay cả khi model trả lời thiếu/sai phần đó. Thêm matcher bắt các đơn
vị này (cẩn thận loại trừ nhầm lẫn với cấu trúc trích dẫn "khoản N điểm X"),
nhưng vòng sửa đầu lại có bug khác (so chuỗi con số trần, bị trùng ngẫu nhiên
với số khác trong câu, vd "4" trùng với một phần của "4.000.000") — bắt được
nhờ viết test trước (`tests/test_eval_metrics.py`), sửa bằng cách kiểm tra số
xuất hiện **đúng ngữ cảnh** (cùng đơn vị) ở answer thay vì chỉ là chuỗi con.
Tính lại từ `predictions.jsonl` đã lưu (không gọi lại LLM): test hybrid
0.8636 → **0.7273** (3/22 câu đổi), test dense (v3c) 0.6364 → **0.5000**
(3/22 câu đổi). Bảng số liệu ở trên đã dùng chỉ số đã sửa (bản cuối). Vẫn là
so khớp theo mẫu cố định (không phải LLM-as-judge), vẫn còn giới hạn với các
cách diễn đạt ngưỡng không theo mẫu đã liệt kê — tự nhận, không báo số đẹp
hơn thực tế.

## 5. Cải tiến (so sánh trước/sau bằng số liệu thật)

Bốn thí nghiệm thật, mỗi lần đổi đúng một biến, log đầy đủ ở `experiments/`:

**`001` — rút gọn text dùng để embed (thất bại, giữ nguyên baseline).**
Giả thuyết: tiêu đề Điều lặp lại ở mọi chunk con làm loãng vector. Thử bỏ
tiêu đề (v1) và bỏ câu dẫn khoản (v2). Kết quả trên dev: v0 (baseline)
Recall@5 = 0.3077, v1 = 0.1538, v2 = 0.2308 — **cả hai đều tệ hơn**. Nhóm
`phu_thuoc_loai_xe` giảm mạnh nhất ở v1 (1.0 → 0.0): tiêu đề Điều 6/Điều 7
hoá ra là nơi duy nhất phân biệt rõ ô tô/xe máy. Giả thuyết bị bác bỏ, giữ
nguyên v0, ghi nhận kết quả âm tính đầy đủ thay vì giấu đi.

**`002` — tăng k đưa vào bước sinh câu trả lời 8→12 (thành công, chốt
k=12).** Giả thuyết: vì retrieval yếu, nhiều gold chunk nằm ở hạng 6–12 thay
vì top-5; truyền nhiều ứng viên hơn cho LLM tự chọn đúng, thay vì bắt
retrieval phải đúng ngay từ đầu. Kết quả trên dev (13 câu answerable):

| k | correct_numbers | citation_ok | refusal_ok (answerable) |
|---|---|---|---|
| 8 | 0.3846 | 0.3077 | 0.6154 |
| 12 | **0.4615** | **0.4615** | **0.6923** |

Cải thiện thật trên cả 3 chỉ số, `refusal_ok` cho câu ngoài phạm vi vẫn giữ
1.0 (không bị "liều" trả lời khi có nhiều ngữ cảnh hơn). Latency không tệ đi
đáng kể (p50 tổng 2077ms ở k=12 so với 2329ms ở k=8 trên dev — thực ra nhanh
hơn, nằm trong biên độ nhiễu giữa các lần gọi LLM). Chốt k=12 làm cấu hình
chính thức.

**`003` — prompt văn phong tự nhiên (giữ).** Câu trả lời cũ chép nguyên câu
chữ điều luật và lặp "không phải tư vấn pháp lý" (8/16 câu dev). Prompt mới:
câu đầu trả lời thẳng, từ đời thường nhưng giữ nguyên số tiền, câu cuối
"Căn cứ: điểm… khoản… Điều…", không lặp câu miễn trừ (giao diện đã có). Trên
dev: câu lặp miễn trừ 8 → 0; `correct_numbers` 0.4615 → 0.5385,
`citation_ok` 0.4615 → 0.6154, `refusal_ok` (answerable) 0.8462 → 0.6154.
Hai chỉ số đầu tăng nhưng nằm trong dao động giữa các lần chạy (~2/13 câu)
nên chỉ kết luận "không giảm". `refusal_ok` giảm vì 3 câu bản cũ trả lời
**sai** (q13, q14, q28) nay chuyển thành từ chối; 5 câu bản cũ đúng hoàn
toàn vẫn đúng.

**`004` — retrieval hybrid BM25+cosine (thành công lớn nhất dự án, chốt làm
mặc định).** Rà lại nguyên nhân Recall@5 thấp thay vì chỉ chấp nhận là giới
hạn: phát hiện 73% câu test gold chunk không lọt top-12 (không phải "xếp
hạng thấp" như giả định khi tăng k ở `002`), tập trung ở các câu bị nhầm giữa
Điều 6/7 và các Điều có tiêu đề hành chính gần giống (20/21/32). Thêm BM25
(thuần CPU, không tốn thêm API) kết hợp cosine: Recall@5 test 0.227→**0.727**,
MRR 0.159→**0.429**; cùng prompt, `correct_numbers` 0.500→**0.727**
(số đã sửa theo `experiments/005`), `citation_ok` 0.273→**0.682**,
`refusal_ok` (answerable) 0.545→**0.955**, latency còn **nhanh hơn**
(p50 1718→1418ms). Chi tiết đầy đủ: `experiments/004-hybrid-bm25.md`.

**`005` — sửa lỗ hổng chỉ số `correct_numbers_rate` (không phải thí nghiệm
đổi model, mà sửa cách đo).** Phát hiện chỉ số này chấm `True` oan cho các
câu hỏi không có số tiền để so (ngưỡng km/h, tuổi, điểm trừ GPLX...). Sửa và
tính lại từ `predictions.jsonl` đã lưu (không gọi lại LLM): các số
`correct_numbers` ở mục 4 đều là số đã sửa. Kết luận `004` không đổi —
hybrid vẫn hơn dense rõ rệt, chỉ số tuyệt đối thấp hơn vì đo chặt hơn. Chi
tiết: `experiments/005-fix-correct-numbers-metric.md`.

**`006` — kiểm tra trích dẫn ở mức nội dung (giữ, nhưng không chạm gốc
lỗi).** Bắt nguồn từ câu ví dụ README: có lần model trả lời bằng trí nhớ
riêng rồi gắn một id có trong ngữ cảnh nhưng không liên quan. Thêm bước:
mọi số tiền trong câu trả lời phải có trong chunk được trích (xem mục 6).
Phân tích phản thực tế trên các câu trả lời đã lưu phát hiện 2 dương tính
giả, dẫn tới **sửa một lỗi dữ liệu tồn tại từ đầu dự án** ("40.000.<span>000"
trong HTML gốc thành "40.000. 000" sau khi làm sạch — vô hình với mọi chỉ số
vì LLM vẫn đọc hiểu) và chấp nhận số suy ra (hiệu/tổng). Sau sửa: 0/32 dương
tính giả, nhưng test lặp 15 lần chỉ chặn thêm 1 lần sai, trong khi 6/15 lần
sai "có căn cứ" vẫn lọt — chỉ ra gốc lỗi ở retrieval. Chi tiết:
`experiments/006-kiem-tra-trich-dan-noi-dung.md`.

**`007` — mở rộng truy vấn văn nói → thuật ngữ luật (thành công, chốt mặc
định).** Bảng 5 ánh xạ thiết kế từ câu dev + câu ví dụ README, cố ý loại các
cách nói chỉ biết qua câu test. Test (giữ riêng): MRR 0.429 → **0.613**,
Recall@1 0.273 → **0.455**, `correct_numbers` 0.727 → **0.773**,
`refusal_ok` 0.909 → **0.955** (so với cấu hình 006); câu ví dụ README 0/15 →
**15/15** đúng. Không thêm độ trễ hay chi phí. Tác dụng phụ: model trích chunk
khoản cha nhiều hơn (kém chi tiết hơn, căn cứ vẫn đúng). Chi tiết:
`experiments/007-mo-rong-truy-van-van-noi.md`.

## 6. Phần tự nghĩ thêm: tự động phát hiện trích dẫn bịa

Yêu cầu "mọi câu trả lời phải kèm trích dẫn" chỉ đảm bảo model *nói* nó có
trích dẫn — không đảm bảo trích dẫn đó *thật* (model vẫn có thể bịa một id
chunk không tồn tại hoặc không nằm trong ngữ cảnh đã đọc, nhất là khi bị ép
trả JSON theo schema). Thêm một bước kiểm tra tự động (`src/generation.py`,
không chỉ ở tầng eval mà nằm trong chính logic sinh câu trả lời, nên có hiệu
lực cả ở API/demo thật): sau khi nhận JSON từ LLM, so từng id trong
`citations` với danh sách id đã thực sự truy xuất (`retrieved_ids`); nếu có
id không khớp, tự động ép `refused=True` thay vì để lọt một câu trả lời
*trông* có căn cứ nhưng thực ra trích dẫn ảo.

Khi thêm tính năng này, test đã chạy lại (lần 2, có kế hoạch từ trước, không
phải vì thấy số xấu rồi sửa): `refusal_ok_rate` (answerable) tăng từ 0.5909
lên 0.6364 — tức phát hiện được một số câu LLM từng trả lời "trông ổn" nhưng
trích dẫn sai. Cả hai lần chạy đều giữ lại, không xoá
(`eval/results/generation_test/` và
`eval/results/generation_test_v1_no_citation_check/`), tuân thủ quy tắc
không bịa/giấu số liệu.

**Mức thứ hai — kiểm tra nội dung (`experiments/006`):** id hợp lệ chưa đủ.
Có lần model trả lời bằng trí nhớ riêng (đúng mức 4–6 triệu ngoài đời) rồi
gắn một id *có* trong ngữ cảnh nhưng là điều khoản nồng độ cồn mức 6–8 triệu
— lọt qua mức id. Bổ sung: mọi số tiền nêu trong câu trả lời phải có trong
nội dung ít nhất một chunk được trích (so theo giá trị, không theo chuỗi con
— "8.000.000" nằm trong "18.000.000" nhưng là mức khác; chấp nhận số suy ra
bằng hiệu/tổng cho câu hỏi "chênh lệch bao nhiêu"). Rẻ, tất định, không gọi
thêm LLM. Kiểm chứng: 0 dương tính giả trên 32 câu đang được trả lời ở
dev/test (sau khi sửa một lỗi dữ liệu mà chính bước kiểm tra này làm lộ ra).

**Giới hạn của cả hai mức, và bài học lớn nhất từ phần này:** bộ kiểm tra
chỉ xác minh câu trả lời *khớp với ngữ cảnh*, không xác minh ngữ cảnh *đúng
với câu hỏi*. Test lặp câu ví dụ README cho thấy 6/15 lần trả lời sai vẫn
qua cả hai mức — model áp mức phạt xe đạp cho xe máy, trích dẫn có thật và
chứa đúng số đó. Kiểm tra hậu xử lý không thay được retrieval đúng; lỗi đó
được sửa ở `007`. Hướng tiếp theo chưa làm: kiểm tra loại xe trong câu hỏi
khớp loại xe của Điều được trích (vd hỏi xe máy mà trích Điều 9 xe đạp).

## 7. Deployment

**API:** FastAPI, một endpoint `POST /chat` (`src/app.py`), nhận
`{question, history}`, trả `{answer, citations, refused,
needs_clarification, clarify_question, retrieved_ids,
hallucinated_citations, citation_labels, retrieval_ms, generation_ms}`
(`citation_labels`: trích dẫn dạng chữ, vd "Điểm b, khoản 8, Điều 7 Nghị định
168/2024/NĐ-CP", để web hiển thị thay cho id chunk). `Retriever` và
`OpenAI` client được tạo một lần lúc khởi động server và dùng chung cho mọi
request (không embed lại corpus mỗi câu hỏi).

**Web demo:** `web/index.html` — một trang HTML/JS thuần (không framework),
giao diện chat tối giản, giữ lịch sử hội thoại phía trình duyệt để hỏi được
nhiều lượt, hiển thị trích dẫn + thời gian xử lý cho mỗi câu trả lời.

**Latency đo thật** (`eval/run_api_latency.py`, round-trip HTTP qua 16 câu
dev, không phải latency nội bộ hàm Python):

| p50 | p90 | max |
|---|---|---|
| 1706ms | 2742ms | 3105ms |

(`eval/results/api_latency/`.) Không dùng Triton/dashboard giám sát — điểm
cộng nâng cao, ngoài phạm vi cắt giảm của bản nộp này.

## Giới hạn đã biết và hướng tiếp theo

Tổng hợp (chi tiết từng mục ở trên, không lặp lại số liệu):
1. Retrieval đã cải thiện nhiều nhờ hybrid BM25+cosine (`experiments/004`)
   và mở rộng truy vấn (`experiments/007`) nhưng chưa hoàn hảo: Recall@5 test
   0.77; trọng số kết hợp 0.5/0.5 chọn thủ công, chưa quét. Bảng mở rộng truy
   vấn viết tay, chỉ 5 mục — chỉ chữa đúng các cách nói đã liệt kê (vd "con
   nít" vẫn trượt); hướng tổng quát hơn là một bước LLM viết lại câu hỏi sang
   thuật ngữ luật (thêm một lượt gọi API và độ trễ, chưa thử), hoặc rerank.
2. Tập 40 câu chưa được người dùng duyệt tay toàn bộ — không nên coi số
   liệu trong báo cáo này là đánh giá cuối cùng, chỉ là ước lượng đầu tiên
   trên một tập nhỏ.
3. Không cố định seed/temperature cho LLM sinh câu trả lời → có nhiễu nhỏ
   giữa các lần chạy giống cấu hình. API embedding cũng không tất định hoàn
   toàn (đo được khi build lại index từ đầu: ~40% vector lệch nhẹ, tối đa
   ~0.01) — Recall@k không đổi nhưng MRR dao động ~±0.003; đây cũng là lời
   giải thích cho chênh lệch MRR chưa rõ nguyên nhân ghi ở `experiments/001`.
4. Hội thoại nhiều lượt có trong code và demo nhưng chưa có bộ eval tự động
   riêng để đo chất lượng khi hỏi nối tiếp.
5. Không có bản hợp nhất văn bản luật — hệ thống suy luận phiên bản theo
   ngày tại thời điểm trả lời, chưa thử so sánh với cách dựng bản hợp nhất
   tĩnh.
6. **Bộ kiểm tra trích dẫn không bắt được ngữ cảnh sai**: cả mức id lẫn mức
   nội dung (`006`) chỉ xác minh câu trả lời khớp với chunk được trích, không
   xác minh chunk đó đúng với câu hỏi. Khi retrieval đưa nhầm điều khoản (vd
   xe đạp thay vì xe máy), câu trả lời sai vẫn qua. `007` đã sửa trường hợp
   cụ thể đã biết; hướng tổng quát chưa làm: kiểm tra loại xe trong câu hỏi
   khớp loại xe của Điều được trích.
7. **Trích dẫn kém chi tiết hơn sau khi retrieval tốt lên**: model ngày càng
   hay trích chunk khoản cha thay vì chunk cấp điểm (6/22 câu test ở cấu hình
   chốt), nên nhãn hiển thị là "Khoản 9, Điều 6" thay vì "Điểm b, khoản 9,
   Điều 6". Căn cứ vẫn đúng nhưng người dùng phải tự tìm điểm. Hướng sửa chưa
   làm: yêu cầu trong prompt ưu tiên chunk cấp điểm.
