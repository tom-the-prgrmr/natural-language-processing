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

**Retrieval** (`src/retrieval.py`): dense retrieval — embed toàn bộ chunk
bằng `text-embedding-3-small`, cache vector vào `embeddings.npz`, tìm top-k
bằng cosine similarity (numpy thuần, không dùng vector DB vì corpus đủ nhỏ
để giữ trong RAM). Không dùng BM25/hybrid/reranker — cắt phạm vi có chủ đích
để còn thời gian cho các phần khác, ghi trong `docs/plan.md`.

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

| Split | n (answerable) | Recall@1 | Recall@3 | Recall@5 | MRR |
|---|---|---|---|---|---|
| dev | 13 | 0.0769 | 0.1538 | 0.3077 | 0.1682 |
| test | 22 | 0.0909 | 0.2273 | 0.2273 | 0.1591 |

(`eval/results/retrieval_dev/`, `eval/results/retrieval_test/`.)

Recall@5 ~0.23–0.31 là **yếu** — với top-5, phần lớn câu hỏi vẫn không tìm
đúng chunk vàng. Phân tích theo nhóm trên dev: `phu_thuoc_loai_xe` Recall@5
= 1.0 (câu hỏi luôn nói rõ "ô tô"/"xe máy", tiêu đề Điều 6/Điều 7 đủ phân
biệt), nhưng `doi_thuong` (văn nói) = 0.0/3 và `nhieu_dieu_kien` = 0.0/1 —
đây là hai nhóm khó nhất cho dense retrieval trên văn bản luật ngắn.

**Nguyên nhân cụ thể** (quan sát thủ công trên `predictions.jsonl` của test):
câu hỏi về nồng độ cồn ("nồng độ cồn mức cao nhất", "nồng độ cồn ở mức thấp
nhất") liên tục truy xuất nhầm sang Điều 21 (giấy tờ xe/giấy phép lái xe) dù
mức phạt nồng độ cồn thực ra nằm ở Điều 6 (ô tô) và Điều 7 (xe máy) — hai chủ
đề hoàn toàn khác nhưng embedding xếp gần nhau, có lẽ vì các điều luật này
dùng chung nhiều cụm từ hành chính lặp lại ("phạt tiền", "đồng", "hành vi vi
phạm quy định tại"). Ví dụ cụ thể: câu "Nồng độ cồn mức cao nhất (trên 80
miligam/100ml máu)..." (test) truy xuất toàn chunk `168_D21_*`, không có
chunk `168_D6_K11_a`/`168_D7_K9_d` (chunk vàng) trong top-12, hệ thống đúng
quy trình **từ chối trả lời** thay vì bịa — an toàn nhưng không hữu ích. Ghi
chi tiết thí nghiệm đã thử để sửa (không thành công) ở mục 5 và
`experiments/001-...md`.

### Sinh câu trả lời (test, k=12)

Test được chạy với prompt cũ, sau đó chạy lại **một lần** khi đổi prompt văn
phong (thí nghiệm `003`, chốt trên dev trước rồi mới chạy test, không chỉnh
tiếp sau khi xem số test). Cả hai lần đều giữ lại.

| Metric | Prompt cũ | Prompt văn phong (hiện tại) |
|---|---|---|
| correct_numbers_rate (answerable, n=22) | 0.5455 | 0.6364 |
| citation_ok_rate (answerable, n=22) | 0.2273 | 0.2727 |
| refusal_ok_rate (answerable — nên trả lời) | 0.6364 | 0.5455 |
| refusal_ok_rate (unanswerable, n=2 — nên từ chối) | 1.0 | 1.0 |
| latency total p50 / max | 2082ms / 3385ms | 1718ms / 2805ms |

(`eval/results/generation_test/`, `eval/results/generation_test_v3c_natural_style/`.)
Theo nhóm (test, prompt hiện tại): `muc_phat_truc_tiep` 3/7, `doi_thuong`
1/5, `nhieu_dieu_kien` 1/4, `phu_thuoc_loai_xe` 0/4, `ngoai_pham_vi` 2/2,
`bay_loi_thoi` 1/2 (prompt cũ giống hệt, trừ `doi_thuong` 0/5; tiêu chí "ok"
= đúng số liệu VÀ đúng trích dẫn với câu answerable, hoặc từ chối đúng với
câu unanswerable). Chênh lệch giữa hai cột nhỏ hơn dao động đo được giữa hai
lần chạy cùng một prompt trên dev (~2/13 câu, xem `experiments/003`), nên
không coi là cải thiện độ đúng.

**`citation_ok_rate` thấp hơn cả retrieval Recall@5** — hợp lý, vì
`citation_ok` yêu cầu đúng chunk vàng nằm trong `citations` LLM thực sự dùng
(tập con của 12 chunk truy xuất), chặt hơn việc gold chunk chỉ cần *có mặt*
trong top-12.

**Ví dụ lỗi cụ thể** (từ `eval/results/generation_test/predictions.jsonl`, lặp lại ở lần chạy prompt mới):
- *"lạng lách xe hơi lần 2 (tái phạm) bị sao không"* — gold: tịch thu xe
  (Điều 6 khoản 14, áp dụng khi tái phạm khoản 12). Retrieval không đưa
  chunk "tái phạm → tịch thu" vào top-12; model đúng mực hỏi lại (prompt mới:
  từ chối) thay vì đoán. Nhóm lỗi: quy định kiểu "nếu vi phạm X thì áp dụng mức ở khoản
  khác" (tái phạm, gộp hành vi) khó với retrieval từng-khoản độc lập.
- *"chở con nít ngồi ghế trước xe hơi mà không có ghế an toàn giờ phạt
  chưa"* — gold: phạt cảnh cáo theo khoản 1a Điều 6 (khoản **do ND238 bổ
  sung**, hiệu lực 15/08/2026). Model trích dẫn nhầm sang khoản 3 Điều 6
  ND168 gốc (phạt tiền 800.000–1.000.000đ, cho hành vi tương tự nhưng
  **trước** khi có khoản 1a mới) — đúng dạng lỗi "chưa cập nhật quy định bổ
  sung" mà nhóm `bay_loi_thoi` nhắm tới, nhưng câu này lại không gắn nhãn
  nhóm đó trong seed hiện tại, cho thấy ranh giới giữa các nhóm chưa tách
  bạch hoàn toàn trong tập 40 câu.

**Hạn chế của chính chỉ số `correct_numbers_rate`:** chỉ số này so khớp
chuỗi số tiền dạng `x.xxx.xxx` (có dấu chấm phân cách nghìn); các câu hỏi
phân biệt bằng ngưỡng khác (vd "quá tốc độ trên 20 km/h", không phải số
tiền) không bị chỉ số này phát hiện khi model trả lời sai/từ chối — tức
`correct_numbers=True` vẫn xuất hiện ở một số câu model **đã từ chối trả
lời** đơn giản vì gold_answer của câu đó không có số tiền để so khớp. Đây là
giới hạn của cách đo đơn giản hoá (không phải LLM-as-judge), tự nhận trong
báo cáo thay vì report số đẹp mà không giải thích.

## 5. Cải tiến (so sánh trước/sau bằng số liệu thật)

Ba thí nghiệm thật, mỗi lần đổi đúng một biến, log đầy đủ ở `experiments/`:

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

Hướng mở rộng chưa kịp làm (ghi nhận, không giả vờ đã làm): kiểm tra không
chỉ id chunk có tồn tại, mà nội dung câu trả lời có thực sự suy ra được từ
nội dung chunk được trích hay không (cần một bước so khớp ngữ nghĩa/LLM-judge
riêng, tốn thêm một lượt gọi API).

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
1. Retrieval dense đơn thuần không đủ cho văn bản luật ngắn, nhiều thuật
   ngữ lặp — hướng tiếp theo hợp lý nhất là thử BM25/hybrid hoặc rerank
   (đã cắt khỏi phạm vi lần này, không phải không biết tới).
2. Tập 40 câu chưa được người dùng duyệt tay toàn bộ — không nên coi số
   liệu trong báo cáo này là đánh giá cuối cùng, chỉ là ước lượng đầu tiên
   trên một tập nhỏ.
3. Không cố định seed/temperature cho LLM sinh câu trả lời → có nhiễu nhỏ
   giữa các lần chạy giống cấu hình.
4. Hội thoại nhiều lượt có trong code và demo nhưng chưa có bộ eval tự động
   riêng để đo chất lượng khi hỏi nối tiếp.
5. Không có bản hợp nhất văn bản luật — hệ thống suy luận phiên bản theo
   ngày tại thời điểm trả lời, chưa thử so sánh với cách dựng bản hợp nhất
   tĩnh.
