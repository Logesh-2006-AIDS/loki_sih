import uuid
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.application import Application
from app.repositories.base_repo import BaseRepository


class ApplicationRepository(BaseRepository[Application]):
    def __init__(self, db: Session):
        super().__init__(Application, db)

    def get_by_reference_id(self, ref_id: str) -> Optional[Application]:
        query = select(Application).where(Application.reference_id == ref_id.strip())
        return self.db.execute(query).scalar_one_or_none()

    def get_by_applicant(self, applicant_id: uuid.UUID) -> List[Application]:
        query = select(Application).where(Application.applicant_id == applicant_id)
        return list(self.db.execute(query).scalars().all())

    def get_by_scheme(self, scheme_id: uuid.UUID) -> List[Application]:
        query = select(Application).where(Application.scheme_id == scheme_id)
        return list(self.db.execute(query).scalars().all())
