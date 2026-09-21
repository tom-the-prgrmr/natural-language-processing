# Quy ước dữ liệu văn bản luật

- `data/raw/` là bản gốc, **bất biến**. Muốn thêm hoặc thay file: tải bằng `curl -sL --compressed` (thiếu `--compressed` thì trang chinhphu trả gzip, ra file nhị phân), rồi cập nhật `data/raw/SOURCES.md` (nguồn, mã băm SHA-256, ngày truy cập, tình trạng: đủ/thiếu/scan).
- `data/processed/` chỉ chứa thứ tái tạo được bằng script từ `data/raw/`. Không sửa tay file đầu ra; sửa script rồi chạy lại.
- Mức phạt, điều, khoản, điểm phải lấy từ file nguồn, không chép từ trí nhớ hay từ kết quả tóm tắt của công cụ fetch.
- ID chunk: `{văn bản}_D{điều}_K{khoản}`, ví dụ `168_D7_K4`; nếu tách theo điểm: `168_D7_K4_a`. Văn bản viết tắt: `L36` (Luật 36/2024), `168` (ND168), `238` (ND238). Mức phạt nằm ở câu dẫn của khoản, hành vi nằm ở các điểm, nên chunk tối thiểu là khoản; chunk tách theo điểm phải lặp lại câu dẫn của khoản.
- Phiên bản: hành vi xảy ra trước 15/08/2026 áp dụng ND168 bản gốc; sau đó áp dụng ND168 đã được ND238 sửa. Không trộn hai bản.
- Bản OCR (ví dụ `data/processed/ocr/nd238/`) chỉ là bản nháp cho đến khi từng con số đã được đối chiếu tay với ảnh trang. Ghi rõ phần nào đã đối chiếu.
