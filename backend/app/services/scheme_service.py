import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.exceptions import EntityNotFoundException, DuplicateEntityException
from app.models.scheme import Scheme
from app.schemas.scheme import SchemeCreate, SchemeUpdate, SchemeResponse
from app.repositories.scheme_repo import SchemeRepository
from app.repositories.audit_repo import AuditRepository


class SchemeService:
    """
    Scheme management service providing discovery and configuration of
    tribal scholarships/fellowships (e.g. NFST, NOS).

    Note: In Phase 0, `scheme_version` establishes the architectural foundation
    for future version tracking and rule migration without full historical branching.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = SchemeRepository(db)
        self.audit_repo = AuditRepository(db)

    def list_active_schemes(self) -> List[SchemeResponse]:
        schemes = self.repo.get_active_schemes()
        return [SchemeResponse.model_validate(s) for s in schemes]

    def list_all_schemes(self, skip: int = 0, limit: int = 100) -> List[SchemeResponse]:
        schemes = self.repo.get_all(skip=skip, limit=limit)
        return [SchemeResponse.model_validate(s) for s in schemes]

    def get_scheme(self, scheme_id: uuid.UUID) -> SchemeResponse:
        scheme = self.repo.get_by_id(scheme_id)
        if not scheme:
            raise EntityNotFoundException(f"Scheme with ID {scheme_id} not found")
        return SchemeResponse.model_validate(scheme)

    def get_scheme_by_code(self, code: str) -> SchemeResponse:
        scheme = self.repo.get_by_code(code)
        if not scheme:
            raise EntityNotFoundException(f"Scheme with code '{code}' not found")
        return SchemeResponse.model_validate(scheme)

    def create_scheme(self, data: SchemeCreate, actor_id: Optional[uuid.UUID] = None) -> SchemeResponse:
        existing = self.repo.get_by_code(data.scheme_code)
        if existing:
            raise DuplicateEntityException(f"Scheme with code '{data.scheme_code}' already exists")

        scheme = Scheme(
            scheme_code=data.scheme_code.upper().strip(),
            name=data.name,
            description=data.description,
            scheme_version=data.scheme_version or "1.0",
            is_demo=data.is_demo,
            eligibility_rules=data.eligibility_rules,
            form_schema=data.form_schema,
            required_documents=data.required_documents,
            scoring_weights=data.scoring_weights,
            deadline=data.deadline,
            is_active=data.is_active,
        )
        created = self.repo.create(scheme)

        self.audit_repo.log_event(
            entity_type="SCHEME",
            entity_id=str(created.id),
            actor_id=actor_id,
            action="SCHEME_CREATED",
            details={
                "scheme_code": created.scheme_code,
                "name": created.name,
                "scheme_version": created.scheme_version,
                "is_demo": created.is_demo,
            },
        )
        return SchemeResponse.model_validate(created)

    def update_scheme(
        self, scheme_id: uuid.UUID, data: SchemeUpdate, actor_id: Optional[uuid.UUID] = None
    ) -> SchemeResponse:
        scheme = self.repo.get_by_id(scheme_id)
        if not scheme:
            raise EntityNotFoundException(f"Scheme with ID {scheme_id} not found")

        update_dict = data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(scheme, field, value)

        updated = self.repo.update(scheme)

        self.audit_repo.log_event(
            entity_type="SCHEME",
            entity_id=str(updated.id),
            actor_id=actor_id,
            action="SCHEME_UPDATED",
            details={"updated_fields": list(update_dict.keys())},
        )
        return SchemeResponse.model_validate(updated)
