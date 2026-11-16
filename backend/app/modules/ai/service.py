import re
from functools import lru_cache
from io import BytesIO
from threading import Lock

from app.core.config import get_settings
from app.core.errors import AppError

_lock = Lock()


@lru_cache(maxsize=1)
def reader():
    import easyocr
    import torch

    torch.set_num_threads(2)
    return easyocr.Reader(get_settings().ocr_languages, gpu=False, verbose=False)


def recognize(image):
    stream = BytesIO()
    image.thumbnail((1600, 1600))
    image.save(stream, "PNG")
    with _lock:
        result = reader().readtext(stream.getvalue(), detail=1, paragraph=False, workers=0)
    return [
        {"text": str(item[1]), "confidence": round(float(item[2]), 4)}
        for item in result
        if str(item[1]).strip()
    ]


def parse(lines):
    text = "\n".join(x["text"] for x in lines)
    # Suggestions come only from observed text. No invented type, quantities or price.
    code = re.search(
        r"(?:model|s/n|serial|mã)\s*[:#]?\s*([A-Za-z0-9][A-Za-z0-9._-]{1,79})", text, re.IGNORECASE
    )
    return {
        "name": lines[0]["text"][:200] if lines else None,
        "code_candidate": code.group(1) if code else None,
        "product_type": None,
        "description": text[:10000] or None,
    }


def extract(image):
    if not get_settings().ocr_enabled:
        raise AppError(503, "OCR_DISABLED", "OCR chưa bật. Xem hướng dẫn bật OCR trong README.")
    try:
        lines = recognize(image)
    except (ImportError, ModuleNotFoundError):
        raise AppError(
            503, "OCR_NOT_INSTALLED", "Chưa cài dependency OCR thực; xem hướng dẫn OCR"
        ) from None
    except Exception:
        raise AppError(
            503,
            "OCR_UNAVAILABLE",
            "Không thể chạy model OCR; kiểm tra model và kết nối tải lần đầu",
        ) from None
    confidence = round(sum(x["confidence"] for x in lines) / len(lines), 4) if lines else None
    return {
        "engine": "EasyOCR (CPU)",
        "raw_text": "\n".join(x["text"] for x in lines),
        "confidence": confidence,
        "lines": lines,
        "suggestions": parse(lines),
        "requires_confirmation": True,
        "warning": "Không đọc được chữ, hãy nhập thủ công"
        if not lines
        else "Kiểm tra và chỉnh sửa kết quả trước khi lưu",
    }
