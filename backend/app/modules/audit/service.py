from app.modules.audit.models import AuditLog


def record(db, actor, entity_type, entity_id, action, before=None, after=None):
    db.add(
        AuditLog(
            actor_user_id=actor.id if actor else None,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            before_json=before,
            after_json=after,
        )
    )
