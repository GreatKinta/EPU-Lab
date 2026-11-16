# Kiểm tra máy phát triển

Cập nhật đóng gói 2026-11-16: chạy triển khai chỉ cần Docker + Compose đang hoạt động. Python/Node được ghi bên dưới là công cụ phát triển tùy chọn trên host. OCR CPU và model đã được kiểm chứng trong Docker; frontend triển khai bằng Nginx. Xem [OPERATIONS.md](OPERATIONS.md) và [docker-validation.json](docker-validation.json).

Kiểm tra ngày 2026-11-12 bằng `python scripts/check_environment.py --json`.

| Thành phần | Máy hiện tại | Cách sử dụng |
|---|---|---|
| Python | 3.14.9, pip, venv có sẵn | Backend container cố định Python 3.12 |
| Node.js / npm | 26.13.1 / 12.2.2 | Container dùng Node 24 |
| Git | Có | Thư mục ban đầu chưa phải Git repository |
| Docker / Compose | 29.9.3 / 5.7.0 | Docker Desktop context `desktop-linux` |
| Docker daemon | Ban đầu tắt, đã khởi động | `systemctl --user start docker-desktop` |
| PostgreSQL | Chưa cài trực tiếp | Service PostgreSQL 17 trong Compose |
| Hardhat / frontend / backend libraries | Chưa có trong thư mục ban đầu | Cài cục bộ dự án, có lockfiles |
| Dung lượng | Khoảng 364 GiB trống ban đầu | Đủ cho image, DB, model OCR |
| RAM | 15 GiB, khoảng 5.6 GiB available ban đầu | OCR chạy CPU theo yêu cầu, tránh nhiều request song song |

Không cần cài PostgreSQL, Solidity hoặc Python 3.12 vào hệ điều hành khi chạy toàn bộ qua Docker. Các thư viện OCR và model cần tải riêng nếu bật OCR; cài Docker CLI đơn thuần chưa đủ, daemon phải hoạt động.

Dữ liệu máy có thể thay đổi. Chạy lại script để xem kết quả hiện tại. Script không đọc hoặc in giá trị secrets.

## Kết quả triển khai

Docker Desktop đã chạy được full-stack với workaround DNS tại phạm vi build. Đã kiểm tra thực tế Python 3.12.16 trong backend container, frontend build Node 24, smart contract tests trong container và HTTP smoke có worker xác minh cả mượn/trả. PyTorch CPU/EasyOCR đã cài trong venv host; model acceptance được báo riêng trong README. Công cụ browser của phiên làm việc hiện không kết nối nên chưa có screenshot.
