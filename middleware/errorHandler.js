// Xử lý đường dẫn API không tồn tại
function notFound(req, res) {
  res.status(404).json({ error: 'Khong tim thay API nay' });
}

// Bắt mọi lỗi phát sinh trong quá trình xử lý
function errorHandler(err, req, res, next) {
  console.error(err);

  // Lỗi từ multer (upload file)
  if (err.name === 'MulterError') {
    return res.status(400).json({ error: 'Loi upload: ' + err.message });
  }

  // Lỗi vi phạm ràng buộc CSDL (ví dụ trùng email)
  if (err.code === 'SQLITE_CONSTRAINT_UNIQUE') {
    return res.status(409).json({ error: 'Du lieu da ton tai' });
  }

  const status = err.status || 500;
  res.status(status).json({ error: err.message || 'Loi may chu' });
}

module.exports = { notFound, errorHandler };