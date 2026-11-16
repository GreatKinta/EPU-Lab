from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_inventory import create

from app.infrastructure.blockchain.models import OutboxEvent
from app.main import app
from app.modules.borrowing.models import Loan
from app.modules.inventory.models import Equipment


def loan(client, accounts, items, key=None):
    body = {
        "due_at": (datetime.now(UTC) + timedelta(days=3)).isoformat(),
        "items": [{"equipment_id": x["id"], "quantity": q} for x, q in items],
    }
    headers = {**accounts["student"], **({"Idempotency-Key": key} if key else {})}
    response = client.post("/api/v1/loans", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json(), body


def command(client, accounts, item, action, role="staff", body=None):
    return client.post(f"/api/v1/loans/{item['id']}/{action}", json=body, headers=accounts[role])


def test_full_workflow_rbac_history_double_commands(client, accounts, db):
    equipment = create(client, accounts)
    item, _ = loan(client, accounts, [(equipment, 3)])
    assert command(client, accounts, item, "approve", role="student").status_code == 403
    assert command(client, accounts, item, "return").status_code == 409
    assert command(client, accounts, item, "approve").status_code == 200
    assert command(client, accounts, item, "approve").status_code == 409
    assert db.get(Equipment, equipment["id"]).quantity_reserved == 3
    assert (
        client.delete(f"/api/v1/equipment/{equipment['id']}", headers=accounts["staff"]).status_code
        == 409
    )
    assert (
        client.patch(
            f"/api/v1/equipment/{equipment['id']}",
            json={"quantity_total": 2},
            headers=accounts["staff"],
        ).status_code
        == 409
    )
    assert command(client, accounts, item, "cancel", role="student").status_code == 403
    assert command(client, accounts, item, "handover").status_code == 200
    assert command(client, accounts, item, "cancel").status_code == 409
    assert command(client, accounts, item, "return").status_code == 200
    assert command(client, accounts, item, "return").status_code == 409
    db.expire_all()
    assert db.get(Equipment, equipment["id"]).quantity_reserved == 0
    assert db.scalar(select(func.count()).select_from(OutboxEvent)) == 2
    assert (
        client.delete(f"/api/v1/equipment/{equipment['id']}", headers=accounts["staff"]).status_code
        == 200
    )
    detail = client.get(f"/api/v1/loans/{item['id']}", headers=accounts["student"]).json()
    assert detail["items"][0]["code"] == equipment["code"] and len(detail["timeline"]) == 4


def test_approval_rollback_and_cancel(client, accounts, db):
    first = create(client, accounts, code="FIRST", quantity_total=1)
    second = create(client, accounts, code="SECOND", quantity_total=0)
    item, _ = loan(client, accounts, [(first, 1), (second, 1)])
    assert command(client, accounts, item, "approve").status_code == 409
    assert db.get(Equipment, first["id"]).quantity_reserved == 0
    assert db.scalar(select(func.count()).select_from(OutboxEvent)) == 0
    assert command(client, accounts, item, "cancel", role="student").status_code == 200
    assert command(client, accounts, item, "approve").status_code == 409
    good, _ = loan(client, accounts, [(first, 1)])
    assert command(client, accounts, good, "approve").status_code == 200
    assert command(client, accounts, good, "cancel").status_code == 200
    db.expire_all()
    assert db.get(Equipment, first["id"]).quantity_reserved == 0


def test_isolation_rejection_dates_idempotency(client, accounts):
    equipment = create(client, accounts)
    item, body = loan(client, accounts, [(equipment, 1)], "retry-key")
    again = client.post(
        "/api/v1/loans", json=body, headers={**accounts["student"], "Idempotency-Key": "retry-key"}
    )
    assert again.status_code == 201 and again.json()["id"] == item["id"]
    body["items"][0]["quantity"] = 2
    assert (
        client.post(
            "/api/v1/loans",
            json=body,
            headers={**accounts["student"], "Idempotency-Key": "retry-key"},
        ).status_code
        == 409
    )
    assert command(client, accounts, item, "reject").status_code == 422
    assert (
        command(client, accounts, item, "reject", body={"reason": "Thiết bị cần bảo trì"}).json()[
            "status"
        ]
        == "REJECTED"
    )
    another = client.post("/api/v1/loans", json=body, headers=accounts["staff"]).json()
    assert (
        client.get(f"/api/v1/loans/{another['id']}", headers=accounts["student"]).status_code == 404
    )
    assert client.get("/api/v1/loans", headers=accounts["student"]).json()["total"] == 1
    body["due_at"] = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    assert client.post("/api/v1/loans", json=body, headers=accounts["student"]).status_code == 422
    body["due_at"] = "2028-01-01T00:00:00"
    assert client.post("/api/v1/loans", json=body, headers=accounts["student"]).status_code == 422


def test_postgres_concurrent_approvals(client, accounts, db):
    equipment = create(client, accounts, quantity_total=1)
    loans = [loan(client, accounts, [(equipment, 1)])[0] for _ in range(2)]

    def approve(item):
        with TestClient(app) as concurrent_client:
            return command(concurrent_client, accounts, item, "approve").status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(approve, loans))
    assert sorted(statuses) == [200, 409]
    assert db.get(Equipment, equipment["id"]).quantity_reserved == 1
    assert db.scalar(select(func.count()).select_from(Loan).where(Loan.status == "APPROVED")) == 1
    assert db.scalar(select(func.count()).select_from(OutboxEvent)) == 1


def test_postgres_double_return(client, accounts, db):
    equipment = create(client, accounts, quantity_total=2)
    item, _ = loan(client, accounts, [(equipment, 2)])
    command(client, accounts, item, "approve")
    command(client, accounts, item, "handover")

    def return_once(_):
        with TestClient(app) as concurrent_client:
            return command(concurrent_client, accounts, item, "return").status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(return_once, range(2))) == [200, 409]
    assert db.get(Equipment, equipment["id"]).quantity_reserved == 0


def test_summary_audit_scope(client, accounts):
    equipment = create(client, accounts)
    loan(client, accounts, [(equipment, 1)])
    assert (
        client.get("/api/v1/dashboard/summary", headers=accounts["student"]).json()["pending_loans"]
        == 1
    )
    assert client.get("/api/v1/audit/events", headers=accounts["student"]).json()["total"] == 1
    assert client.get("/api/v1/audit/events", headers=accounts["staff"]).json()["total"] == 2
