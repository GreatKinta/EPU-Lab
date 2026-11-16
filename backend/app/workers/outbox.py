"""Durable signed-before-send outbox; polling with bounded exponential retries."""

import logging
import time
from datetime import timedelta

from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from app import models  # noqa: F401 -- register FK targets in standalone worker process
from app.core.config import get_settings
from app.core.db import engine, utcnow
from app.infrastructure.blockchain.adapter import ChainAdapter
from app.infrastructure.blockchain.hashing import loan_ref, operation_id, snapshot_hash
from app.infrastructure.blockchain.models import BlockchainTransaction, OutboxEvent

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 8
# Session advisory lock serializes the relayer nonce even across durable commits.
SIGNER_LOCK = 31337001


def matches(record, event, tx):
    return (
        record["loan_ref"] == loan_ref(event.aggregate_id)
        and record["data_hash"] == snapshot_hash(event.payload) == tx.data_hash
        and record["kind"] == (1 if event.event_type == "BorrowApproved" else 2)
        and tx.operation_id == operation_id(event.id)
    )


def run_once(adapter_factory=ChainAdapter):
    with engine.connect() as connection:
        acquired = connection.scalar(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": SIGNER_LOCK}
        )
        connection.commit()
        if not acquired:
            return False
        try:
            with Session(bind=connection, expire_on_commit=False) as db:
                event = db.scalar(
                    select(OutboxEvent)
                    .where(
                        OutboxEvent.next_retry_at <= utcnow(),
                        or_(
                            OutboxEvent.status == "PENDING",
                            (OutboxEvent.status == "PROCESSING")
                            & (OutboxEvent.locked_at < utcnow() - timedelta(minutes=2)),
                        ),
                    )
                    .order_by(OutboxEvent.created_at, OutboxEvent.id)
                    .with_for_update(skip_locked=True)
                    .limit(1)
                )
                if not event:
                    db.rollback()
                    return False
                tx = db.scalar(
                    select(BlockchainTransaction).where(
                        BlockchainTransaction.outbox_event_id == event.id
                    )
                )
                event.status = "PROCESSING"
                event.locked_at = utcnow()
                event.attempt_count += 1
                db.commit()
                try:
                    if event.event_type == "EquipmentReturned":
                        borrow = db.scalar(
                            select(BlockchainTransaction).where(
                                BlockchainTransaction.loan_id == tx.loan_id,
                                BlockchainTransaction.event_type == "BorrowApproved",
                            )
                        )
                        if not borrow or borrow.status != "CONFIRMED":
                            event.status = "PENDING"
                            event.attempt_count -= 1
                            event.next_retry_at = utcnow() + timedelta(seconds=5)
                            db.commit()
                            return True
                    adapter = adapter_factory()
                    record = adapter.read(tx.operation_id)
                    if record["kind"]:
                        if not matches(record, event, tx):
                            raise ValueError(
                                "Existing on-chain record differs from immutable snapshot"
                            )
                        confirm(event, tx, adapter)
                    else:
                        if (
                            tx.data_hash != snapshot_hash(event.payload)
                            or tx.operation_id != operation_id(event.id)
                            or event.payload["loan_ref"] != loan_ref(event.aggregate_id)
                        ):
                            raise ValueError(
                                "Snapshot or operation identity mismatch; refusing submission"
                            )
                        if not tx.raw_transaction:
                            unresolved = db.scalars(
                                select(BlockchainTransaction).where(
                                    BlockchainTransaction.id != tx.id,
                                    BlockchainTransaction.raw_transaction.is_not(None),
                                    BlockchainTransaction.status != "CONFIRMED",
                                )
                            )
                            # A signed but unaccepted tx may reserve the same nonce that
                            # RPC reports as pending. Do not sign another event over it.
                            if any(
                                adapter.receipt(previous.tx_hash) is None for previous in unresolved
                            ):
                                event.status = "PENDING"
                                event.attempt_count -= 1
                                event.next_retry_at = utcnow() + timedelta(seconds=5)
                                db.commit()
                                return True
                            tx.nonce, tx.raw_transaction, tx.tx_hash = adapter.sign(event, tx)
                            tx.status = "SUBMITTED"
                            db.commit()  # Persist exact signed bytes/hash BEFORE the network side effect.
                        receipt = adapter.receipt(tx.tx_hash)
                        if receipt is None:
                            try:
                                adapter.broadcast(tx.raw_transaction)
                            except Exception:
                                # RPC may accept bytes and lose response. Keep original nonce/bytes.
                                receipt = adapter.receipt(tx.tx_hash)
                                if receipt is None:
                                    raise
                            receipt = receipt or adapter.receipt(tx.tx_hash)
                        if receipt is None:
                            event.status = "PENDING"
                            event.next_retry_at = utcnow() + timedelta(seconds=5)
                        elif receipt["status"] != 1:
                            event.status = "FAILED"
                            tx.status = "FAILED"
                            event.last_error = tx.error_message = (
                                "Transaction reverted; inspect and retry manually"
                            )
                        elif not matches(adapter.read(tx.operation_id), event, tx):
                            raise ValueError("Receipt exists but contract evidence does not match")
                        else:
                            tx.block_number = receipt["blockNumber"]
                            confirm(event, tx, adapter)
                    db.commit()
                except Exception as exc:
                    db.rollback()
                    event = db.get(OutboxEvent, event.id)
                    tx = db.get(BlockchainTransaction, tx.id)
                    # Never persist exception strings that might contain URLs, keys or payloads.
                    error = type(exc).__name__
                    event.last_error = tx.error_message = error
                    event.status = "FAILED" if event.attempt_count >= MAX_ATTEMPTS else "PENDING"
                    if event.status == "FAILED":
                        tx.status = "FAILED"
                    event.next_retry_at = utcnow() + timedelta(
                        seconds=min(300, 2**event.attempt_count)
                    )
                    db.commit()
                    logger.warning(
                        "outbox event=%s operation=%s error=%s", event.id, tx.operation_id, error
                    )
                return True
        finally:
            connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": SIGNER_LOCK})
            connection.commit()


def confirm(event, tx, adapter):
    receipt = adapter.receipt(tx.tx_hash) if tx.tx_hash else None
    confirmations = get_settings().chain_confirmations
    if not receipt or (
        confirmations > 1
        and adapter.web3.eth.block_number - receipt["blockNumber"] + 1 < confirmations
    ):
        event.status = "PENDING"
        event.next_retry_at = utcnow() + timedelta(seconds=5)
        return
    tx.block_number = receipt["blockNumber"]
    event.status = "CONFIRMED"
    event.processed_at = utcnow()
    event.last_error = None
    tx.status = "CONFIRMED"
    tx.error_message = None


def main():
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            run_once()
        except Exception as exc:
            logger.error("Worker polling failure: %s", type(exc).__name__)
        time.sleep(2)


if __name__ == "__main__":
    main()
