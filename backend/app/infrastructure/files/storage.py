import warnings
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings
from app.core.errors import AppError

Image.MAX_IMAGE_PIXELS = 16_000_000


async def read_upload(file: UploadFile):
    content = await file.read(get_settings().max_upload_bytes + 1)
    if len(content) > get_settings().max_upload_bytes:
        raise AppError(413, "FILE_TOO_LARGE", "Tệp vượt quá giới hạn 5 MB")
    if not content:
        raise AppError(422, "EMPTY_FILE", "Tệp rỗng")
    return content


def validate_image(content: bytes, mime: str):
    formats = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as source:
                if formats.get(source.format) != mime or mime not in formats.values():
                    raise AppError(
                        422, "INVALID_IMAGE", "Chỉ nhận ảnh PNG, JPEG, WebP đúng định dạng"
                    )
                source.load()
                return source.convert("RGB")
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        ValueError,
    ):
        raise AppError(422, "INVALID_IMAGE", "Ảnh hỏng hoặc kích thước ảnh quá lớn") from None


def save_image(image):
    directory = get_settings().upload_dir
    directory.mkdir(parents=True, exist_ok=True)
    name = f"{uuid4().hex}.jpg"
    image.thumbnail((2000, 2000))
    image.save(directory / name, "JPEG", quality=90)
    return name


def image_file(name):
    if not name or Path(name).name != name or not name.endswith(".jpg"):
        raise AppError(404, "NOT_FOUND", "Không tìm thấy ảnh")
    path = get_settings().upload_dir / name
    if not path.is_file():
        raise AppError(404, "NOT_FOUND", "Không tìm thấy ảnh")
    return path
