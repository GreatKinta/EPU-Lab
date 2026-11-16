import json
import xml.etree.ElementTree as ET
from io import BytesIO
from zipfile import BadZipFile, ZipFile

from defusedxml import ElementTree as SafeET
from defusedxml.common import DefusedXmlException
from openpyxl import Workbook, load_workbook
from pydantic import ValidationError
from sqlalchemy import select

from app.core.config import get_settings
from app.core.errors import AppError
from app.modules.inventory.models import Equipment
from app.modules.inventory.schemas import EquipmentCreate

FIELDS = list(EquipmentCreate.model_fields)
MIMES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "json": "application/json",
    "xml": "application/xml",
}


def decode(content, format):
    limit = get_settings().max_import_rows
    try:
        if format == "json":
            rows = json.loads(content)
            if not isinstance(rows, list):
                raise ValueError("JSON phải là một mảng")
        elif format == "xml":
            root = SafeET.fromstring(content, forbid_dtd=True)
            if root.tag != "equipment":
                raise ValueError("XML phải có root equipment")
            rows = []
            for item in root:
                if item.tag != "item" or len({e.tag for e in item}) != len(item):
                    raise ValueError("Cấu trúc XML không hợp lệ")
                rows.append({field.tag: field.text or "" for field in item})
        elif format == "xlsx":
            with ZipFile(BytesIO(content)) as archive:
                if sum(x.file_size for x in archive.infolist()) > 25 * 1024 * 1024:
                    raise AppError(413, "EXPANDED_FILE_TOO_LARGE", "XLSX giải nén vượt giới hạn")
            workbook = load_workbook(BytesIO(content), read_only=True, data_only=False)
            try:
                sheet = workbook.active
                iterator = sheet.iter_rows(
                    values_only=True, max_row=limit + 2, max_col=len(FIELDS) + 1
                )
                headers = [v for v in next(iterator) if v is not None]
                if (
                    not headers
                    or len(set(headers)) != len(headers)
                    or any(h not in FIELDS for h in headers)
                ):
                    raise ValueError("Tiêu đề cột không hợp lệ, hãy dùng tệp mẫu")
                rows = []
                for row in iterator:
                    if any(v is not None for v in row):
                        if any(v is not None for v in row[len(headers) :]):
                            raise ValueError("Có dữ liệu ngoài các cột đã khai báo")
                        rows.append(dict(zip(headers, row[: len(headers)], strict=True)))
            finally:
                workbook.close()
        else:
            raise ValueError("Định dạng không hỗ trợ")
        if not rows:
            raise ValueError("Tệp không có dữ liệu")
        if len(rows) > limit:
            raise AppError(413, "TOO_MANY_ROWS", f"Tối đa {limit} dòng")
        return rows
    except AppError:
        raise
    except (
        ValueError,
        TypeError,
        KeyError,
        StopIteration,
        ET.ParseError,
        DefusedXmlException,
        BadZipFile,
        OSError,
        OverflowError,
    ):
        raise AppError(
            422, "INVALID_IMPORT", "Tệp không hợp lệ, sai cấu trúc hoặc XML không an toàn"
        ) from None


def validate_rows(db, rows):
    valid, errors, seen = [], [], set()
    for index, row in enumerate(rows, 1):
        try:
            item = EquipmentCreate.model_validate(row)
            if item.code in seen:
                errors.append({"row": index, "message": "Mã bị trùng trong tệp"})
            else:
                valid.append((index, item))
                seen.add(item.code)
        except ValidationError as exc:
            errors.append(
                {
                    "row": index,
                    "message": "; ".join(
                        f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()
                    ),
                }
            )
    existing = set(db.scalars(select(Equipment.code).where(Equipment.code.in_(seen))))
    errors.extend(
        {"row": index, "message": f"Mã {item.code} đã tồn tại"}
        for index, item in valid
        if item.code in existing
    )
    return [item for _, item in valid], sorted(errors, key=lambda e: e["row"])


def encode(rows, format):
    values = [{key: row.get(key) for key in FIELDS} for row in rows]
    if format == "json":
        return json.dumps(values, ensure_ascii=False, indent=2).encode()
    if format == "xml":
        root = ET.Element("equipment")
        for row in values:
            child = ET.SubElement(root, "item")
            for key, value in row.items():
                ET.SubElement(child, key).text = "" if value is None else str(value)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Equipment"
    sheet.append(FIELDS)
    for row in values:
        sheet.append(list(row.values()))
        # Explicit string cells prevent Excel interpreting untrusted values as formulas.
        for cell in sheet[sheet.max_row]:
            if isinstance(cell.value, str):
                cell.data_type = "s"
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()
