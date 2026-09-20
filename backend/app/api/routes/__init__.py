from fastapi import APIRouter
from app.api.routes import (
    health,
    auth,
    users,
    schemes,
    applications,
    documents,
    notifications,
    audit,
    officer,
    deficiencies,
    committee,
    merit,
    analytics,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(schemes.router, prefix="/schemes", tags=["Schemes"])
api_router.include_router(applications.router, prefix="/applications", tags=["Applications"])
api_router.include_router(deficiencies.router, prefix="/applications", tags=["Deficiencies & Resubmission"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(audit.router, prefix="/audit", tags=["Audit Logs"])
api_router.include_router(officer.router, prefix="/officer", tags=["Officer Scrutiny"])
api_router.include_router(committee.router, prefix="/committee", tags=["Committee Scrutiny & Selection"])
api_router.include_router(merit.router, prefix="/merit", tags=["Merit Scoring & Ranking"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics & Monitoring"])

