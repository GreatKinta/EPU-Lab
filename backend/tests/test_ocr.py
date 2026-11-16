import os
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import func, select

from app.core.config import get_settings
from app.modules.ai import service
from app.modules.inventory.models import Equipment


def sample():
    stream = BytesIO()
    Image.new("RGB", (100, 100), "white").save(stream, "PNG")
    return stream.getvalue()


def test_ocr_validation_rbac_disabled(client, accounts, monkeypatch):
    path = "/api/v1/ai/ocr/equipment"
    assert (
        client.post(
            path, files={"file": ("a.png", sample(), "image/png")}, headers=accounts["student"]
        ).status_code
        == 403
    )
    assert (
        client.post(
            path, files={"file": ("a.png", b"bad", "image/png")}, headers=accounts["staff"]
        ).status_code
        == 422
    )
    monkeypatch.setattr(get_settings(), "ocr_enabled", False)
    assert (
        client.post(
            path, files={"file": ("a.png", sample(), "image/png")}, headers=accounts["staff"]
        ).json()["code"]
        == "OCR_DISABLED"
    )


def test_ocr_suggestions_no_automatic_save(client, accounts, db, monkeypatch):
    monkeypatch.setattr(get_settings(), "ocr_enabled", True)
    monkeypatch.setattr(
        service,
        "recognize",
        lambda image: [
            {"text": "Arduino Uno R3", "confidence": 0.99},
            {"text": "Model: UNO-R3", "confidence": 0.9},
        ],
    )
    response = client.post(
        "/api/v1/ai/ocr/equipment",
        files={"file": ("a.png", sample(), "image/png")},
        headers=accounts["staff"],
    )
    assert response.json()["suggestions"]["code_candidate"] == "UNO-R3"
    assert response.json()["requires_confirmation"] is True
    assert db.scalar(select(func.count()).select_from(Equipment)) == 0
    monkeypatch.setattr(service, "recognize", lambda image: [])
    result = client.post(
        "/api/v1/ai/ocr/equipment",
        files={"file": ("a.png", sample(), "image/png")},
        headers=accounts["staff"],
    ).json()
    assert result["confidence"] is None and result["suggestions"]["name"] is None


@pytest.mark.skipif(
    os.getenv("RUN_OCR_TESTS") != "1", reason="Real OCR model opt-in: RUN_OCR_TESTS=1"
)
def test_real_model_sample(client, accounts, db, monkeypatch):
    monkeypatch.setattr(get_settings(), "ocr_enabled", True)
    content = (
        Path(__file__).resolve().parents[2] / "docs/samples/equipment-label.png"
    ).read_bytes()
    response = client.post(
        "/api/v1/ai/ocr/equipment",
        files={"file": ("label.png", content, "image/png")},
        headers=accounts["staff"],
    )
    assert response.status_code == 200, response.text
    assert "ARDUINO" in response.json()["raw_text"].upper()
    assert "UNO" in response.json()["raw_text"].upper()
    assert db.scalar(select(func.count()).select_from(Equipment)) == 0
