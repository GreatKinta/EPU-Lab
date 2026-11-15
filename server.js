require('dotenv').config();
const express = require('express');
const cors = require('cors');
const path = require('path');

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

// Báo lỗi khi gọi đường dẫn API không tồn tại
app.use('/api', (req, res) => {
  res.status(404).json({ error: 'Khong tim thay API nay' });
});

// Bắt lỗi chung
app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: 'Loi may chu' });
});

app.listen(PORT, () => {
  console.log(`Server chay tai http://localhost:${PORT}`);
});