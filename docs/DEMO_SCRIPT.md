# Kịch bản trình diễn

Chạy `./scripts/start.sh` (máy này dùng thêm `--dns-workaround`). Mở http://localhost:5173. Tài khoản `{admin,staff,student}@labchain.local`; mật khẩu trong dòng DEMO_PASSWORD của `.env`. Không dùng tài khoản demo cho môi trường thật.

## Môn Ngôn ngữ kịch bản

1. Login staff. Mở Thiết bị, đổi 10/15 mỗi trang, tìm Arduino hoặc EQ-0001.
2. Alt+N mở biểu mẫu, tạo thiết bị `DEMO-001`. Alt+S lưu. Mở chi tiết xem đủ field Product và timestamps; sửa tên/ảnh.
3. Nhân bản một, chọn hai checkbox và nhân bản nhiều. Chọn các bản sao và lưu trữ nguyên lô.
4. Tắt cột đơn giá, reload/login lại để kiểm tra lựa chọn vẫn còn. Alt+F đưa focus vào tìm kiếm.
5. Tải mẫu XLSX/JSON/XML, đổi mã để không trùng. Kiểm tra xem trước, rồi xác nhận nhập. Thử số lượng âm/trùng mã để thấy lỗi dòng và không lưu dở dang. Xuất theo từ khóa đang tìm.
6. Nếu đã bật và kiểm chứng OCR thực: mở Thêm → Quét ảnh nhãn → dùng `docs/samples/equipment-label.png` → đọc → sửa gợi ý → áp dụng → nhập phân loại/số lượng/giá → Lưu. Trước khi Lưu, không có thiết bị mới trong DB.
7. Login student để thấy chức năng sửa thiết bị bị ẩn và API vẫn từ chối thao tác ghi.

## Môn Blockchain

1. Login student, tạo phiếu có hai loại thiết bị, hạn trả tương lai. Student chỉ thấy phiếu của mình.
2. Login staff, duyệt. Khả dụng giảm ngay; PENDING/SUBMITTED/CONFIRMED của Blockchain hiển thị riêng. Mở chi tiết copy tx hash, block.
3. Mở Xác minh Blockchain; so sánh hash snapshot tính lại và hash đọc từ contract. Chỉ VERIFIED khi đối chiếu thành công.
4. Bàn giao rồi Nhận trả toàn bộ. Khả dụng phục hồi, sự kiện EquipmentReturned và bằng chứng thứ hai xuất hiện.
5. Dừng worker để thấy pending rồi bật lại; để mô phỏng RPC outage giữ nguyên chain state, dùng `docker compose pause hardhat-node` rồi `unpause` (thêm context desktop-linux trên máy này). Không restart/reset node hoặc dùng `down -v` khi cần giữ bằng chứng; Hardhat local không lưu chain qua restart.
6. Trình bày test `test_postgres_concurrent_approvals`, `test_postgres_double_return`, `test_worker_signed_before_send_reconcile_idempotency`: chống vượt tồn, trả đôi, mất phản hồi RPC. Test sửa snapshot trong DB test chứng minh MISMATCH mà không sửa lịch sử demo.
7. Giải thích: chain giữ hash và tham chiếu opaque; thông tin cá nhân ở DB; chứng thực hash không chứng minh bàn giao ngoài thực tế.

Screenshots/kiểm tra thị giác: chưa chụp qua trình duyệt nếu công cụ browser không kết nối. Không coi kịch bản OCR là đã demo thành công khi model chưa tải xong; xem bảng trạng thái kiểm chứng trong README.
