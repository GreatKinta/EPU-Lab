# API

OpenAPI tương tác: http://localhost:8000/docs. Mọi route nghiệp vụ dưới `/api/v1`.

1. `POST /auth/login` với JSON `{ "email": "staff@labchain.local", "password": "<DEMO_PASSWORD từ .env>" }`.
2. Gắn `Authorization: Bearer <access_token>` cho các request sau. Token hết hạn sau 30 phút; token chỉ lưu trong bộ nhớ trình duyệt.
3. `GET /equipment?page=1&page_size=15&search=Arduino&sort=code` → `{items,total,page,page_size}`; chỉ nhận cỡ trang 10/15. `sort` cho name/code/price/created_at/quantity_total, tiền tố `-` để giảm dần. Tìm kiếm không phân biệt hoa thường; `%` và `_` được tìm như ký tự thường.
4. CRUD, duplicate/bulk, import/export/template theo contract trong PROJECT_PLAN. Tất cả thao tác ghi thiết bị chỉ dành cho staff/admin. Export theo bộ lọc search/product_type; XLSX ghi rõ kiểu text để tránh công thức.
5. Import multipart field `file`; `format=xlsx|json|xml`; `dry_run=true` mặc định chỉ kiểm tra và xem trước tối đa 20 dòng. `dry_run=false` xác nhận nhập nguyên lô; lỗi ở bất kỳ dòng nào không lưu dòng nào. Dòng lỗi đánh số bản ghi dữ liệu từ 1; XLSX dùng sheet đầu, bỏ dòng trống và không tính header. Tối đa 1.000 dòng, 5 MiB; tổng dung lượng ZIP XLSX giải nén tối đa 25 MiB.
6. Xóa và xóa nhiều luôn lưu trữ mềm. ID/mã vẫn giữ để đối chiếu lịch sử; không tái sử dụng mã đã lưu trữ. Lô có bất kỳ thiết bị đang giữ chỗ nào bị từ chối toàn bộ. Nhân bản giữ dữ liệu mô tả, ảnh; ID, mã, timestamp mới và giữ chỗ bằng 0.
7. Ảnh: `POST /equipment/{id}/image`, đọc qua `GET` cùng URL có xác thực. Không chấp nhận `image_path` từ client. Tên file ngẫu nhiên, chuyển JPEG và bỏ metadata, giới hạn pixel và kích thước.

Ví dụ tạo phiếu (thay UUID thiết bị hợp lệ, dùng thời gian tương lai có timezone):

```json
{
  "due_at": "2027-01-15T10:00:00+07:00",
  "items": [{"equipment_id": "<uuid>", "quantity": 2}]
}
```

`POST /loans` hỗ trợ header `Idempotency-Key` tối đa 100 ký tự. Cùng khóa/cùng user/cùng nội dung trả lại phiếu; khác nội dung trả 409. Phiếu chờ duyệt chưa giữ chỗ.

Các lệnh `/loans/{id}/approve|reject|handover|return|cancel` dùng POST. Reject yêu cầu `{reason:"..."}`; approve cho phép `{due_at:"..."}` để chỉnh hạn trả, được ghi audit. Sai trạng thái trả 409; thiếu quyền 403. Student chỉ xem phiếu của mình và hủy khi PENDING. Staff có thể hủy APPROVED, giải phóng giữ chỗ. Tất cả trả cùng lúc.

`GET /loans/{id}/verify`: VERIFIED/MISMATCH/NOT_RECORDED/PENDING/CHAIN_UNAVAILABLE. Snapshot gốc, hash tính lại, hash trên contract và tx hash được trả độc lập. `POST /blockchain/events/{id}/retry` dành cho staff/admin, chỉ nhận sự kiện FAILED.

`POST /ai/ocr/equipment`: multipart file ảnh, staff/admin; trả raw_text, confidence, suggestions, requires_confirmation. Không ghi thiết bị. OCR chưa bật/model chưa cài trả 503 có mã cụ thể.

`/dashboard/summary` và `/audit/events` lọc quyền; admin có `/users` GET/POST và `/users/{id}` PATCH. Người dùng không thể tự khóa/hạ quyền tài khoản admin đang dùng.

Lỗi nghiệp vụ: `{code,message,details?}`; validation 422, authentication 401, authorization 403, missing 404, conflict 409, file size 413, service unavailable 503.
