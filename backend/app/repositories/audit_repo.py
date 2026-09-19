import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from app.repositories.base_repo import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    def __init__(self, db: Session):
        super().__init__(AuditLog, db)

    def log_event(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        application_id: Optional[uuid.UUID] = None,
        actor_id: Optional[uuid.UUID] = None,
        previous_status: Optional[str] = None,
        new_status: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        audit_entry = AuditLog(
            application_id=application_id,
            entity_type=entity_type,
            entity_id=str(entity_id),
            actor_id=actor_id,
            action=action,
            previous_status=previous_status,
            new_status=new_status,
            details=details or {},
        )
        return self.create(audit_entry)

    def get_by_entity(
        self, entity_type: str, entity_id: str, skip: int = 0, limit: int = 100
    ) -> List[AuditLog]:
        query = (
            select(AuditLog)
            .where(
                AuditLog.entity_type == entity_type,
                AuditLog.entity_id == str(entity_id),
            )
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(query).scalars().all())

    def get_by_application(
        self, application_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[AuditLog]:
        query = (
            select(AuditLog)
            .where(AuditLog.application_id == application_id)
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(query).scalars().all())
