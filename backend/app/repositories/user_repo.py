import uuid
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.user import User
from app.repositories.base_repo import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_email(self, email: str) -> Optional[User]:
        query = select(User).where(User.email == email.lower().strip())
        return self.db.execute(query).scalar_one_or_none()

    def get_by_role(self, role: str) -> List[User]:
        query = select(User).where(User.role == role)
        return list(self.db.execute(query).scalars().all())
