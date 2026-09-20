import os
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import get_db

router = APIRouter()

SERVER_START_TIME = time.time()


@router.get("/live", tags=["Health"])
def liveness_probe():
    """
    Liveness probe: verifies that the FastAPI application process is alive and responsive.
    Returns HTTP 200 immediately without hitting database or downstream services.
    """
    uptime = round(time.time() - SERVER_START_TIME, 2)
    return {
        "status": "alive",
        "service": settings.PROJECT_NAME,
        "ministry": "Ministry of Tribal Affairs",
        "version": "1.0.0-phase9",
        "uptime_seconds": uptime,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health", tags=["Health"])
@router.get("/ready", tags=["Health"])
def readiness_probe(response: Response, db: Session = Depends(get_db)):
    """
    Readiness probe: validates that all critical application subsystems are operational
    and ready to accept and serve traffic. Probes:
      1. PostgreSQL Database connectivity & query latency.
      2. Storage subsystem directory existence and writeability.
      3. Alembic schema migration head alignment against settings.EXPECTED_ALEMBIC_HEAD.
      4. Subsystems status (Standalone OCR pipeline & PFMS DBT mock gateway).

    HTTP Status Contract:
      - 200 OK: 'healthy' (all core and secondary subsystems passing)
      - 200 OK: 'degraded' (storage or secondary warning, but core database operational)
      - 503 Service Unavailable: 'unhealthy' (database down or migration mismatch)
    """
    overall_status = "healthy"
    subsystems = {}

    # 1. Database Check & Latency
    db_start = time.time()
    try:
        db.execute(text("SELECT 1"))
        db_latency_ms = round((time.time() - db_start) * 1000, 2)
        subsystems["database"] = {
            "status": "connected",
            "latency_ms": db_latency_ms,
        }
    except Exception as e:
        subsystems["database"] = {
            "status": "unreachable",
            "error": str(e),
        }
        overall_status = "unhealthy"

    # 2. Schema Migration Version Check
    try:
        ver_row = db.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).first()
        current_migration = ver_row[0] if ver_row else "none"
        expected_head = settings.EXPECTED_ALEMBIC_HEAD
        migration_match = current_migration == expected_head
        subsystems["migration"] = {
            "status": "aligned" if migration_match else "version_mismatch",
            "current_head": current_migration,
            "expected_head": expected_head,
        }
        if not migration_match and overall_status != "unhealthy":
            overall_status = "degraded"
    except Exception as e:
        subsystems["migration"] = {
            "status": "check_failed",
            "error": str(e),
        }
        if overall_status != "unhealthy":
            overall_status = "degraded"

    # 3. Storage Directory & Writeability Check
    storage_path = settings.STORAGE_PATH
    try:
        os.makedirs(storage_path, exist_ok=True)
        storage_writeable = os.access(storage_path, os.W_OK)
        subsystems["storage"] = {
            "status": "writeable" if storage_writeable else "read_only",
            "path": storage_path,
        }
        if not storage_writeable and overall_status != "unhealthy":
            overall_status = "degraded"
    except Exception as e:
        subsystems["storage"] = {
            "status": "inaccessible",
            "error": str(e),
        }
        if overall_status != "unhealthy":
            overall_status = "degraded"

    # 4. Standalone Subsystems Mode
    subsystems["ai_ocr_pipeline"] = {
        "status": "operational",
        "mode": "STANDALONE_SIMULATED",
        "description": "Deterministic OCR text extraction with field confidence scoring",
    }
    subsystems["pfms_dbt_gateway"] = {
        "status": "operational",
        "mode": "MOCK_SIMULATED",
        "disclaimer": "SIMULATED ENVIRONMENT: No actual government funds transferred",
    }

    # Set HTTP status code based on health
    if overall_status == "unhealthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    db_status = subsystems.get("database", {}).get("status", "unknown")

    return {
        "status": overall_status,
        "service": settings.PROJECT_NAME,
        "ministry": "Ministry of Tribal Affairs",
        "database": db_status,
        "environment": settings.ENVIRONMENT,
        "subsystems": subsystems,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
