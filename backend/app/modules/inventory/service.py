from uuid import uuid4

from sqlalchemy import select, update

from app.core.db import utcnow
from app.core.errors import AppError
from app.modules.audit.service import record
from app.modules.inventory.models import Equipment
from app.modules.inventory.schemas import EquipmentCreate, EquipmentOut


def get_equipment(db, equipment_id, lock=False):
    query = select(Equipment).where(Equipment.id == equipment_id, Equipment.deleted_at.is_(None))
    item = db.scalar(query.with_for_update() if lock else query)
    if not item:
        raise AppError(404, "NOT_FOUND", "Không tìm thấy thiết bị")
    return item


def create(db, body: EquipmentCreate, actor):
    item = Equipment(**body.model_dump())
    db.add(item)
    db.flush()
    record(
        db,
        actor,
        "equipment",
        item.id,
        "EquipmentCreated",
        after=EquipmentOut.model_validate(item).model_dump(mode="json"),
    )
    return item


def modify(db, item_id, body, actor):
    item = get_equipment(db, item_id, lock=True)
    values = body.model_dump(exclude_unset=True)
    if any(value is None and key != "description" for key, value in values.items()):
        raise AppError(422, "VALIDATION_ERROR", "Các trường bắt buộc không được để trống")
    if values.get("quantity_total", item.quantity_total) < item.quantity_reserved:
        raise AppError(
            409, "STOCK_RESERVED", "Tổng số lượng không được thấp hơn số đang mượn/giữ chỗ"
        )
    before = EquipmentOut.model_validate(item).model_dump(mode="json")
    for key, value in values.items():
        setattr(item, key, value)
    db.flush()
    record(
        db,
        actor,
        "equipment",
        item.id,
        "EquipmentUpdated",
        before,
        EquipmentOut.model_validate(item).model_dump(mode="json"),
    )
    return item


def bulk(db, ids, actor, action):
    if len(ids) != len(set(ids)):
        raise AppError(422, "DUPLICATE_ID", "Danh sách có ID trùng")
    result = []
    # Global lock order prevents deadlocks between bulk and loan commands.
    items = [get_equipment(db, item_id, lock=True) for item_id in sorted(ids)]
    for item in items:
        if action == "delete":
            if item.quantity_reserved:
                raise AppError(
                    409, "STOCK_RESERVED", f"Thiết bị {item.code} đang được mượn/giữ chỗ"
                )
            item.deleted_at = utcnow()
            record(db, actor, "equipment", item.id, "EquipmentArchived")
            result.append(str(item.id))
        else:
            values = EquipmentCreate.model_validate(
                EquipmentOut.model_validate(item).model_dump(
                    include=set(EquipmentCreate.model_fields)
                )
            )
            values.code = f"COPY-{uuid4().hex[:20]}"
            copied = create(db, values, actor)
            copied.image_path = item.image_path
            result.append(copied)
    db.flush()
    return result


def reserve(db, quantities):
    for equipment_id, quantity in sorted(quantities.items()):
        result = db.execute(
            update(Equipment)
            .where(
                Equipment.id == equipment_id,
                Equipment.deleted_at.is_(None),
                Equipment.quantity_total - Equipment.quantity_reserved >= quantity,
            )
            .values(quantity_reserved=Equipment.quantity_reserved + quantity)
        )
        if result.rowcount != 1:
            raise AppError(
                409, "INSUFFICIENT_STOCK", "Không đủ thiết bị khả dụng; phiếu chưa được duyệt"
            )


def release(db, quantities):
    for equipment_id, quantity in sorted(quantities.items()):
        result = db.execute(
            update(Equipment)
            .where(Equipment.id == equipment_id, Equipment.quantity_reserved >= quantity)
            .values(quantity_reserved=Equipment.quantity_reserved - quantity)
        )
        if result.rowcount != 1:
            raise AppError(409, "STOCK_INCONSISTENT", "Số lượng giữ chỗ không nhất quán")
