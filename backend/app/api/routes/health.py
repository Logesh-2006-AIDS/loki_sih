from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import get_db

router = APIRouter()


@router.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unreachable: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "service": "AI-Enabled Scholarship & Fellowship Management System (Phase 0)",
        "ministry": "Ministry of Tribal Affairs",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
