import logging
from typing import Any

from app.core.security import UserContext
from app.db.supabase import supabase

logger = logging.getLogger("luso.audit")


def record_audit(
    context: UserContext,
    action: str,
    entity_type: str,
    entity_id: object | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    payload = {
        "hotel_id": str(context.hotel_id),
        "user_id": context.user_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": str(entity_id) if entity_id is not None else None,
        "metadata": metadata or {},
    }
    try:
        supabase.table("audit_logs").insert(payload).execute()
    except Exception:
        logger.exception("audit_write_failed", extra={"action": action})
