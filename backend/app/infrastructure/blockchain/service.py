from datetime import UTC

from app.infrastructure.blockchain.hashing import loan_ref, operation_id, snapshot_hash
from app.infrastructure.blockchain.models import BlockchainTransaction, OutboxEvent
from app.modules.inventory.models import Equipment


def timestamp(value):
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def enqueue(db, loan, event_type, occurred_at):
    payload = {
        "schema_version": 1,
        "event_type": event_type,
        "loan_ref": loan_ref(loan.id),
        "loan_code": loan.code,
        "student_ref": str(loan.student_id),
        "items": sorted(
            [
                {
                    "equipment_code": db.get(Equipment, line.equipment_id).code,
                    "quantity": line.quantity,
                }
                for line in loan.items
            ],
            key=lambda x: x["equipment_code"],
        ),
        "occurred_at": timestamp(occurred_at),
        "due_at": timestamp(loan.due_at),
    }
    event = OutboxEvent(aggregate_id=loan.id, event_type=event_type, payload=payload)
    db.add(event)
    db.flush()
    db.add(
        BlockchainTransaction(
            outbox_event_id=event.id,
            loan_id=loan.id,
            operation_id=operation_id(event.id),
            event_type=event_type,
            data_hash=snapshot_hash(payload),
        )
    )
    db.flush()
