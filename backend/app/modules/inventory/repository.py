from sqlalchemy import or_, select

from app.modules.inventory.models import Equipment


def filtered(search="", product_type=None):
    query = select(Equipment).where(Equipment.deleted_at.is_(None))
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(
            or_(
                *(
                    col.ilike(f"%{escaped}%", escape="\\")
                    for col in [Equipment.name, Equipment.code, Equipment.description]
                )
            )
        )
    if product_type:
        query = query.where(Equipment.product_type == product_type)
    return query
