const jwt = require('jsonwebtoken');
const db = require('../db');

// Bắt buộc đăng nhập: đọc token từ header "Authorization: Bearer <token>"
function requireAuth(req, res, next) {
  const header = req.headers.authorization || '';
  const token = header.startsWith('Bearer ') ? header.slice(7) : null;

  if (!token) {
    return res.status(401).json({ error: 'Chua dang nhap' });
  }

  try {
    const payload = jwt.verify(token, process.env.JWT_SECRET);

    // Lấy lại thông tin người dùng từ CSDL (đảm bảo tài khoản còn tồn tại)
    const user = db
      .prepare('SELECT id, full_name, email, phone, role FROM users WHERE id = ?')
      .get(payload.id);

    if (!user) {
      return res.status(401).json({ error: 'Tai khoan khong ton tai' });
    }

    req.user = user;
    next();
  } catch (err) {
    return res.status(401).json({ error: 'Token khong hop le hoac het han' });
  }
}

// Chỉ cho admin đi tiếp (dùng SAU requireAuth)
function requireAdmin(req, res, next) {
  if (!req.user || req.user.role !== 'admin') {
    return res.status(403).json({ error: 'Chi admin moi duoc phep' });
  }
  next();
}

module.exports = { requireAuth, requireAdmin };