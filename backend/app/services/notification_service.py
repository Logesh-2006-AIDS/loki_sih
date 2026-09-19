import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.enums import NotificationChannel
from app.models.notification import Notification
from app.schemas.notification import NotificationResponse


class NotificationService:
    """
    Notification dispatch service supporting multi-channel delivery
    (In-App, Email, SMS) with in-app database persistence.
    """

    def __init__(self, db: Session):
        self.db = db

    def send_notification(
        self,
        user_id: uuid.UUID,
        title: str,
        message: str,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        application_id: Optional[uuid.UUID] = None,
    ) -> NotificationResponse:
        notification = Notification(
            user_id=user_id,
            application_id=application_id,
            channel=channel,
            title=title,
            message=message,
            status="SENT",
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)

        # In Phase 0, external dispatch (SMTP/SMS gateway) is stubbed.
        # In-app notifications are persisted directly to PostgreSQL.
        return NotificationResponse.model_validate(notification)

    def list_user_notifications(
        self, user_id: uuid.UUID, limit: int = 50
    ) -> List[NotificationResponse]:
        query = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        notifications = self.db.execute(query).scalars().all()
        return [NotificationResponse.model_validate(n) for n in notifications]
