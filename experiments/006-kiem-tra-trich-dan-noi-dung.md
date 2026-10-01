# 006 - Kiểm tra trích dẫn ở mức nội dung (có ích nhưng không chạm tới gốc lỗi)

- Split: dev (16 câu) + phân tích phản thực tế trên dev/test đã lưu + test lặp
  có mục tiêu (15 lần một câu hỏi)

## Bối cảnh
Khi tự chạy lại README trên bản sao sạch, chính câu mẫu "Xe máy vượt đèn đỏ
phạt bao nhiêu?" trả lời sai. Một lần model trả lời đúng mức ngoài đời (4–6
triệu, từ trí nhớ riêng) nhưng trích `168_D7_K8_b` — điều khoản nồng độ cồn,
mức 6–8 triệu, không hề chứa "4.000.000". Bộ kiểm tra trích dẫn bịa của
"phần tự nghĩ thêm" cho lọt vì nó chỉ kiểm id có nằm trong ngữ cảnh hay không.

## Giả thuyết
Nâng kiểm tra từ mức id lên mức nội dung — mọi số tiền trong câu trả lời phải
có trong nội dung ít nhất một chunk được trích — sẽ chặn được loại lỗi "trả
lời bằng trí nhớ rồi gắn trích dẫn không liên quan", mà không làm hỏng câu
trả lời đúng.

## Biến đã đổi
`src/generation.py`: thêm `ungrounded_amounts()`, chạy sau kiểm tra id; có số
không có căn cứ -> ép `refused=True`, hiện câu từ chối dự phòng. So khớp theo
**giá trị số** chứ không theo chuỗi con ("8.000.000" nằm trong "18.000.000"
nhưng là mức khác). API trả thêm trường `ungrounded_amounts`.

## Hai vấn đề bắt được trước khi tin dùng (phân tích phản thực tế)
Áp bộ kiểm tra lên các câu trả lời đã lưu của cấu hình hybrid (hậu xử lý tất
định, không gọi API): bản đầu chặn 2 câu, **cả hai đều vốn đúng** (dương tính
giả):
1. **Lỗi dữ liệu có sẵn từ lâu**: HTML gốc ND168 khoản 11 Điều 6 viết
   `40.000.<span>000</span>`, `clean.py` thay thẻ bằng dấu cách nên văn bản
   sạch thành "40.000. 000 đồng". Quét toàn corpus: chỉ đúng 1 chỗ, lặp trong
   6 chunk con của khoản 11. Sửa ở `clean.py` (ghép lại số bị tách khi phía
   trước đã có nhóm nghìn), chạy lại ingest: đúng 6 chunk đổi, không gì khác;
   thêm test chặn tái phát. LLM vẫn đọc hiểu được số bị tách nên lỗi này trước
   đó vô hình trong mọi chỉ số.
2. **Số suy ra hợp lệ**: câu "ô tô phạt hơn xe máy bao nhiêu" (q31) — model
   tính 30tr − 8tr = 22tr, không có nguyên văn trong chunk nào. Chấp nhận số
   bằng hiệu/tổng của hai số có căn cứ.

Sau 2 sửa: **0/32** câu đang được trả lời (dev 11 + test 21) bị chặn — không
dương tính giả nào. Nhưng cũng không bắt được lỗi nào trong các lần chạy đã
lưu, vì tập eval không chứa đúng kiểu lỗi này.

## Kết quả chạy lại dev (dữ liệu đã sửa + kiểm tra mới, `_006`)

| | Recall@5 | MRR | correct_numbers | citation_ok | refusal_ok (answerable) | refusal_ok (ngoài phạm vi) |
|---|---|---|---|---|---|---|
| hybrid trước (`generation_dev_hybrid_v2metric`) | 0.5385 | 0.3817 | 0.7692 | 0.7692 | 0.8462 | 1.0 |
| 006 (`retrieval_dev_006`, `generation_dev_006`) | 0.5385 | 0.3842 | 0.7692 | 0.6923 | 0.8462 | 1.0 |

Bộ kiểm tra mới chặn 0 câu. Chênh 1 câu ở `citation_ok` (q27) là nhiễu LLM:
lần này model trích id không có trong ngữ cảnh, bị bộ kiểm tra **cũ** chặn.
MRR lệch 0.0025 do build lại index (API embedding không tất định, xem README).

## Test lặp có mục tiêu: 15 lần "Xe máy vượt đèn đỏ phạt bao nhiêu?"
(`eval/run_repeat.py`, kết quả `eval/results/repeat_den_do_xe_may/`). Đáp án
đúng: 4.000.000–6.000.000 đồng (`168_D7_K7_c`).

| Kết cục | Số lần | Ghi chú |
|---|---|---|
| Bị chặn: trích id không có trong ngữ cảnh | 6 | bộ kiểm tra cũ |
| **Bị chặn: số tiền không có trong chunk được trích** | **1** | chỉ bộ kiểm tra mới bắt được |
| Model tự từ chối | 2 | |
| **Hiển thị cho người dùng** | **6** | **cả 6 đều SAI**: 150–250 nghìn, trích `168_D9_K2` |

`168_D9_K2` là **Điều 9 — xe đạp, xe đạp máy, xe thô sơ**, điểm đ "không chấp
hành hiệu lệnh của đèn tín hiệu giao thông". Model áp nhầm mức của xe đạp cho
xe máy. Câu trả lời này *có căn cứ thật* (số tiền đúng là trong chunk được
trích) nên vượt qua cả hai mức kiểm tra. Chunk đúng `168_D7_K7_c` không lọt
top-12 lần nào.

## Kết luận
Giả thuyết đúng nhưng hẹp: kiểm tra mức nội dung chặn đúng loại lỗi nó nhắm
tới (1/15) và không có dương tính giả (0/32), nên **giữ lại** như một lớp an
toàn. Nhưng test lặp cho thấy lỗi nguy hiểm hơn — **40% lần trả lời sai mà
vẫn "có căn cứ"** — nằm ở retrieval, và không bộ kiểm tra hậu xử lý nào chặn
được khi ngữ cảnh chỉ chứa điều khoản sai. Nguyên nhân: lệch từ vựng ở cả hai
cụm của câu hỏi — "xe máy" ↔ luật viết "xe mô tô, xe gắn máy"; "vượt đèn đỏ" ↔
"không chấp hành hiệu lệnh của đèn tín hiệu giao thông". Tệ hơn, Điều 9 có
chữ "xe đạp **máy**" nên BM25 còn ưu tiên nhầm sang nó.

Sản phẩm phụ có giá trị: phát hiện và sửa một lỗi dữ liệu tồn tại từ đầu dự
án mà không chỉ số nào bắt được.

## Bước tiếp
`experiments/007`: mở rộng truy vấn văn nói -> thuật ngữ luật. Lưu ý tránh rò
test: chỉ dùng câu dev (vd q27 cùng họ lỗi "vượt đèn đỏ") và kiến thức chung
về thuật ngữ luật để thiết kế, không xem cách diễn đạt câu test.
