# 007 - Mở rộng truy vấn văn nói -> thuật ngữ luật (thành công, chốt mặc định)

- Split: dev (thiết kế + đo) rồi test (đo một lần, giữ riêng) + test lặp 15 lần
  câu mẫu README

## Giả thuyết
`experiments/006` cho thấy lỗi nguy hiểm nhất còn lại nằm ở retrieval: với
"Xe máy vượt đèn đỏ phạt bao nhiêu?", 6/15 lần hệ thống trả lời **sai mà vẫn
có căn cứ** (áp mức của xe đạp ở Điều 9), vì lệch từ vựng ở cả hai cụm: "xe
máy" ↔ luật viết "xe mô tô, xe gắn máy"; "vượt đèn đỏ" ↔ "không chấp hành
hiệu lệnh của đèn tín hiệu giao thông". Trên dev, cả 3 câu trượt hoàn toàn
(q14, q15, q27) cũng cùng kiểu: "say rượu / nhậu xỉn" (luật: "nồng độ cồn"),
"xe hơi", "vượt đèn đỏ". Nối thêm thuật ngữ luật tương ứng vào truy vấn sẽ để
cả embedding lẫn BM25 bắt được điều khoản đúng.

## Biến đã đổi
`src/retrieval.py`: `expand_query()` + bảng `COLLOQUIAL_TO_LEGAL` (5 mục),
dùng trong `Retriever.search` khi `expand=True`. Chỉ bổ sung vào **truy vấn
retrieval**; LLM vẫn nhận câu hỏi gốc. Bảng gồm: xe máy -> "xe mô tô, xe gắn
máy"; xe hơi -> "xe ô tô"; vượt đèn/đèn đỏ/đèn vàng -> "không chấp hành hiệu
lệnh của đèn tín hiệu giao thông"; rượu/bia/nhậu/xỉn/say -> "trong máu hoặc
hơi thở có nồng độ cồn"; bằng lái/tước bằng -> "tước quyền sử dụng giấy phép
lái xe".

**Chống rò test**: bảng chỉ thiết kế từ câu dev, câu mẫu README và từ đồng
nghĩa phổ thông về loại xe. Tác giả đã từng đọc cách diễn đạt các câu test
trong lúc phân tích lỗi ở các thí nghiệm trước, nên **cố ý không** đưa vào
những cách nói chỉ biết qua câu test (vd "con nít", "nẹt pô", "bốc đầu"). Kết
quả ở dưới khớp với điều này: câu test duy nhất còn trượt (q18 "chở con
nít...") đúng là cách nói đã bị loại ra.

## Giữ nguyên
Hybrid cosine+BM25, `gpt-5.4-mini`, prompt v3c, top-k 12, dữ liệu và bộ kiểm
tra của 006.

## Kết quả retrieval

| Split | Cấu hình | Recall@1 | Recall@3 | Recall@5 | MRR |
|---|---|---|---|---|---|
| dev | 006 (không mở rộng) | 0.2308 | 0.4615 | 0.5385 | 0.3842 |
| dev | **007 (mở rộng)** | **0.3846** | **0.7692** | **0.8462** | **0.5911** |
| test | 006 (không mở rộng) | 0.2727 | 0.5000 | 0.7273 | 0.4289 |
| test | **007 (mở rộng)** | **0.4545** | **0.7273** | **0.7727** | **0.6134** |

(`eval/results/retrieval_{dev,test}_{006,007_expand}/`.) Dev: 4 câu tốt hơn
(q14, q15, q27 từ không tìm thấy lên hạng 1–3), 0 câu tệ đi — nhưng đây là
kết quả **trong mẫu** (bảng thiết kế từ chính các câu này). Test (giữ riêng):
10 câu tốt hơn, 1 câu nhích xuống (q11 hạng 6 -> 8, vẫn trong top-12); 16/22
câu test có kích hoạt mở rộng. Recall@5 test tăng ít hơn dev (+0.05 so với
+0.31) đúng như kỳ vọng với một bảng thiết kế từ dev; Recall@1/MRR tăng mạnh
(+0.18) vì điều khoản đúng được đẩy lên đầu.

## Kết quả sinh câu trả lời

| Split | Cấu hình | correct_numbers | citation_ok (strict) | citation_ok (đúng khoản*) | refusal_ok (answerable) | refusal_ok (ngoài phạm vi) | total p50 |
|---|---|---|---|---|---|---|---|
| dev | 006 | 0.7692 | 0.6923 | 0.7692 | 0.8462 | 1.0 | — |
| dev | 007 | 0.7692 | 0.6154 | **0.8462** | **0.9231** | 1.0 | 1914ms |
| test | 006 | 0.7273 | 0.6364 | 0.8182 | 0.9091 | 1.0 | 1568ms |
| test | **007** | **0.7727** | 0.6364 | **0.9091** | **0.9545** | 1.0 | 1536ms |

(`eval/results/generation_{dev,test}_{006,007_expand}/`.)

\* **Chỉ số phụ, không thay chỉ số chính thức.** `citation_ok` (strict) đòi
đúng id chunk vàng (cấp điểm). Phân tích từng câu cho thấy mọi lần trượt
"cùng khoản" đều là model trích **chunk cấp khoản cha** — chunk này chứa
nguyên văn điểm đúng, nên căn cứ vẫn đúng, chỉ kém chi tiết; không có lần nào
trích nhầm điểm anh em trong cùng khoản. Số lần trích khoản cha tăng dần theo
từng cải tiến retrieval trên test: 1 (dense v3c) -> 3 (hybrid) -> 4 (006) ->
6 (007), vì BM25 và mở rộng truy vấn ưu tiên chunk khoản (dài, chứa nhiều từ
khoá). Cột "đúng khoản" chấp nhận trích khoản cha của chunk vàng, tính lại
offline từ predictions đã lưu cho **mọi** lần chạy để so sánh công bằng.
Không đổi chỉ số chính thức vì đổi thước đo ngay sau khi thấy kết quả bất lợi
là đúng kiểu thiên lệch cần tránh.

Bộ kiểm tra nội dung của 006 chặn 0 câu trong cả 4 lần chạy ở bảng trên.

## Test lặp: 15 lần "Xe máy vượt đèn đỏ phạt bao nhiêu?"

| Kết cục | 006 (không mở rộng) | 007 (mở rộng) |
|---|---|---|
| Hiển thị, **đúng** (4–6 triệu) | 0 | **15** |
| Hiển thị, **sai** (xe đạp, 150–250 nghìn) | 6 | 0 |
| Bị chặn / model từ chối | 9 | 0 |

(`eval/results/repeat_den_do_xe_may{,_expand}/`.) Chunk đúng `168_D7_K7_c`
xếp **hạng 1 cả 15/15 lần** (trước: không lọt top-12 lần nào). 13/15 lần trích
đúng cấp điểm, 2/15 trích khoản cha. Đây là câu đã khởi đầu chuỗi phát hiện
nên là bằng chứng *động cơ*, không phải bằng chứng giữ riêng — bằng chứng giữ
riêng là bảng test ở trên.

## Sửa phụ phát hiện trong lúc đo (không phải biến của thí nghiệm)
Dev q21: model trích `"[168_D6_K11_a]"` — chép cả ngoặc vuông của định dạng
ngữ cảnh `[id] ...` — nên id đúng bị coi là bịa, câu trả lời đúng bị ép từ
chối. Rà toàn bộ lịch sử: chỉ đúng 1 lần (chính lần này). Sửa ở
`src/generation.py` (chuẩn hoá id: bỏ khoảng trắng và ngoặc vuông bao quanh)
+ test. Bản sửa chỉ ảnh hưởng đúng loại output này; các số test ở trên chạy
sau khi đã có bản sửa nên không bị ảnh hưởng bởi lỗi này.

## Kết luận
Giả thuyết đúng. Cải thiện lớn ở retrieval trên test giữ riêng (MRR
0.43 -> 0.61), sửa hoàn toàn câu mẫu README (0/15 -> 15/15 đúng), và cải
thiện vừa phải ở sinh câu trả lời (+1 câu `correct_numbers`, +1 câu
`refusal_ok`, +2 câu đúng khoản trên test), không thêm độ trễ hay chi phí API.
**Chốt `expand=True` làm mặc định** (`Retriever`; script eval có `--no-expand`
để chạy lại baseline).

## Hạn chế còn lại
- Bảng ánh xạ viết tay, chỉ 5 mục — chỉ chữa đúng các cách nói đã liệt kê
  (vd q18 "con nít" vẫn trượt). Khó mở rộng thủ công mà không thiên lệch theo
  dữ liệu đánh giá; hướng tổng quát hơn là một bước LLM viết lại câu hỏi sang
  thuật ngữ luật (tốn thêm một lượt gọi API và độ trễ, chưa thử).
- Trích dẫn kém chi tiết hơn: model trích khoản cha nhiều hơn (6/22 câu test),
  nên nhãn hiển thị cho người dùng là "Khoản 9, Điều 6" thay vì "Điểm b, khoản
  9, Điều 6". Hướng sửa: yêu cầu trong prompt ưu tiên chunk cấp điểm (một thí
  nghiệm riêng, chưa làm).
- Cùng tác giả viết câu dev, bảng ánh xạ và đã từng đọc câu test — không loại
  trừ được hoàn toàn thiên lệch, chỉ giảm bằng quy tắc loại trừ nêu trên.
