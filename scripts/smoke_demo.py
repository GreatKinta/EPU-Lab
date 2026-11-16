"""Real HTTP/worker/local-chain smoke. Adds one completed demo loan, keeps history."""

import json
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
from dotenv import dotenv_values

root = Path(__file__).resolve().parents[1]
password = dotenv_values(root / ".env").get("DEMO_PASSWORD")
base = os.getenv("LABCHAIN_BASE_URL", "http://127.0.0.1:5173/api/v1")


def checked(response):
    response.raise_for_status()
    return response.json()


with httpx.Client(base_url=base, timeout=20) as client:
    assert checked(client.get("/health"))["status"] == "ok"
    tokens = {}
    for role in ["staff", "student"]:
        result = checked(
            client.post(
                "/auth/login",
                json={"email": f"{role}@labchain.local", "password": password},
            )
        )
        tokens[role] = {"Authorization": f"Bearer {result['access_token']}"}
    result = checked(client.get("/equipment?page_size=15", headers=tokens["student"]))
    assert result["total"] >= 30 and len(result["items"]) == 15
    item = next(x for x in result["items"] if x["quantity_available"] > 0)
    original = item["quantity_available"]
    loan = checked(
        client.post(
            "/loans",
            headers={**tokens["student"], "Idempotency-Key": str(uuid4())},
            json={
                "due_at": (datetime.now(UTC) + timedelta(days=3)).isoformat(),
                "items": [{"equipment_id": item["id"], "quantity": 1}],
            },
        )
    )
    path = f"/loans/{loan['id']}"
    checked(client.post(path + "/approve", headers=tokens["staff"]))
    reserved = checked(client.get(f"/equipment/{item['id']}", headers=tokens["staff"]))
    assert reserved["quantity_available"] == original - 1
    checked(client.post(path + "/handover", headers=tokens["staff"]))
    checked(client.post(path + "/return", headers=tokens["staff"]))
    assert client.post(path + "/return", headers=tokens["staff"]).status_code == 409
    verified = None
    for _ in range(30):
        verified = checked(client.get(path + "/verify", headers=tokens["student"]))
        if verified["status"] == "VERIFIED" and len(verified["records"]) == 2:
            break
        time.sleep(2)
    assert (
        verified and verified["status"] == "VERIFIED" and len(verified["records"]) == 2
    ), verified
    assert all(
        x["tx_hash"] and x["chain_hash"] == x["computed_hash"]
        for x in verified["records"]
    )
    restored = checked(client.get(f"/equipment/{item['id']}", headers=tokens["staff"]))
    assert restored["quantity_available"] == original
    report = {
        "result": "PASS",
        "loan_id": loan["id"],
        "events": 2,
        "verified": True,
        "stock_restored": True,
        "frontend_proxy": True,
        "network": verified["network"],
    }
    (root / "docs" / "smoke-result.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report, indent=2))
