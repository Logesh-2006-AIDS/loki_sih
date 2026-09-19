import uuid
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app.models.scheme_version import SchemeVersion
from app.models.scheme import Scheme
from app.repositories.base_repo import BaseRepository


class SchemeVersionRepository(BaseRepository[SchemeVersion]):
    def __init__(self, db: Session):
        super().__init__(SchemeVersion, db)

    def get_by_code_and_version(
        self, scheme_code: str, scheme_version: str
    ) -> Optional[SchemeVersion]:
        query = select(SchemeVersion).where(
            SchemeVersion.scheme_code == scheme_code.upper().strip(),
            SchemeVersion.scheme_version == scheme_version.strip(),
        )
        return self.db.execute(query).scalar_one_or_none()

    def get_versions_by_scheme_id(self, scheme_id: uuid.UUID) -> List[SchemeVersion]:
        query = (
            select(SchemeVersion)
            .where(SchemeVersion.scheme_id == scheme_id)
            .order_by(SchemeVersion.created_at.desc())
        )
        return list(self.db.execute(query).scalars().all())

    def get_active_version(self, scheme_id: uuid.UUID) -> Optional[SchemeVersion]:
        query = (
            select(SchemeVersion)
            .where(
                SchemeVersion.scheme_id == scheme_id,
                SchemeVersion.is_active.is_(True),
            )
            .order_by(SchemeVersion.created_at.desc())
        )
        return self.db.execute(query).scalars().first()

    def set_single_active_version(
        self, scheme_id: uuid.UUID, version_id: uuid.UUID
    ) -> SchemeVersion:
        """
        Enforces that strictly ONE active version exists for a scheme at any time.
        Transactionally deactivates all other versions of the scheme and activates target version.
        Synchronizes parent Scheme's read-only mirror columns.
        """
        # 1. Deactivate all versions of this scheme
        self.db.execute(
            update(SchemeVersion)
            .where(SchemeVersion.scheme_id == scheme_id)
            .values(is_active=False)
        )

        # 2. Activate the specified version
        target = self.get_by_id(version_id)
        if not target or target.scheme_id != scheme_id:
            raise ValueError("Target version not found for this scheme.")

        target.is_active = True
        self.db.add(target)

        # 3. Synchronize parent Scheme record mirror fields for legacy compatibility
        parent = self.db.get(Scheme, scheme_id)
        if parent:
            parent.scheme_version = target.scheme_version
            parent.name = target.name
            parent.description = target.description
            parent.is_demo = target.is_demo
            parent.eligibility_rules = target.eligibility_rules
            parent.form_schema = target.form_schema
            parent.required_documents = target.required_documents
            parent.scoring_weights = target.scoring_weights
            self.db.add(parent)

        self.db.commit()
        self.db.refresh(target)
        return target
