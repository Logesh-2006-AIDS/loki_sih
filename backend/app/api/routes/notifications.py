from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.notification import NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get(
    "/",
    response_model=List[NotificationResponse],
    summary="List notifications for current authenticated user",
)
def list_notifications(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NotificationService(db)
    return service.list_user_notifications(user_id=current_user.id, limit=limit)
