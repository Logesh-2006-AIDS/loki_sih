import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from app.schemas.audit import AuditLogResponse
from app.repositories.audit_repo import AuditRepository


class AuditService:
    """
    Centralized audit logging service providing traceable audit trails
    across applications, documents, users, schemes, and fellowships.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = AuditRepository(db)

    def log(
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
        return self.repo.log_event(
            entity_type=entity_type,
            entity_id=str(entity_id),
            action=action,
            application_id=application_id,
            actor_id=actor_id,
            previous_status=previous_status,
            new_status=new_status,
            details=details,
        )

    def get_logs_for_entity(
        self, entity_type: str, entity_id: str, skip: int = 0, limit: int = 100
    ) -> List[AuditLogResponse]:
        logs = self.repo.get_by_entity(entity_type, entity_id, skip=skip, limit=limit)
        return [AuditLogResponse.model_validate(log) for log in logs]

    def get_logs_for_application(
        self, application_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[AuditLogResponse]:
        logs = self.repo.get_by_application(application_id, skip=skip, limit=limit)
        return [AuditLogResponse.model_validate(log) for log in logs]
