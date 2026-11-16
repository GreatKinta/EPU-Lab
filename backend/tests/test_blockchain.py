import os
from datetime import timedelta

import pytest
from sqlalchemy import select
from test_borrowing import command, loan
from test_inventory import create

from app.core.db import SessionLocal, utcnow
from app.infrastructure.blockchain.adapter import ChainAdapter
from app.infrastructure.blockchain.hashing import canonical, loan_ref, operation_id, snapshot_hash
from app.infrastructure.blockchain.models import BlockchainTransaction, OutboxEvent
from app.workers.outbox import run_once


def test_canonical_hash_is_stable():
    a = {"schema_version": 1, "a": "Tiếng Việt", "items": [{"quantity": 2}]}
    b = {"items": [{"quantity": 2}], "a": "Tiếng Việt", "schema_version": 1}
    assert canonical(a) == canonical(b) and snapshot_hash(a) == snapshot_hash(b)
    assert loan_ref("id") != operation_id("id")


class MemoryAdapter:
    def __init__(self):
        self.records = {}
        self.receipts = {}
        self.signed = 0
        self.sent = 0
        self.lose_response = False

    def read(self, operation):
        return self.records.get(operation, {"kind": 0})

    def sign(self, event, tx):
        self.signed += 1
        self.current = (event, tx)
        return 1, "0x1234", "0x" + "ab" * 32

    def receipt(self, hash):
        return self.receipts.get(hash)

    def broadcast(self, raw):
        self.sent += 1
        event, tx = self.current
        # Inspect durable state from a separate connection before the side effect.
        with SessionLocal() as check:
            persisted = check.get(BlockchainTransaction, tx.id)
            assert persisted.raw_transaction == raw and persisted.tx_hash == tx.tx_hash
        self.records[tx.operation_id] = {
            "kind": 1 if event.event_type == "BorrowApproved" else 2,
            "loan_ref": event.payload["loan_ref"],
            "data_hash": tx.data_hash,
        }
        self.receipts[tx.tx_hash] = {"status": 1, "blockNumber": 2}
        if self.lose_response:
            raise ConnectionError("RPC response lost")


def test_worker_signed_before_send_reconcile_idempotency(client, accounts, db, monkeypatch):
    equipment = create(client, accounts)
    item, _ = loan(client, accounts, [(equipment, 1)])
    command(client, accounts, item, "approve")
    adapter = MemoryAdapter()
    adapter.lose_response = True
    assert run_once(lambda: adapter)
    assert not run_once(lambda: adapter)
    assert adapter.signed == adapter.sent == 1
    db.expire_all()
    assert db.scalar(select(OutboxEvent)).status == "CONFIRMED"
    monkeypatch.setattr("app.infrastructure.blockchain.router.ChainAdapter", lambda: adapter)
    result = client.get(f"/api/v1/loans/{item['id']}/verify", headers=accounts["student"])
    assert result.json()["status"] == "VERIFIED"
    event = db.scalar(select(OutboxEvent))
    event.payload = {**event.payload, "loan_code": "tampered"}
    db.commit()
    assert (
        client.get(f"/api/v1/loans/{item['id']}/verify", headers=accounts["student"]).json()[
            "status"
        ]
        == "MISMATCH"
    )


def test_worker_rpc_outage_lease_recovery_and_manual_retry(client, accounts, db):
    equipment = create(client, accounts)
    item, _ = loan(client, accounts, [(equipment, 1)])
    command(client, accounts, item, "approve")

    def unavailable():
        raise ConnectionError("down")

    assert run_once(unavailable)
    event = db.scalar(select(OutboxEvent))
    assert event.status == "PENDING" and event.attempt_count == 1
    for _ in range(7):
        event.next_retry_at = utcnow() - timedelta(seconds=1)
        db.commit()
        run_once(unavailable)
        db.expire_all()
    assert event.status == "FAILED"
    path = f"/api/v1/blockchain/events/{event.id}/retry"
    assert client.post(path, headers=accounts["student"]).status_code == 403
    assert client.post(path, headers=accounts["staff"]).status_code == 200
    db.expire_all()
    assert event.attempt_count == 0
    event.status = "PROCESSING"
    event.locked_at = utcnow() - timedelta(minutes=3)
    db.commit()
    assert run_once(lambda: MemoryAdapter())
    db.expire_all()
    assert event.status == "CONFIRMED"


@pytest.mark.skipif(
    os.getenv("RUN_CHAIN_TESTS") != "1", reason="Real chain opt-in: RUN_CHAIN_TESTS=1"
)
def test_real_chain_end_to_end(client, accounts, db):
    # Marked integration: requires the local node and a deployed runtime config.
    ChainAdapter()
    equipment = create(client, accounts)
    item, _ = loan(client, accounts, [(equipment, 1)])
    assert command(client, accounts, item, "approve").status_code == 200
    assert run_once()
    result = client.get(f"/api/v1/loans/{item['id']}/verify", headers=accounts["student"]).json()
    assert result["status"] == "VERIFIED", result
    assert (
        result["records"][0]["tx_hash"]
        and result["records"][0]["chain_hash"] == result["records"][0]["computed_hash"]
    )
    assert command(client, accounts, item, "handover").status_code == 200
    assert command(client, accounts, item, "return").status_code == 200
    assert run_once()
    verified = client.get(f"/api/v1/loans/{item['id']}/verify", headers=accounts["student"]).json()
    assert verified["status"] == "VERIFIED" and len(verified["records"]) == 2
    assert all(x["status"] == "VERIFIED" for x in verified["records"])


def test_unknown_submission_blocks_new_nonce_and_reuses_signed_bytes(client, accounts, db):
    equipment = create(client, accounts, quantity_total=5)
    first, _ = loan(client, accounts, [(equipment, 1)])
    command(client, accounts, first, "approve")
    second, _ = loan(client, accounts, [(equipment, 1)])
    command(client, accounts, second, "approve")
    adapter = MemoryAdapter()
    broadcast = adapter.broadcast

    def outage(raw):
        raise ConnectionError("Before RPC accepts")

    adapter.broadcast = outage
    assert run_once(lambda: adapter)
    assert adapter.signed == 1
    assert run_once(lambda: adapter)
    assert adapter.signed == 1  # second event cannot reuse first event's uncertain nonce
    events = list(db.scalars(select(OutboxEvent).order_by(OutboxEvent.created_at)))
    assert events[0].status == events[1].status == "PENDING"
    adapter.broadcast = broadcast
    events[0].next_retry_at = utcnow() - timedelta(seconds=1)
    db.commit()
    assert run_once(lambda: adapter)
    assert adapter.signed == 1  # exact durable bytes are reused
    db.expire_all()
    assert events[0].status == "CONFIRMED"


def test_worker_standalone_process_registers_all_foreign_key_targets(client, accounts, db):
    import subprocess
    import sys

    equipment = create(client, accounts)
    item, _ = loan(client, accounts, [(equipment, 1)])
    command(client, accounts, item, "approve")
    source = "from app.workers.outbox import run_once\ndef offline():\n raise ConnectionError('offline')\nassert run_once(offline)\n"
    process = subprocess.run(
        [sys.executable, "-c", source], capture_output=True, text=True, timeout=20, check=False
    )
    assert process.returncode == 0, process.stderr
    event = db.scalar(select(OutboxEvent))
    assert event.attempt_count == 1 and event.status == "PENDING"
