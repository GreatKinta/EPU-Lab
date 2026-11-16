# Triển khai và vận hành bằng Docker

## Máy mới

Cài Docker Engine + Compose bản mới (hỗ trợ `up --wait`) hoặc Docker Desktop (Linux containers), mở Docker rồi chép/clone mã nguồn dự án. Máy không cần Python, Node.js, npm, PostgreSQL hoặc EasyOCR. Image ứng dụng cố định `linux/amd64` vì dependency native được pin theo kiến trúc này. Docker Desktop trên ARM cần bật hỗ trợ giả lập amd64; Linux ARM cần cài hỗ trợ binfmt/QEMU tương ứng. Kiểm chứng hiện tại trên Linux x86_64, chưa kiểm chứng ARM hoặc Windows thực tế.

Linux/macOS: `./scripts/start.sh`. Windows PowerShell: `powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1`. Nếu không muốn chạy script, tại thư mục dự án:

```bash
# Linux/macOS:
LOCAL_UID=$(id -u) LOCAL_GID=$(id -g) docker compose -f docker-compose.setup.yml run --rm setup
# Windows PowerShell:
# docker compose -f docker-compose.setup.yml run --rm setup

docker compose up --build -d --wait --wait-timeout 600
```

Container setup sinh `.env` và secrets riêng nếu chưa có. Mặc định UID/GID 1000; script Linux/macOS tự dùng UID/GID người gọi. `migrate`, `seed`, `chain-deploy`, `ocr-init` là các tác vụ một lần: trạng thái `Exited (0)` là bình thường. API chờ migration, seed và model OCR; worker chờ API và deploy contract. Seed chỉ chạy khi `APP_ENV=development` và có `DEMO_PASSWORD`, giữ nguyên tài khoản/thiết bị đã tồn tại.

Model OCR cần mạng lần đầu và được cache vào volume `ocr_models`; lần sau không phải tải lại. Build image cũng cần mạng tải dependency. Đây là triển khai demo/học tập, không phải cấu hình blockchain công khai hoặc production Internet.

Mặc định mở `http://localhost:5173`. Để truy cập từ máy khác trong LAN, sửa `.env`:

```dotenv
WEB_BIND_ADDRESS=0.0.0.0
WEB_PORT=5173
```

Chạy lại script, truy cập `http://IP_MAY_CHU:5173` và cho phép cổng web trong firewall nếu cần. Nginx phục vụ frontend build và proxy `/api/` tới backend; không cần sửa URL API trong frontend. Cổng DB 5432, API trực tiếp 8000 và RPC 8545 chỉ mở localhost.

## Lệnh thường dùng

Các ví dụ dùng context Docker hiện tại. Nếu máy dùng Docker Desktop Linux với context mặc định chưa hoạt động, thêm `--context desktop-linux` sau `docker`; script Linux/macOS tự phát hiện.

```bash
docker compose ps -a
docker compose logs --tail=100 backend worker ocr-init
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.scripts.seed_demo
docker compose run --rm ocr-init
# Dừng và giữ named volumes:
docker compose down
# Khởi động lại và chờ sẵn sàng:
docker compose up -d --wait --wait-timeout 600
```

Không dùng `down -v` khi cần giữ dữ liệu: lệnh đó xóa DB, ảnh, model và cấu hình signer. Không in `.env` hoặc private signer config vào logs.

Hardhat là chain thử nghiệm trong bộ nhớ: restart/dừng node xóa toàn bộ lịch sử on-chain. `chain_config` chỉ lưu địa chỉ, ABI và khóa signer, không lưu state blockchain. Compose chạy lại deploy khi `up`; nếu chỉ restart node, chạy `docker compose run --rm chain-deploy` trước khi tiếp tục thao tác blockchain. Bằng chứng cũ trong DB sẽ không được xác minh sau khi chain reset. Muốn giữ lịch sử on-chain qua restart cần thay Hardhat bằng node có lưu state; cấu hình này giữ nguyên công nghệ Hardhat của dự án.

## Chuyển dự án và dữ liệu

Chép mã nguồn cùng Dockerfile, Compose, lockfiles và scripts. Không chép `.venv`, `node_modules`, cache build hoặc `runtime/compose.build-dns.yml`. Trên máy mới, script tạo `.env` và dữ liệu demo độc lập. Không đưa `.env` hoặc backup chứa signer vào Git.

Nếu muốn chuyển dữ liệu cũ, cần chuyển **cùng bộ**: DB, uploads, chain_config và `.env` tương ứng. Khôi phục DB có tài khoản cũ sẽ giữ mật khẩu cũ, seed không thay mật khẩu. OCR model có thể tải lại; chuyển volume model nếu máy đích không có mạng.

Backup SQL (Bash, tại thư mục dự án):

```bash
mkdir -p backups
chmod 700 backups
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > backups/labchain.sql
chmod 600 backups/labchain.sql
```

Restore vào DB **trống**, sau khi đã có backup cho dữ liệu đích nếu cần:

```bash
docker compose exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" "$POSTGRES_DB"' < backups/labchain.sql
```

Ví dụ backup volumes ảnh và signer khi đã dừng API/worker để dữ liệu không thay đổi. Dừng/restart backend bằng `--no-deps` để tránh khởi động lại các tác vụ seed/migration:

```bash
docker compose stop backend worker
docker compose run --rm --no-deps -T --user 0 -v "$PWD/backups:/backup" backend sh -c 'tar czf /backup/files.tgz -C /data uploads && tar czf /backup/signer.tgz -C /chain . && chmod 600 /backup/*.tgz'
docker compose up -d --no-deps backend worker
```

Chuyển `.env`, SQL và backup qua kênh riêng tư. Không thể phục hồi lịch sử Hardhat bằng các backup này. Để phục hồi file vào volumes trên máy đích, dừng API/worker, giải nén `files.tgz` vào `/data` và `signer.tgz` vào `/chain` bằng container maintenance có quyền ghi các volume. Compose backend gắn signer chỉ đọc để hạn chế sửa nhầm; có thể dùng `chain-deploy` (gắn volume signer có quyền ghi) cho thao tác phục hồi signer. Không ghi đè volumes đang dùng mà chưa sao lưu.

## Lỗi mạng Docker Desktop

Nếu build báo `EAI_AGAIN` khi tải npm/pip, chạy `./scripts/start.sh --dns-workaround`. Script cũng chạy công cụ tạo override bên trong container; không cần Python host. File `runtime/compose.build-dns.yml` được tạo từ DNS mới mỗi lần; không mang IP này sang máy khác. Nếu DNS của container setup cũng không hoạt động, cần sửa DNS/kết nối Docker Desktop trước. Không thay DNS hệ điều hành bằng script.
