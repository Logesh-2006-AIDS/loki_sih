from datetime import datetime, timezone
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.middleware import (
    SecurityHeadersMiddleware,
    PayloadSizeLimitMiddleware,
    InMemoryRateLimiter,
)
from app.api.routes import api_router
from app.api.routes.health import router as health_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0-phase9",
    description=(
        "Ministry of Tribal Affairs AI-Enabled Scholarship & Fellowship Management System. "
        "SIH 2026 Evaluation Ready. Provides automated OCR extraction, human-in-the-loop desk scrutiny, "
        "closed-loop deficiency management, blind committee evaluation, dynamic merit selection, "
        "executive analytics, and post-selection fellowship DBT disbursements."
    ),
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Configure Middlewares (Order: RateLimiter -> PayloadSizeLimit -> SecurityHeaders -> CORS)
app.add_middleware(
    InMemoryRateLimiter,
    requests_per_minute=settings.RATE_LIMIT_LOGIN_PER_MINUTE,
)
app.add_middleware(PayloadSizeLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Also expose direct /api/health for convenient probe checks
app.include_router(health_router, prefix="/api")


@app.exception_handler(AppException)
async def handle_app_exception(request: Request, exc: AppException):
    content = {
        "error": exc.message,
        "status_code": exc.status_code,
        "details": exc.details,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if getattr(exc, "reason", None) is not None:
        content["reason"] = exc.reason
    return JSONResponse(
        status_code=exc.status_code,
        content=content,
    )


from fastapi.encoders import jsonable_encoder


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Request validation failed",
            "status_code": 422,
            "details": jsonable_encoder(exc.errors()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.get("/health", tags=["Health"])
def liveness_probe():
    """Liveness probe: verifies process responsiveness without hitting downstream services."""
    return {
        "status": "alive",
        "service": settings.PROJECT_NAME,
        "ministry": "Ministry of Tribal Affairs",
        "version": "1.0.0-phase9",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/", tags=["Root"])
def root():
    return {
        "service": settings.PROJECT_NAME,
        "ministry": "Ministry of Tribal Affairs",
        "phase": "Phase 0-9 (Security, Deployment & SIH Grand Finale Demo)",
        "version": "1.0.0-phase9",
        "status": "operational",
        "docs_url": f"{settings.API_V1_STR}/docs",
        "health_check": f"{settings.API_V1_STR}/health",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
