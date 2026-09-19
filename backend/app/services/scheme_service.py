import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.core.exceptions import (
    EntityNotFoundException,
    DuplicateEntityException,
    InvalidOperationException,
)
from app.models.scheme import Scheme
from app.models.scheme_version import SchemeVersion
from app.schemas.scheme import (
    SchemeCreate,
    SchemeUpdate,
    SchemeResponse,
    SchemeDetailResponse,
    SchemeVersionCreate,
    SchemeVersionUpdate,
    SchemeVersionResponse,
    EligibilityCheckResponse,
)
from app.repositories.scheme_repo import SchemeRepository
from app.repositories.scheme_version_repo import SchemeVersionRepository
from app.repositories.audit_repo import AuditRepository
from app.services.rules_engine import RulesEngine


class SchemeService:
    """
    Scheme management service providing discovery and configuration of
    tribal scholarships/fellowships (e.g. NFST, NOS).

    SchemeVersion is the single authoritative source of truth for all
    eligibility rules, form schemas, required documents, and scoring weights.
    The parent Scheme entity serves as the catalog identity and maintains
    read-only mirror columns for backward compatibility.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = SchemeRepository(db)
        self.version_repo = SchemeVersionRepository(db)
        self.audit_repo = AuditRepository(db)

    # -----------------------------------------------------------------------
    # Scheme Discovery (Public / Applicant)
    # -----------------------------------------------------------------------

    def list_active_schemes(self) -> List[SchemeResponse]:
        schemes = self.repo.get_active_schemes()
        responses = []
        for s in schemes:
            active_v = self.version_repo.get_active_version(s.id)
            res = SchemeResponse.model_validate(s)
            if active_v:
                res.active_version_id = active_v.id
                res.scheme_version = active_v.scheme_version
                res.eligibility_rules = active_v.eligibility_rules
                res.form_schema = active_v.form_schema
                res.required_documents = active_v.required_documents
                res.scoring_weights = active_v.scoring_weights
                res.is_demo = active_v.is_demo
            responses.append(res)
        return responses

    def list_all_schemes(self, skip: int = 0, limit: int = 100) -> List[SchemeResponse]:
        schemes = self.repo.get_all(skip=skip, limit=limit)
        responses = []
        for s in schemes:
            active_v = self.version_repo.get_active_version(s.id)
            res = SchemeResponse.model_validate(s)
            if active_v:
                res.active_version_id = active_v.id
                res.scheme_version = active_v.scheme_version
            responses.append(res)
        return responses

    def get_scheme(self, scheme_id: uuid.UUID) -> SchemeDetailResponse:
        scheme = self.repo.get_by_id(scheme_id)
        if not scheme:
            raise EntityNotFoundException("Scheme", scheme_id)

        active_v = self.version_repo.get_active_version(scheme.id)
        versions = self.version_repo.get_versions_by_scheme_id(scheme.id)

        res_dict = SchemeResponse.model_validate(scheme).model_dump()
        if active_v:
            res_dict["active_version_id"] = active_v.id
            res_dict["scheme_version"] = active_v.scheme_version
            res_dict["eligibility_rules"] = active_v.eligibility_rules
            res_dict["form_schema"] = active_v.form_schema
            res_dict["required_documents"] = active_v.required_documents
            res_dict["scoring_weights"] = active_v.scoring_weights
            res_dict["is_demo"] = active_v.is_demo

        detail = SchemeDetailResponse(**res_dict)
        detail.active_version = (
            SchemeVersionResponse.model_validate(active_v) if active_v else None
        )
        detail.versions_count = len(versions)
        return detail

    def get_scheme_by_code(self, code: str) -> SchemeResponse:
        scheme = self.repo.get_by_code(code)
        if not scheme:
            raise EntityNotFoundException("Scheme", code)

        active_v = self.version_repo.get_active_version(scheme.id)
        res = SchemeResponse.model_validate(scheme)
        if active_v:
            res.active_version_id = active_v.id
            res.scheme_version = active_v.scheme_version
            res.eligibility_rules = active_v.eligibility_rules
            res.form_schema = active_v.form_schema
            res.required_documents = active_v.required_documents
            res.scoring_weights = active_v.scoring_weights
            res.is_demo = active_v.is_demo
        return res

    # -----------------------------------------------------------------------
    # Scheme Creation & Parent Updates (Admin Only)
    # -----------------------------------------------------------------------

    def create_scheme(
        self, data: SchemeCreate, actor_id: Optional[uuid.UUID] = None
    ) -> SchemeResponse:
        existing = self.repo.get_by_code(data.scheme_code)
        if existing:
            raise DuplicateEntityException(
                f"Scheme with code '{data.scheme_code}' already exists"
            )

        # 1. Create parent catalog entry
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
        created_scheme = self.repo.create(scheme)

        # 2. Automatically create initial SchemeVersion 1.0 (authoritative)
        initial_version = SchemeVersion(
            scheme_id=created_scheme.id,
            scheme_code=created_scheme.scheme_code,
            scheme_version=data.scheme_version or "1.0",
            name=data.name,
            description=data.description,
            is_demo=data.is_demo,
            eligibility_rules=data.eligibility_rules,
            form_schema=data.form_schema,
            required_documents=data.required_documents,
            scoring_weights=data.scoring_weights,
            is_active=True,
            is_locked=False,
        )
        created_version = self.version_repo.create(initial_version)

        # 3. Log audit events
        self.audit_repo.log_event(
            entity_type="SCHEME",
            entity_id=str(created_scheme.id),
            actor_id=actor_id,
            action="SCHEME_CREATED",
            details={
                "scheme_code": created_scheme.scheme_code,
                "name": created_scheme.name,
                "initial_version": created_version.scheme_version,
            },
        )
        self.audit_repo.log_event(
            entity_type="SCHEME",
            entity_id=str(created_version.id),
            actor_id=actor_id,
            action="SCHEME_VERSION_CREATED",
            details={
                "scheme_code": created_version.scheme_code,
                "scheme_version": created_version.scheme_version,
                "is_active": True,
            },
        )

        res = SchemeResponse.model_validate(created_scheme)
        res.active_version_id = created_version.id
        return res

    def update_scheme(
        self,
        scheme_id: uuid.UUID,
        data: SchemeUpdate,
        actor_id: Optional[uuid.UUID] = None,
    ) -> SchemeResponse:
        """
        Updates Scheme catalog identity metadata (name, description, deadline, is_active).
        Does NOT allow directly modifying rules on the Scheme table — rules must be
        versioned in SchemeVersion.
        """
        scheme = self.repo.get_by_id(scheme_id)
        if not scheme:
            raise EntityNotFoundException("Scheme", scheme_id)

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

    # -----------------------------------------------------------------------
    # Version Lifecycle Management (Admin Only)
    # -----------------------------------------------------------------------

    def get_scheme_versions(
        self, scheme_id: uuid.UUID
    ) -> List[SchemeVersionResponse]:
        scheme = self.repo.get_by_id(scheme_id)
        if not scheme:
            raise EntityNotFoundException("Scheme", scheme_id)
        versions = self.version_repo.get_versions_by_scheme_id(scheme_id)
        return [SchemeVersionResponse.model_validate(v) for v in versions]

    def get_scheme_version(
        self, version_id: uuid.UUID
    ) -> SchemeVersionResponse:
        version = self.version_repo.get_by_id(version_id)
        if not version:
            raise EntityNotFoundException("SchemeVersion", version_id)
        return SchemeVersionResponse.model_validate(version)

    def create_scheme_version(
        self,
        scheme_id: uuid.UUID,
        data: SchemeVersionCreate,
        actor_id: Optional[uuid.UUID] = None,
    ) -> SchemeVersionResponse:
        scheme = self.repo.get_by_id(scheme_id)
        if not scheme:
            raise EntityNotFoundException("Scheme", scheme_id)

        # Check unique (scheme_code, scheme_version)
        existing = self.version_repo.get_by_code_and_version(
            scheme.scheme_code, data.scheme_version
        )
        if existing:
            raise DuplicateEntityException(
                f"Version '{data.scheme_version}' already exists for scheme '{scheme.scheme_code}'"
            )

        new_version = SchemeVersion(
            scheme_id=scheme.id,
            scheme_code=scheme.scheme_code,
            scheme_version=data.scheme_version.strip(),
            name=data.name or scheme.name,
            description=data.description or scheme.description,
            is_demo=data.is_demo,
            eligibility_rules=data.eligibility_rules,
            form_schema=data.form_schema,
            required_documents=data.required_documents,
            scoring_weights=data.scoring_weights,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
            is_active=False,  # Activation handled through activate_scheme_version
            is_locked=False,
        )
        created = self.version_repo.create(new_version)

        # If created with is_active requested, transactionally activate
        if data.is_active:
            created = self.version_repo.set_single_active_version(
                scheme.id, created.id
            )

        self.audit_repo.log_event(
            entity_type="SCHEME",
            entity_id=str(created.id),
            actor_id=actor_id,
            action="SCHEME_VERSION_CREATED",
            details={
                "scheme_code": created.scheme_code,
                "scheme_version": created.scheme_version,
                "is_active": created.is_active,
            },
        )
        return SchemeVersionResponse.model_validate(created)

    def update_scheme_version(
        self,
        version_id: uuid.UUID,
        data: SchemeVersionUpdate,
        actor_id: Optional[uuid.UUID] = None,
    ) -> SchemeVersionResponse:
        version = self.version_repo.get_by_id(version_id)
        if not version:
            raise EntityNotFoundException("SchemeVersion", version_id)

        # Strict immutability check for locked versions
        if version.is_locked:
            raise InvalidOperationException(
                f"Scheme version '{version.scheme_code} {version.scheme_version}' is locked and cannot be modified."
            )

        update_dict = data.model_dump(exclude_unset=True)
        for field, val in update_dict.items():
            setattr(version, field, val)

        updated = self.version_repo.update(version)

        # If this is the active version, mirror changes to parent Scheme
        if updated.is_active:
            parent = self.repo.get_by_id(updated.scheme_id)
            if parent:
                parent.name = updated.name
                parent.description = updated.description
                parent.is_demo = updated.is_demo
                parent.eligibility_rules = updated.eligibility_rules
                parent.form_schema = updated.form_schema
                parent.required_documents = updated.required_documents
                parent.scoring_weights = updated.scoring_weights
                self.repo.update(parent)

        self.audit_repo.log_event(
            entity_type="SCHEME",
            entity_id=str(updated.id),
            actor_id=actor_id,
            action="SCHEME_VERSION_UPDATED",
            details={
                "scheme_code": updated.scheme_code,
                "scheme_version": updated.scheme_version,
                "updated_fields": list(update_dict.keys()),
            },
        )
        return SchemeVersionResponse.model_validate(updated)

    def lock_scheme_version(
        self, version_id: uuid.UUID, actor_id: Optional[uuid.UUID] = None
    ) -> SchemeVersionResponse:
        version = self.version_repo.get_by_id(version_id)
        if not version:
            raise EntityNotFoundException("SchemeVersion", version_id)

        version.is_locked = True
        locked = self.version_repo.update(version)

        self.audit_repo.log_event(
            entity_type="SCHEME",
            entity_id=str(locked.id),
            actor_id=actor_id,
            action="SCHEME_VERSION_LOCKED",
            details={
                "scheme_code": locked.scheme_code,
                "scheme_version": locked.scheme_version,
            },
        )
        return SchemeVersionResponse.model_validate(locked)

    def activate_scheme_version(
        self, version_id: uuid.UUID, actor_id: Optional[uuid.UUID] = None
    ) -> SchemeVersionResponse:
        version = self.version_repo.get_by_id(version_id)
        if not version:
            raise EntityNotFoundException("SchemeVersion", version_id)

        # Transactional single-active enforcement
        activated = self.version_repo.set_single_active_version(
            version.scheme_id, version.id
        )

        self.audit_repo.log_event(
            entity_type="SCHEME",
            entity_id=str(activated.id),
            actor_id=actor_id,
            action="SCHEME_VERSION_ACTIVATED",
            details={
                "scheme_code": activated.scheme_code,
                "scheme_version": activated.scheme_version,
            },
        )
        return SchemeVersionResponse.model_validate(activated)

    # -----------------------------------------------------------------------
    # Self-Eligibility Evaluation (Public / Applicant)
    # -----------------------------------------------------------------------

    def check_eligibility(
        self,
        scheme_id: uuid.UUID,
        answers: Dict[str, Any],
        scheme_version_id: Optional[uuid.UUID] = None,
    ) -> EligibilityCheckResponse:
        """
        Runs deterministic eligibility evaluation against scheme rules.
        Does not mutate, write, or affect any application records.
        """
        if scheme_version_id:
            version = self.version_repo.get_by_id(scheme_version_id)
            if not version:
                raise EntityNotFoundException("SchemeVersion", scheme_version_id)
        else:
            version = self.version_repo.get_active_version(scheme_id)
            if not version:
                # Fallback to parent scheme if no version exists
                scheme = self.repo.get_by_id(scheme_id)
                if not scheme:
                    raise EntityNotFoundException("Scheme", scheme_id)
                return RulesEngine.evaluate(
                    scheme.eligibility_rules, answers, is_demo=scheme.is_demo
                )

        eval_result = RulesEngine.evaluate(
            version.eligibility_rules, answers, is_demo=version.is_demo
        )
        return EligibilityCheckResponse(
            eligible=eval_result.eligible,
            summary_message=eval_result.summary_message,
            disclaimer=eval_result.disclaimer,
            is_demo=eval_result.is_demo,
            checks=eval_result.checks,
        )
