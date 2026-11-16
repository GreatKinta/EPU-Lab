from typing import Literal
from uuid import UUID

from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, select

from app.core.errors import AppError
from app.core.security import CurrentUser, Db, Staff
from app.infrastructure.files.storage import image_file, read_upload, save_image, validate_image
from app.modules.audit.service import record
from app.modules.inventory import service, transfers
from app.modules.inventory.models import Equipment
from app.modules.inventory.repository import filtered
from app.modules.inventory.schemas import BulkInput, EquipmentCreate, EquipmentOut, EquipmentPatch

router = APIRouter(prefix="/equipment", tags=["equipment"])
Format = Literal["xlsx", "json", "xml"]


@router.get("")
def list_equipment(
    db: Db,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=10, le=15),
    search: str = Query("", max_length=200),
    product_type: str | None = None,
    sort: Literal[
        "name",
        "code",
        "price",
        "created_at",
        "quantity_total",
        "-name",
        "-code",
        "-price",
        "-created_at",
        "-quantity_total",
    ] = "-created_at",
):
    if page_size not in (10, 15):
        raise AppError(422, "INVALID_PAGE_SIZE", "Cỡ trang chỉ nhận 10 hoặc 15")
    query = filtered(search, product_type)
    column = getattr(Equipment, sort.lstrip("-"))
    items = db.scalars(
        query.order_by(column.desc() if sort.startswith("-") else column.asc(), Equipment.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return {
        "items": [EquipmentOut.model_validate(x) for x in items],
        "total": db.scalar(select(func.count()).select_from(query.subquery())),
        "page": page,
        "page_size": page_size,
    }


@router.post("", response_model=EquipmentOut, status_code=201)
def create_equipment(body: EquipmentCreate, db: Db, actor: Staff):
    return service.create(db, body, actor)


@router.post("/bulk-delete")
def bulk_delete(body: BulkInput, db: Db, actor: Staff):
    return {"deleted": service.bulk(db, body.ids, actor, "delete")}


@router.post("/bulk-duplicate", response_model=list[EquipmentOut], status_code=201)
def bulk_duplicate(body: BulkInput, db: Db, actor: Staff):
    return service.bulk(db, body.ids, actor, "duplicate")


@router.get("/export")
def export(
    db: Db,
    actor: Staff,
    format: Format = "xlsx",
    search: str = Query("", max_length=200),
    product_type: str | None = None,
):
    rows = [
        EquipmentOut.model_validate(x).model_dump(mode="json")
        for x in db.scalars(filtered(search, product_type).order_by(Equipment.code))
    ]
    return Response(
        transfers.encode(rows, format),
        media_type=transfers.MIMES[format],
        headers={"Content-Disposition": f'attachment; filename="equipment.{format}"'},
    )


@router.get("/import-template")
def template(actor: Staff, format: Format = "xlsx"):
    rows = [
        {
            "code": "EQ-SAMPLE",
            "name": "Thiết bị mẫu",
            "product_type": "Điện tử",
            "quantity_total": 5,
            "unit": "cái",
            "price": "150000.00",
            "description": "Thay dữ liệu mẫu trước khi nhập",
        }
    ]
    return Response(
        transfers.encode(rows, format),
        media_type=transfers.MIMES[format],
        headers={"Content-Disposition": f'attachment; filename="equipment-template.{format}"'},
    )


@router.post("/import")
async def import_equipment(
    db: Db,
    actor: Staff,
    file: UploadFile = File(...),
    format: Format = "xlsx",
    dry_run: bool = True,
):
    content = await read_upload(file)
    rows = transfers.decode(content, format)
    items, errors = transfers.validate_rows(db, rows)
    preview = [item.model_dump(mode="json") for item in items[:20]]
    if errors:
        if not dry_run:
            raise AppError(422, "IMPORT_VALIDATION", "Không nhập dòng nào vì tệp có lỗi", errors)
        return {
            "valid": False,
            "total": len(rows),
            "errors": errors,
            "preview": preview,
            "imported": 0,
        }
    if not dry_run:
        for item in items:
            service.create(db, item, actor)
    return {
        "valid": True,
        "total": len(rows),
        "errors": [],
        "preview": preview,
        "imported": 0 if dry_run else len(items),
    }


@router.get("/{equipment_id}", response_model=EquipmentOut)
def detail(equipment_id: UUID, db: Db, user: CurrentUser):
    return service.get_equipment(db, equipment_id)


@router.patch("/{equipment_id}", response_model=EquipmentOut)
def modify(equipment_id: UUID, body: EquipmentPatch, db: Db, actor: Staff):
    return service.modify(db, equipment_id, body, actor)


@router.delete("/{equipment_id}")
def delete(equipment_id: UUID, db: Db, actor: Staff):
    return {"deleted": service.bulk(db, [equipment_id], actor, "delete")}


@router.post("/{equipment_id}/duplicate", response_model=EquipmentOut, status_code=201)
def duplicate(equipment_id: UUID, db: Db, actor: Staff):
    return service.bulk(db, [equipment_id], actor, "duplicate")[0]


@router.post("/{equipment_id}/image", response_model=EquipmentOut)
async def upload_image(equipment_id: UUID, db: Db, actor: Staff, file: UploadFile = File(...)):
    item = service.get_equipment(db, equipment_id, lock=True)
    image = validate_image(await read_upload(file), file.content_type)
    item.image_path = save_image(image)
    record(db, actor, "equipment", item.id, "EquipmentImageUpdated")
    db.flush()
    return item


@router.get("/{equipment_id}/image")
def get_image(equipment_id: UUID, db: Db, user: CurrentUser):
    item = db.get(Equipment, equipment_id)
    if not item:
        raise AppError(404, "NOT_FOUND", "Không tìm thấy thiết bị")
    return FileResponse(
        image_file(item.image_path),
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=300"},
    )
