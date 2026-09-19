from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.scheme import Scheme
from app.repositories.base_repo import BaseRepository


class SchemeRepository(BaseRepository[Scheme]):
    def __init__(self, db: Session):
        super().__init__(Scheme, db)

    def get_by_code(self, scheme_code: str) -> Optional[Scheme]:
        query = select(Scheme).where(Scheme.scheme_code == scheme_code.upper().strip())
        return self.db.execute(query).scalar_one_or_none()

    def get_active_schemes(self) -> List[Scheme]:
        query = select(Scheme).where(Scheme.is_active.is_(True))
        return list(self.db.execute(query).scalars().all())
