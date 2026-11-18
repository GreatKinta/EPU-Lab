const express = require('express');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const db = require('../db');
const { requireAuth } = require('../middleware/auth');
const { validateBody, isValidEmail, isValidPassword } = require('../middleware/validate');

const router = express.Router();

// Tạo token đăng nhập
function signToken(user) {
  return jwt.sign({ id: user.id, role: user.role }, process.env.JWT_SECRET, {
    expiresIn: process.env.JWT_EXPIRES_IN || '7d',
  });
}

// ===== ĐĂNG KÝ =====
// POST /api/auth/register
router.post(
  '/register',
  validateBody(['full_name', 'email', 'password']),
  (req, res) => {
    const { full_name, email, password, phone } = req.body;

    if (!isValidEmail(email)) {
      return res.status(400).json({ error: 'Email khong hop le' });
    }
    if (!isValidPassword(password)) {
      return res.status(400).json({ error: 'Mat khau toi thieu 6 ky tu' });
    }

    const normalizedEmail = email.trim().toLowerCase();

    const exists = db.prepare('SELECT id FROM users WHERE email = ?').get(normalizedEmail);
    if (exists) {
      return res.status(409).json({ error: 'Email da duoc su dung' });
    }

    const hash = bcrypt.hashSync(password, 10);
    const result = db
      .prepare(
        'INSERT INTO users (full_name, email, password_hash, phone, role) VALUES (?, ?, ?, ?, ?)'
      )
      .run(full_name.trim(), normalizedEmail, hash, phone || null, 'user');

    const user = db
      .prepare('SELECT id, full_name, email, phone, role FROM users WHERE id = ?')
      .get(result.lastInsertRowid);

    res.status(201).json({ token: signToken(user), user });
  }
);

// ===== ĐĂNG NHẬP =====
// POST /api/auth/login
router.post('/login', validateBody(['email', 'password']), (req, res) => {
  const { email, password } = req.body;
  const normalizedEmail = email.trim().toLowerCase();

  const row = db.prepare('SELECT * FROM users WHERE email = ?').get(normalizedEmail);

  // Cùng một thông báo cho cả "sai email" và "sai mật khẩu" để tránh lộ thông tin
  if (!row || !bcrypt.compareSync(password, row.password_hash)) {
    return res.status(401).json({ error: 'Email hoac mat khau khong dung' });
  }

  const user = {
    id: row.id,
    full_name: row.full_name,
    email: row.email,
    phone: row.phone,
    role: row.role,
  };

  res.json({ token: signToken(user), user });
});

// ===== LẤY THÔNG TIN NGƯỜI ĐANG ĐĂNG NHẬP =====
// GET /api/auth/me  (dùng để kiểm tra token hoạt động)
router.get('/me', requireAuth, (req, res) => {
  res.json({ user: req.user });
});
// ===== CẬP NHẬT HỒ SƠ =====
// PUT /api/auth/profile
router.put('/profile', requireAuth, validateBody(['full_name']), (req, res) => {
  const { full_name, phone } = req.body;

  db.prepare('UPDATE users SET full_name = ?, phone = ? WHERE id = ?').run(
    full_name.trim(),
    phone || null,
    req.user.id
  );

  const user = db
    .prepare('SELECT id, full_name, email, phone, role FROM users WHERE id = ?')
    .get(req.user.id);

  res.json({ user });
});

// ===== ĐỔI MẬT KHẨU =====
// PUT /api/auth/password
router.put(
  '/password',
  requireAuth,
  validateBody(['old_password', 'new_password']),
  (req, res) => {
    const { old_password, new_password } = req.body;

    if (!isValidPassword(new_password)) {
      return res.status(400).json({ error: 'Mat khau moi toi thieu 6 ky tu' });
    }

    const row = db.prepare('SELECT password_hash FROM users WHERE id = ?').get(req.user.id);

    if (!bcrypt.compareSync(old_password, row.password_hash)) {
      return res.status(401).json({ error: 'Mat khau cu khong dung' });
    }

    const hash = bcrypt.hashSync(new_password, 10);
    db.prepare('UPDATE users SET password_hash = ? WHERE id = ?').run(hash, req.user.id);

    res.json({ message: 'Doi mat khau thanh cong' });
  }
);

module.exports = router;