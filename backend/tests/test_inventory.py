import json
from io import BytesIO
from uuid import uuid4

import pytest
from openpyxl import load_workbook
from PIL import Image

from app.modules.inventory import transfers


def payload(code="EQ-TEST", **kw):
    return {
        "code": code,
        "name": "Arduino thử nghiệm",
        "product_type": "Điện tử",
        "quantity_total": 5,
        "unit": "cái",
        "price": "150000.00",
        "description": "Mô tả có thể tìm",
        **kw,
    }


def create(client, accounts, **kw):
    response = client.post("/api/v1/equipment", json=payload(**kw), headers=accounts["staff"])
    assert response.status_code == 201, response.text
    return response.json()


def test_auth_and_permissions(client, accounts):
    assert client.get("/api/v1/equipment").status_code == 401
    assert (
        client.post("/api/v1/equipment", json=payload(), headers=accounts["student"]).status_code
        == 403
    )
    assert client.get("/api/v1/users", headers=accounts["staff"]).status_code == 403
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "staff@example.test", "password": "test-password-12345"},
    )
    assert response.status_code == 200
    assert "password_hash" not in response.text
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": "staff@example.test", "password": "bad"}
        ).status_code
        == 401
    )
    for _ in range(8):
        client.post("/api/v1/auth/login", json={"email": "none@example.test", "password": "bad"})
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": "none@example.test", "password": "bad"}
        ).status_code
        == 429
    )


def test_crud_pagination_search_sort(client, accounts):
    for i in range(16):
        create(client, accounts, code=f"EQ-{i:02}")
    result = client.get(
        "/api/v1/equipment?page_size=15&sort=code", headers=accounts["student"]
    ).json()
    assert result["total"] == 16 and len(result["items"]) == 15
    result2 = client.get(
        "/api/v1/equipment?page=2&page_size=15&sort=code", headers=accounts["staff"]
    ).json()
    assert len(result2["items"]) == 1
    assert (
        client.get("/api/v1/equipment?page_size=12", headers=accounts["staff"]).status_code == 422
    )
    first = result["items"][0]
    path = f"/api/v1/equipment/{first['id']}"
    assert (
        client.patch(
            path, json={"quantity_total": 8, "price": "12.34"}, headers=accounts["staff"]
        ).json()["quantity_available"]
        == 8
    )
    assert client.get(path, headers=accounts["student"]).json()["price"] == "12.34"
    assert (
        client.get("/api/v1/equipment?search=mô%20tả", headers=accounts["staff"]).json()["total"]
        == 16
    )
    assert (
        client.get("/api/v1/equipment?search=%25", headers=accounts["staff"]).json()["total"] == 0
    )
    assert client.delete(path, headers=accounts["student"]).status_code == 403
    assert client.delete(path, headers=accounts["staff"]).status_code == 200
    assert client.get(path, headers=accounts["staff"]).status_code == 404


def test_duplicates_bulk_atomic_validation(client, accounts):
    item = create(client, accounts)
    path = f"/api/v1/equipment/{item['id']}"
    assert (
        client.post("/api/v1/equipment", json=payload(), headers=accounts["staff"]).status_code
        == 409
    )
    copy = client.post(path + "/duplicate", headers=accounts["staff"]).json()
    assert copy["id"] != item["id"] and copy["code"] != item["code"]
    assert copy["created_at"] != item["created_at"]
    ids = [item["id"], copy["id"]]
    copies = client.post(
        "/api/v1/equipment/bulk-duplicate", json={"ids": ids}, headers=accounts["staff"]
    ).json()
    assert len(copies) == 2 and len({c["code"] for c in copies}) == 2
    assert (
        client.post(
            "/api/v1/equipment/bulk-delete",
            json={"ids": [item["id"], str(uuid4())]},
            headers=accounts["staff"],
        ).status_code
        == 404
    )
    assert client.get(path, headers=accounts["staff"]).status_code == 200
    assert (
        client.patch(path, json={"quantity_total": -1}, headers=accounts["staff"]).status_code
        == 422
    )
    assert (
        client.patch(path, json={"quantity_reserved": 100}, headers=accounts["staff"]).status_code
        == 422
    )
    assert client.patch(path, json={"name": None}, headers=accounts["staff"]).status_code == 422


@pytest.mark.parametrize("format", ["xlsx", "json", "xml"])
def test_transfer_roundtrip_preview_confirm(client, accounts, format):
    body = transfers.encode([payload()], format)
    path = f"/api/v1/equipment/import?format={format}"
    preview = client.post(path, files={"file": (f"file.{format}", body)}, headers=accounts["staff"])
    assert preview.status_code == 200, preview.text
    assert preview.json()["valid"] and preview.json()["imported"] == 0
    assert client.get("/api/v1/equipment", headers=accounts["staff"]).json()["total"] == 0
    imported = client.post(
        path + "&dry_run=false", files={"file": (f"file.{format}", body)}, headers=accounts["staff"]
    )
    assert imported.json()["imported"] == 1
    exported = client.get(f"/api/v1/equipment/export?format={format}", headers=accounts["staff"])
    row = transfers.decode(exported.content, format)[0]
    assert row["code"] == "EQ-TEST" and row["name"] == payload()["name"]
    duplicate = client.post(path, files={"file": ("file", body)}, headers=accounts["staff"]).json()
    assert duplicate["errors"][0]["row"] == 1
    assert (
        client.get(
            f"/api/v1/equipment/import-template?format={format}", headers=accounts["staff"]
        ).status_code
        == 200
    )


def test_import_invalid_atomic_xxe_formula_size(client, accounts):
    body = json.dumps([payload(), payload(code="EQ-BAD", quantity_total=-1)]).encode()
    response = client.post(
        "/api/v1/equipment/import?format=json&dry_run=false",
        files={"file": ("bad.json", body)},
        headers=accounts["staff"],
    )
    assert response.status_code == 422 and response.json()["details"][0]["row"] == 2
    assert client.get("/api/v1/equipment", headers=accounts["staff"]).json()["total"] == 0
    xml = b'<!DOCTYPE equipment [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><equipment><item><name>&xxe;</name></item></equipment>'
    assert (
        client.post(
            "/api/v1/equipment/import?format=xml",
            files={"file": ("bad.xml", xml)},
            headers=accounts["staff"],
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/equipment/import?format=json",
            files={"file": ("huge.json", b"x" * 5242881)},
            headers=accounts["staff"],
        ).status_code
        == 413
    )
    content = transfers.encode([payload(name='=HYPERLINK("evil")')], "xlsx")
    workbook = load_workbook(BytesIO(content), data_only=False)
    assert workbook.active["B2"].data_type == "s"


def test_images_mime_signature_and_size(client, accounts):
    item = create(client, accounts)
    path = f"/api/v1/equipment/{item['id']}/image"
    assert (
        client.post(
            path,
            files={"file": ("bad.png", b"not an image", "image/png")},
            headers=accounts["staff"],
        ).status_code
        == 422
    )
    stream = BytesIO()
    Image.new("RGB", (40, 40), "white").save(stream, "PNG")
    assert (
        client.post(
            path,
            files={"file": ("../../photo.png", stream.getvalue(), "image/jpeg")},
            headers=accounts["staff"],
        ).status_code
        == 422
    )
    result = client.post(
        path,
        files={"file": ("../../photo.png", stream.getvalue(), "image/png")},
        headers=accounts["staff"],
    )
    assert result.status_code == 200 and "/" not in result.json()["image_path"]
    assert client.get(path).status_code == 401
    image = client.get(path, headers=accounts["student"])
    assert image.status_code == 200 and image.headers["content-type"] == "image/jpeg"


def test_admin_user_lifecycle_preserves_password_and_refreshes_permissions(client, accounts):
    password = "  exact-password-12345  "
    created = client.post(
        "/api/v1/users",
        json={
            "email": " NEW@example.test ",
            "full_name": "  New Student  ",
            "password": password,
            "role": "student",
        },
        headers=accounts["admin"],
    )
    assert created.status_code == 201, created.text
    user = created.json()
    assert user["full_name"] == "New Student" and user["email"] == "new@example.test"
    login = client.post(
        "/api/v1/auth/login", json={"email": "new@example.test", "password": password}
    )
    assert login.status_code == 200
    auth = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=auth).status_code == 200
    assert (
        client.patch(
            f"/api/v1/users/{user['id']}", json={"is_active": False}, headers=accounts["admin"]
        ).status_code
        == 200
    )
    assert client.get("/api/v1/auth/me", headers=auth).status_code == 401
    assert (
        client.patch(
            f"/api/v1/users/{accounts['admin_id']}",
            json={"role": "student"},
            headers=accounts["admin"],
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/users",
            json={
                "email": "bad@example.test",
                "full_name": " ",
                "password": "long-password-123",
                "role": "student",
            },
            headers=accounts["admin"],
        ).status_code
        == 422
    )
