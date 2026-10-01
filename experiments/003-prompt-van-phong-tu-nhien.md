# 003 - Prompt văn phong tự nhiên (giữ, không làm giảm độ đúng)

- Ngày: 2026-10-01
- Split: dev (16 câu, 13 answerable)

## Giả thuyết
Câu trả lời của bản cũ đọc cứng: hay chép nguyên câu chữ điều luật, lặp câu
"công cụ tham khảo, không phải tư vấn pháp lý" (8/16 câu ở lần đối chứng), hay
nói "ngữ cảnh được cung cấp" như thể người dùng gửi văn bản. Thêm hướng dẫn văn
phong và một ví dụ mẫu vào prompt sẽ làm câu trả lời tự nhiên hơn mà **không**
làm giảm `correct_numbers`/`citation_ok`. Rủi ro: viết "đời thường" có thể làm
model đổi định dạng số tiền (metric so khớp chuỗi `6.000.000`), nên prompt bắt
giữ nguyên số tiền.

## Biến đã đổi
Prompt hệ thống (`src/generation.py: SYSTEM_PROMPT_TEMPLATE`), phần văn phong:
- bỏ yêu cầu nhắc "không phải tư vấn pháp lý" (giao diện đã hiển thị);
- quy tắc 6 mới: câu đầu trả lời thẳng, từ đời thường nhưng giữ nguyên số tiền,
  chỉ nêu hình phạt bổ sung khi ngữ cảnh ghi rõ con số, câu cuối "Căn cứ: ...";
- quy tắc 7 mới: chào hỏi/cảm ơn thì đáp thân thiện;
- 1 ví dụ mẫu văn phong dùng chỗ trống X/Y/Z (không dùng số thật để tránh lộ
  đáp án: câu vượt đèn đỏ nằm trong test).

Prompt được tinh chỉnh 3 lần liên tiếp trong cùng thí nghiệm, đều chỉ ở phần
văn phong: v3 (bản đầu) -> v3b (siết quy tắc hình phạt bổ sung, vì v3 viết
"cả hai đều bị trừ điểm theo quy định" không có số) -> v3c (cấm nói "ngữ cảnh
bạn cung cấp"). Bản chốt là v3c.

## Giữ nguyên
`gpt-5.4-mini`, `text-embedding-3-small`, top-k 12, cùng 16 câu dev, cùng
index. Lần đối chứng đã gồm thay đổi lời từ chối (model tự viết lời từ chối, có
câu dự phòng) nên khác `generation_dev_k12` cũ. Không cố định được seed của
model sinh: cùng prompt v3 chạy 2 lần cho `correct_numbers` 0.4615 và 0.6154,
tức dao động ~2/13 câu.

## Kết quả
| Lần chạy | correct_numbers | citation_ok | refusal_ok (answerable) | refusal_ok (unanswerable) | total p50 (ms) |
|---|---|---|---|---|---|
| v2 đối chứng | 0.4615 | 0.4615 | 0.8462 | 1.0 | 1850.8 |
| v3 | 0.4615 | 0.4615 | 0.6923 | 1.0 | 1650.5 |
| v3 (chạy lại) | 0.6154 | 0.5385 | 0.6923 | 1.0 | 1743.5 |
| v3b | 0.5385 | 0.4615 | 0.7692 | 1.0 | 1783.2 |
| **v3c (chốt)** | **0.5385** | **0.6154** | 0.6154 | 1.0 | 1609.4 |

Lần chạy: `eval/results/generation_dev_v2_baseline/`,
`generation_dev_v3_natural_style/`, `generation_dev_v3_natural_style_run2/`,
`generation_dev_v3b_natural_style/`, `generation_dev_v3c_natural_style/`.

Văn phong (đếm trên `predictions.jsonl`): câu chứa "tham khảo, không phải tư
vấn" 8 (v2) -> 0 (v3c); câu chứa "ngữ cảnh"/"bạn cung cấp" 4 (v3b) -> 0 (v3c).

Ví dụ q01, v2: "Phạt tiền từ 400.000 đồng đến 600.000 đồng. Đây là mức phạt đối
với người điều khiển xe mô tô, xe gắn máy không đội mũ bảo hiểm hoặc đội nhưng
không cài quai đúng quy cách ... Lưu ý: đây là công cụ tham khảo, không phải tư
vấn pháp lý." -> v3c: "Xe máy không đội mũ bảo hiểm bị phạt từ 400.000 đồng đến
600.000 đồng. Căn cứ: điểm h khoản 2 Điều 7 Nghị định 168/2024/NĐ-CP."

## Theo câu
`refusal_ok (answerable)` thấp hơn đối chứng ở cả 4 lần chạy prompt mới, nhưng
các câu bị từ chối thêm so với đối chứng (gộp 4 lần chạy: q03, q13, q14,
q28; riêng v3c: q13, q14, q28) **đều là câu bản đối chứng trả lời sai** (sai số tiền hoặc sai trích dẫn). 5 câu đối chứng đúng hoàn toàn
(q01, q02, q05, q22, q27) đúng ở v3c. Tức là prompt mới đổi một số "trả lời
sai" thành "từ chối", không làm hỏng câu đúng. Theo nhóm (`by_group` v3c) giống
hệt đối chứng: muc_phat_truc_tiep 3/5, doi_thuong 0/3, nhieu_dieu_kien 1/2,
phu_thuoc_loai_xe 1/2, ngoai_pham_vi 2/2, bay_loi_thoi 1/2.

## Kết luận
Giả thuyết được xác nhận ở mức cỡ mẫu cho phép: văn phong tự nhiên hơn rõ
(bỏ câu lặp, trả lời thẳng, căn cứ ghi bằng chữ), `correct_numbers` và
`citation_ok` không giảm (chênh lệch nằm trong dao động ~2/13 câu giữa hai lần
chạy cùng prompt). Chốt prompt v3c.

Lỗi còn thấy: q14 ở v3c đặt `refused: true` (trước đó v3/v3b cũng có lúc đặt
`refused: true` nhưng vẫn viết mức phạt trong answer) -> cờ từ chối chưa nhất
quán với nội dung. Model hay chèn từ tiếng Armenia "օրինակ" (= "ví dụ") vào lời
từ chối; xử lý hậu kỳ bằng cách thay đúng từ này (`KNOWN_FOREIGN_WORDS`), không
ảnh hưởng metric.

## Chạy test (một lần, sau khi chốt v3c trên dev)
| Metric | Prompt cũ (`generation_test/`) | v3c (`generation_test_v3c_natural_style/`) |
|---|---|---|
| correct_numbers | 0.5455 | 0.6364 |
| citation_ok | 0.2273 | 0.2727 |
| refusal_ok (answerable) | 0.6364 | 0.5455 |
| refusal_ok (unanswerable) | 1.0 | 1.0 |
| total p50 (ms) | 2081.9 | 1718.2 |

Cùng xu hướng với dev. Không chỉnh prompt sau khi xem số test.

## Bước tiếp
Sửa trường hợp `refused: true` nhưng answer vẫn có mức phạt (cờ và nội dung
không nhất quán).
