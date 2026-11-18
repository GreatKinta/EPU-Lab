// Kiểm tra các trường bắt buộc có trong req.body
// Dùng: validateBody(['email', 'password'])
function validateBody(requiredFields) {
  return (req, res, next) => {
    const missing = requiredFields.filter((field) => {
      const value = req.body ? req.body[field] : undefined;
      return value === undefined || value === null || String(value).trim() === '';
    });

    if (missing.length > 0) {
      return res.status(400).json({
        error: 'Thieu du lieu bat buoc',
        fields: missing,
      });
    }
    next();
  };
}

// Kiểm tra định dạng email
function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(email));
}

// Mật khẩu tối thiểu 6 ký tự
function isValidPassword(password) {
  return typeof password === 'string' && password.length >= 6;
}

module.exports = { validateBody, isValidEmail, isValidPassword };