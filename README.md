# LabChain

Quản lý mượn/trả thiết bị phòng Lab, giao diện tiếng Việt. React + TypeScript + Ant Design + TanStack Query; FastAPI + SQLAlchemy + Alembic + PostgreSQL; Solidity + Hardhat + Web3.py; OCR EasyOCR CPU tùy chọn.

Đặc tả và tiến độ: [PROJECT_PLAN.md](PROJECT_PLAN.md). Kiểm tra máy: [ENVIRONMENT.md](docs/ENVIRONMENT.md).

## Chạy toàn bộ bằng Docker

Máy mới chỉ cần Docker Engine + Compose bản mới (hỗ trợ `up --wait`) hoặc Docker Desktop đang chạy (Linux containers). Không cần Python, Node.js, npm, PostgreSQL hay môi trường OCR trên máy. Các image ứng dụng dùng Linux/amd64; máy ARM cần hỗ trợ giả lập amd64 của Docker. Lần đầu cần Internet để tải image, dependency và model OCR.

Linux/macOS:

```bash
bash ./setup-linux.sh
# Nếu Docker Desktop gặp lỗi DNS khi build:
bash ./setup-linux.sh --dns-workaround
```

Windows PowerShell, tại thư mục dự án:

```powershell
.\setup-windows.bat
# Nếu Docker Desktop gặp lỗi DNS khi build:
.\setup-windows.bat -DnsWorkaround
```

Windows có thể nhấp đúp `setup-windows.bat`. Hai file setup dùng được cả lần đầu và mỗi lần mở lại, tự mở trình duyệt khi dịch vụ sẵn sàng. Cần mở Docker trước; Linux server không có giao diện sẽ chỉ in địa chỉ web. Script giữ nguyên `.env`, dữ liệu trong volume và mật khẩu tài khoản hiện có.

Script tạo `.env` bằng Python **trong container**, giữ nguyên file nếu đã tồn tại, build image và chờ dịch vụ sẵn sàng. Migration, seed demo, deploy contract và tải/kiểm tra model OCR en/vi đều tự động. Frontend là bản build React được Nginx phục vụ; API được proxy qua `/api/` cùng địa chỉ web.

- Giao diện: http://localhost:5173
- API/OpenAPI trực tiếp: http://localhost:8000/docs
- Health/readiness qua web: http://localhost:5173/api/v1/ready
- RPC: http://localhost:8545, Hardhat local chain 31337
- Tài khoản: `admin@labchain.local`, `staff@labchain.local`, `student@labchain.local`
- Mật khẩu demo: `DEMO_PASSWORD` trong `.env` được tạo riêng cho máy. Seed không đổi mật khẩu tài khoản đã tồn tại.

Có thể chạy trực tiếp bằng Compose trên mọi hệ điều hành:

```bash
# Linux/macOS: đặt UID/GID để .env thuộc người dùng hiện tại.
LOCAL_UID=$(id -u) LOCAL_GID=$(id -g) docker compose -f docker-compose.setup.yml run --rm setup
# Windows PowerShell: docker compose -f docker-compose.setup.yml run --rm setup

docker compose up --build -d --wait --wait-timeout 600
docker compose ps -a
```

Nếu dùng context Docker Desktop trên Linux, thêm `--context desktop-linux` ngay sau `docker`, hoặc dùng script để tự chọn context.

Để máy khác trong LAN truy cập, đặt `WEB_BIND_ADDRESS=0.0.0.0` và `WEB_PORT=5173` trong `.env`, chạy lại script rồi mở `http://IP_MAY_CHU:5173`. API qua Nginx dùng cùng origin nên không cần đổi URL trong frontend. DB, API trực tiếp và RPC vẫn bind localhost.

Dữ liệu DB, ảnh tải lên, cấu hình signer và model OCR nằm trong named volumes. Chuyển **mã nguồn** sang máy mới tạo môi trường độc lập; muốn chuyển dữ liệu đang dùng, xem [hướng dẫn triển khai và sao lưu](docs/OPERATIONS.md). Không chép `node_modules`, `.venv` hoặc `runtime/compose.build-dns.yml` sang máy khác.

Hardhat là blockchain thử nghiệm trong bộ nhớ: dừng/restart node làm mất lịch sử on-chain dù DB và cấu hình signer vẫn còn. Compose deploy lại contract khi khởi động; bằng chứng cũ không được khôi phục. Đây là bộ triển khai phục vụ học tập/demo, chain 31337; không dùng key local cho mạng thật.

## Chức năng

- Đăng nhập Argon2id/JWT; student/staff/admin, quản trị tài khoản.
- Đủ 11 chức năng Product: bảng phân trang 10/15; thêm/sửa/chi tiết; lưu trữ một/nhiều; tìm kiếm; nhân bản một/nhiều; XLSX/JSON/XML import/export + mẫu; ẩn/hiện cột lưu localStorage; Alt+N/S/F.
- Import xem trước rồi xác nhận, kiểm tra nguyên lô, lỗi theo dòng. Ảnh có xác thực, kiểm tra MIME/nội dung, giới hạn dung lượng/pixel. XML cấm DTD/entity; XLSX xuất text an toàn.
- Phiếu nhiều loại thiết bị; duyệt/giữ chỗ, từ chối, bàn giao, trả toàn bộ và hủy đúng state machine. Khóa transaction bảo vệ tồn kho, audit và dashboard.
- Outbox lưu snapshot và transaction bền vững, retry, receipt, lease phục hồi và chống ghi trùng. Trang xác minh đọc contract, hiển thị PENDING/CONFIRMED/FAILED độc lập trạng thái nghiệp vụ.
- OCR đề xuất tên/mã/mô tả từ ảnh, có bước sửa và xác nhận. Cần cài model thực theo mục OCR trước khi demo tính năng AI.

Blockchain xác minh tính toàn vẹn snapshot; không chứng minh việc bàn giao hoặc tình trạng thiết bị ngoài đời. Hardhat reset làm mất bằng chứng trên local chain dù DB vẫn giữ tx hash. Xem [kiến trúc](docs/ARCHITECTURE.md).

## Kiểm tra

Các dependency pin trong `backend/requirements.lock`, hai `package-lock.json`. Các test ghi dữ liệu chỉ chạy trên DB tên kết thúc `_test`.

```bash
# Backend trên host, sau khi cài venv và tạo PostgreSQL labchain_test:
python3 scripts/backend.py --test-db alembic upgrade head
python3 scripts/backend.py --test-db pytest -q
backend/.venv/bin/ruff check backend
# Thêm bài kiểm tra RPC thật khi node đang chạy và đã deploy:
RUN_CHAIN_TESTS=1 python3 scripts/backend.py --test-db pytest -q
# Frontend:
npm --prefix frontend ci
npm --prefix frontend test
npm --prefix frontend run build
# Smart contract:
npm --prefix blockchain ci
npm --prefix blockchain test
```

Backend local: `python3 -m venv backend/.venv`, `backend/.venv/bin/pip install -r backend/requirements.lock`, `python3 scripts/backend.py` (wrapper tự đổi DB/RPC sang localhost, không in secrets). Frontend local `npm --prefix frontend run dev`. Contract local `cd blockchain && npm run node` và terminal khác `npm run deploy`. Không chạy host server trùng cổng container.

## OCR trong Docker

EasyOCR + PyTorch CPU được cài sẵn trong image `labchain-backend-ocr:dev`. Service `ocr-init` tải và nạp thử model trước khi API khởi động. Cache nằm trong volume `ocr_models`, dùng chung với backend, không cần lấy model từ máy phát triển. Backend Docker luôn bật OCR, kể cả `.env` cũ có `OCR_ENABLED=false`.

```bash
docker compose logs ocr-init
docker compose logs --tail=100 backend
# Kiểm tra lại cache nếu lần tải đầu bị gián đoạn:
docker compose run --rm ocr-init
```

Model mặc định đọc en/vi; sửa `OCR_LANGUAGES` trong `.env` rồi chạy lại script nếu cần ngôn ngữ khác. File `docker-compose.ocr.yml` được giữ để tương thích lệnh cũ; OCR đã có trong Compose chính. Ảnh mẫu: [equipment-label.png](docs/samples/equipment-label.png).

Phát triển OCR ngoài Docker vẫn được hỗ trợ bằng venv và `backend/requirements-ocr.lock`; không bắt buộc cho triển khai.

## Tài liệu

[API](docs/API.md) · [ERD](docs/ERD.md) · [Kiến trúc](docs/ARCHITECTURE.md) · [Quyết định](docs/DECISIONS.md) · [Hai kịch bản demo](docs/DEMO_SCRIPT.md) · [Backup/restore và vận hành](docs/OPERATIONS.md).

## Trạng thái kiểm chứng

- Docker full-stack đã build/khởi động; migrate và chain-deploy exit 0; health/readiness thành công.
- Backend: 25 tests pass trên host, bật cả RPC thật và OCR model thật. Python 3.12 container: 24 pass, 1 OCR opt-in skip. Concurrency, outbox/nonce recovery và worker subprocess có test.
- Frontend: 6 tests pass (có bước người dùng sửa/xác nhận OCR trước khi áp dụng); TypeScript và production build pass trên host và Node 24 trong container.
- Contract: 5 tests pass trên host và container. npm audit hai package không còn advisory sau khi pin dependency vá lỗi.
- HTTP smoke qua frontend proxy: PASS; duyệt/bàn giao/trả, hai bằng chứng VERIFIED, tồn kho hoàn lại. Kết quả: [smoke-result.json](docs/smoke-result.json).
- Migration test DB: downgrade về bootstrap, upgrade head và Alembic check không có schema drift.
- Các kết quả cũ ở trên được ghi nhận ngày 2026-11-12. Kiểm chứng cấu hình Docker gồm OCR và Nginx mới: [docker-validation.json](docs/docker-validation.json).

Kết quả kiểm chứng: [validation-result.json](docs/validation-result.json). Chi tiết tiến độ được cập nhật trong PROJECT_PLAN. Các bản build có cảnh báo kích thước chunk lớn của UI library; build vẫn thành công.
