require('dotenv').config();
const express = require('express');
const cors = require('cors');
const path = require('path');
const db = require('./db');
const { notFound, errorHandler } = require('./middleware/errorHandler');
const authRoutes = require('./routes/auth.routes');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware chung
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Phục vụ giao diện (HTML/CSS/JS) và ảnh upload
app.use(express.static(path.join(__dirname, 'public')));
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));

// Route kiểm tra server
app.get('/api/health', (req, res) => {
  res.json({ ok: true, message: 'Server dang chay', time: new Date().toISOString() });
});

// Route kiểm tra CSDL
app.get('/api/db-check', (req, res) => {
  const tables = db
    .prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    .all();
  res.json({ tables: tables.map((t) => t.name) });
});

// Các nhóm route (thêm route mới vào đây, TRƯỚC notFound)
app.use('/api/auth', authRoutes);

// Báo lỗi khi gọi đường dẫn API không tồn tại
app.use('/api', notFound);

// Bắt lỗi chung
app.use(errorHandler);

app.listen(PORT, () => {
  console.log(`Server chay tai http://localhost:${PORT}`);
});