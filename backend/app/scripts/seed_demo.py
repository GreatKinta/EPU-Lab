"""Idempotent development-only seed; credentials are supplied through .env."""

import argparse

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.security import password_hash
from app.modules.identity.models import User
from app.modules.inventory.models import Equipment


def main():
    settings = get_settings()
    if settings.app_env != "development" or len(settings.demo_password) < 12:
        raise SystemExit("Set APP_ENV=development and DEMO_PASSWORD (at least 12 chars)")
    names = [
        "Arduino Uno R3",
        "Raspberry Pi 5",
        "Máy hiện sóng Rigol",
        "Đồng hồ vạn năng",
        "Bộ nguồn DC",
        "Cảm biến nhiệt độ",
        "Máy in 3D",
        "Camera Logitech",
        "Máy chiếu Epson",
        "Laptop Dell",
        "ESP32 DevKit",
        "Breadboard",
        "Mỏ hàn Hakko",
        "Bộ dụng cụ cơ khí",
        "Cảm biến siêu âm",
        "Máy phát tín hiệu",
        "Kính hiển vi",
        "Cân điện tử",
        "Bộ vi điều khiển STM32",
        "Robot học tập",
        "Máy đo LCR",
        "Module Bluetooth",
        "Bộ động cơ bước",
        "Bộ nguồn Arduino",
        "Cáp đo oscilloscope",
        "Màn hình LCD",
        "Bộ cảm biến ánh sáng",
        "Máy quét mã vạch",
        "Bộ dụng cụ quang học",
        "Máy đo độ ẩm",
    ]
    with SessionLocal.begin() as db:
        for role, name in [
            ("admin", "Quản trị viên"),
            ("staff", "Nguyễn Minh Anh"),
            ("student", "Trần Hoàng Nam"),
        ]:
            email = f"{role}@labchain.local"
            if not db.scalar(select(User).where(User.email == email)):
                db.add(
                    User(
                        email=email,
                        full_name=name,
                        role=role,
                        password_hash=password_hash.hash(settings.demo_password),
                    )
                )
        for index, name in enumerate(names, 1):
            code = f"EQ-{index:04}"
            if not db.scalar(select(Equipment).where(Equipment.code == code)):
                db.add(
                    Equipment(
                        code=code,
                        name=name,
                        product_type=["Vi điều khiển", "Đo lường", "Tin học", "Dụng cụ"][index % 4],
                        quantity_total=5 + index % 10,
                        unit="cái",
                        price=str(100000 + index * 75000),
                        description=f"Thiết bị phục vụ thực hành tại phòng Lab · Kệ {index % 5 + 1}",
                    )
                )
    print("Seed completed: 3 accounts and 30 equipment (existing records preserved)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--if-development", action="store_true")
    args = parser.parse_args()
    if args.if_development and (
        get_settings().app_env != "development" or not get_settings().demo_password
    ):
        print("Demo seed skipped: development credentials are not configured")
    else:
        main()
