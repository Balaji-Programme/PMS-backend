from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

def capture_audit_details(
    old_obj: Any,
    new_data_dict: Dict[str, Any],
) -> List[Dict[str, Optional[str]]]:
    changes: List[Dict[str, Optional[str]]] = []
    for field, new_value in new_data_dict.items():
        old_value = getattr(old_obj, field, None)
        old_str = str(old_value) if old_value is not None else None
        new_str = str(new_value) if new_value is not None else None
        if old_str != new_str:
            changes.append(
                {"field_name": field, "old_value": old_str, "new_value": new_str}
            )
    return changes

async def write_audit(
    db: AsyncSession,
    actor_id: Optional[str],
    action_type: str,
    resource_name: str,
    resource_id: int,
    record_id: int,
    details: Optional[List[Dict[str, Optional[str]]]] = None,
) -> None:
    from app.models.audit import AuditLogs, AuditLogDetails

    action_map = {"CREATE": 1, "UPDATE": 2, "DELETE": 3, "ASSIGN": 4, "REMOVE": 5}
    action_verb = str(action_type).upper().split("_")[0]
    action_int = action_map.get(action_verb, 5)

    try:
        performed_by = (
            uuid.UUID(actor_id)
            if actor_id and actor_id != "system"
            else uuid.UUID(int=0)
        )
    except (ValueError, AttributeError):
        performed_by = uuid.UUID(int=0)

    try:
        async with db.begin_nested():
            audit_log = AuditLogs(
                TableName     = resource_name[:250],
                Action        = action_int,
                PerformedBy   = performed_by,
                PerformedOn   = datetime.now(timezone.utc).replace(tzinfo=None),
                TransactionId = uuid.uuid4(),
                Comments      = f"Action: {action_type} on Record ID: {record_id}",
                ModuleName    = "System",
            )
            db.add(audit_log)
            await db.flush()

            if details:
                db.add_all([
                    AuditLogDetails(
                        AuditLogId = audit_log.ID,
                        FieldName  = str(d.get("field_name", ""))[:250],
                        OldValue   = str(d["old_value"]) if d.get("old_value") is not None else None,
                        NewValue   = str(d["new_value"]) if d.get("new_value") is not None else None,
                        ValueType  = 1,
                    )
                    for d in details
                ])
    except Exception:
        
        import logging
        logging.getLogger("app.audit").warning(
            "Audit write failed for action=%s resource=%s record=%s",
            action_type, resource_name, record_id,
            exc_info=True,
        )
