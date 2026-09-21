# Nguồn dữ liệu thô (data/raw)

Ngày truy cập: 2026-09-20. File trong thư mục này là **bản gốc, không sửa tay**. Mọi xử lý (làm sạch, chunk) ghi ra `data/processed/`.

| File | Văn bản | Nguồn | Trạng thái |
|---|---|---|---|
| `luat36.pdf` | Luật Trật tự, an toàn giao thông đường bộ 36/2024/QH15 (hiệu lực 01/01/2025) | https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/9/36-2024-qh15.pdf | Có text layer (21 trang), dùng được |
| `luat36.html` | Cùng văn bản, bản HTML | https://xaydungchinhsach.chinhphu.vn/toan-van-luat-trat-tu-an-toan-giao-thong-duong-bo-119240909105718285.htm | Đủ Điều 1–89 (liên tục, không thiếu số) |
| `nd168.html` | Nghị định 168/2024/NĐ-CP (hiệu lực 01/01/2025), **bản gốc chưa sửa đổi** | https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-dinh-168-2024-nd-cp-quy-dinh-xu-phat-vi-pham-hanh-chinh-ve-trat-tu-atgt-duong-bo-119241231164556785.htm | Đủ Điều 1–55 |
| `nd238.pdf` | Nghị định 238/2026/NĐ-CP sửa đổi ND168 (ký 26/06/2026, hiệu lực **15/08/2026**) | https://xdcs.cdnchinhphu.vn/446259493575335936/2026/6/30/238-2026-nd-cp-26062026-signed-17828044032351834527408.pdf (bản trùng: https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/7/238-ndcp.signed.pdf) | **Ảnh scan, không có text** (14 trang), cần OCR |
| `nd238.html` | Bài đăng chinhphu.vn về ND238 | https://xaydungchinhsach.chinhphu.vn/nghi-dinh-so-238-2026-nd-cp-sua-doi-quy-dinh-xu-phat-vi-pham-giao-thong-duong-bo-tru-diem-phuc-hoi-diem-giay-phep-lai-xe-119260630142033452.htm | **Chỉ trích một phần** (Điều 3, 6, 20, 42), không phải toàn văn |

SHA-256 (16 ký tự đầu): nd168.html `bcbea4df075fb8e0`, luat36.html `155ffb0f617a2e71`, luat36.pdf `e83b092fd1e93a63`, nd238.html `bdf130357ac2679b`, nd238.pdf `4dc0ae6f10aa301d`.

## Điểm cần xử lý

1. **ND238 làm thay đổi ND168.** Theo luatvietnam.vn, ND238 sửa các Điều 3, 6, 13, 14, 17, 18, 20, 21, 26, 29, 32, 39–44, 46, 47, 50, 53 của ND168. Hành vi xảy ra trước 15/08/2026 vẫn áp dụng quy định cũ. Chatbot phải trả lời theo bản còn hiệu lực và biết cảnh báo mốc thời gian. Đây cũng là nguồn tốt cho nhóm câu hỏi "bẫy lỗi thời".
2. **Chưa có toàn văn ND238 dạng text.** Cần OCR file `nd238.pdf` (máy chưa có tesseract/easyocr) rồi **đối chiếu tay từng điều sửa đổi** với PDF, vì OCR sai chữ số thì mức phạt sai. Chưa có bản hợp nhất (ND168 sau sửa đổi) từ nguồn chính thức.
3. Text HTML của ND168 có lỗi khoảng trắng do link nội tuyến (`k hi`, `đ )`, `điểm b , điểm d`). Cần chuẩn hoá khi tiền xử lý.
4. Nghị định 100/2019/NĐ-CP (bị ND168 thay thế phần đường bộ) chưa tải. Chỉ cần nếu muốn câu hỏi bẫy về luật cũ. Nguồn: https://vanban.chinhphu.vn/?pageid=27160&docid=198733
5. Chưa đối chiếu Luật 36/2024 với các văn bản hướng dẫn khác (thông tư của Bộ Công an).

## OCR ND238 (2026-09-21)
- Bản nháp: `data/processed/ocr/nd238/pages/p01..p14.txt` (kèm ảnh trang và `meta.json`). Tạo bằng `src/ingest/ocr_pdf.py`, model `gpt-5.4`, 200 dpi, ~52,6 nghìn token. Không có chỗ nào model đánh dấu `[?]`.
- Văn bản có Điều 1–21 (phần sửa đổi ND168 và điều khoản thi hành).
- **Đã đối chiếu tay với ảnh trang (2026-09-21), toàn bộ khớp với OCR:**
  - Trang 3, 4, 6, 7, 9, 10, 11, 12, 13: đã xem ảnh và so với bản OCR.
  - Mọi **số tiền**: 12–14 triệu (khoản 8a Điều 20, tr.4); 5–10 triệu (khoản 3a Điều 29, tr.6); 5–6 triệu cá nhân / 10–12 triệu tổ chức (khoản 9a Điều 32, tr.6); thẩm quyền 7,5 / 15 / 22,5 / 30 / 37,5 / 45 triệu (tr.9), 60 / 75 triệu (tr.10–11); 37,5 và 75 triệu ở Điều 42 (tr.8) đã khớp với bài chinhphu.vn.
  - Mọi **điểm trừ giấy phép lái xe**: 06 điểm (khoản 10 Điều 20, tr.4), 02 điểm (khoản 4 Điều 29, tr.6), 04 điểm (khoản 21 Điều 32, tr.7).
  - **Ngày hiệu lực:** 15/08/2026 (Điều 20 của ND238, tr.13); 01/01/2028 (khoản 3 Điều 53, tr.12) cho quy định về thiết bị ghi hình người lái ở xe dưới 8 chỗ, xe tải (trừ đầu kéo), xe nội bộ (điểm l khoản 5 Điều 20, điểm b khoản 3 Điều 21, điểm b khoản 9a Điều 32); 01/01/2029 (khoản 4 Điều 53, tr.12) cho thiết bị ghi hình khoang chở khách (điểm n khoản 5 Điều 20; điểm k, l khoản 7 Điều 26).
- **Chưa xem ảnh:** trang 1, 2, 5, 8, 14 (chỉ chứa Điều 1–6, 9, 13–14 và phần cuối; không có số tiền, điểm trừ hay ngày hiệu lực theo kết quả tìm trong OCR). Số khoản/điểm được viện dẫn trên các trang này **chưa đối chiếu**. Bản OCR vẫn coi là nháp ở các trang đó; dùng trang 3–4, 6–7, 9–13 cho số liệu mức phạt/điểm trừ/hiệu lực.
