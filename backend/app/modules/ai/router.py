from fastapi import APIRouter, File, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.security import Staff
from app.infrastructure.files.storage import read_upload, validate_image
from app.modules.ai.service import extract

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/ocr/equipment")
async def ocr_equipment(actor: Staff, file: UploadFile = File(...)):
    image = validate_image(await read_upload(file), file.content_type)
    return await run_in_threadpool(extract, image)
