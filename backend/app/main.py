from datetime import datetime, timezone
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.config import settings
from app.core.exceptions import AppException
from app.api.routes import api_router
from app.api.routes.health import router as health_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0-phase0",
    description=(
        "Production-oriented foundation for AI-Enabled Scholarship & Fellowship Management System "
        "(Ministry of Tribal Affairs). Provides authentication, RBAC, PostgreSQL persistence, "
        "audit logging, and architectural contracts for Phase 1+ AI/OCR integration."
    ),
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

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
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "status_code": exc.status_code,
            "details": exc.details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Request validation failed",
            "status_code": 422,
            "details": exc.errors(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.get("/", tags=["Root"])
def root():
    return {
        "service": settings.PROJECT_NAME,
        "ministry": "Ministry of Tribal Affairs",
        "phase": "Phase 0 (Production-Oriented Foundation)",
        "docs_url": f"{settings.API_V1_STR}/docs",
        "health_check": f"{settings.API_V1_STR}/health",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
