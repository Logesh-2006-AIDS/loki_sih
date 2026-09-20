# Ministry of Tribal Affairs (MoTA) — Fellowship & Scholarship System
## Deployment & Infrastructure Hardening Guide (Phase 9)

This document provides complete instructions for deploying the system in local, containerized (Docker), and cloud VM environments.

---

## 1. System Architecture & Boundaries

```
                 [ Reverse Proxy / Nginx (Port 80/443) ]
                     │ client_max_body_size 25M
                     │ Gzip Compression & Static Asset Caching
                     │ Hardened Security Headers (CSP, HSTS, Clickjacking)
         ┌───────────┴───────────┐
         ▼                       ▼
 [ Frontend SPA (Vite/React) ]   [ Backend API / FastAPI (Port 8000) ]
   - Non-root Nginx                - Non-root appuser (UID: 10001)
   - SPA Fallback                  - In-memory rate limiting (30 req/min)
   - Guided Evaluation Tour        - Decoupled /health & /api/health probes
                                   - Standalone OCR & Mock PFMS Gateway
                                         │
                                         ▼
                             [ PostgreSQL 16 (Port 5432) ]
                               - Schema Head: 0008_phase8_fellowships
                               - Row-level locking & payment idempotency
```

### Scope & Architectural Clarification
- **SIH Evaluation Prototype**: Built as a hardened, single-instance containerized system for high-performance evaluation by jury members.
- **Rate Limiting**: Uses a sliding-window in-memory rate limiter scoped to `/auth/login` and `/auth/demo-login`. In distributed multi-region enterprise production, rate limiting must be delegated to Redis or an API Gateway/WAF.
- **External Gateways**: Document OCR and PFMS DBT disbursement transfers operate in **deterministic standalone simulated mode**. No real banking credentials or live government funds are touched.

---

## 2. Docker Multi-Container Deployment (Recommended)

### Prerequisites
- Docker Engine 24.0+
- Docker Compose v2.20+
- 4 GB RAM minimum

### One-Command Deployment

```bash
# 1. Clone repository
git clone https://github.com/mota-sih/tribal-scholarship-portal.git
cd tribal-scholarship-portal

# 2. Configure environment variables
cp .env.example .env
# Adjust passwords or secrets if needed

# 3. Build and launch all services in background
docker compose up --build -d

# 4. Verify running containers
docker compose ps
```

### Service Endpoints

| Service | Port | Endpoint | Health Probe |
|---|---|---|---|
| **Frontend Web App** | `80` | `http://localhost/` | Built-in Nginx status |
| **Backend API Docs** | `8000` | `http://localhost:8000/api/v1/docs` | `GET /health` (Liveness) |
| **Readiness Check** | `8000` | `http://localhost:8000/api/health` | `GET /api/health` |
| **PostgreSQL DB** | `5432` | `localhost:5432` (db: `loki_db`) | `pg_isready` |

### Running the SIH Master Demo Seeder in Docker

```bash
docker compose exec backend python scripts/seed_sih_demo.py
```

---

## 3. Local Bare-Metal Development Deployment

### Prerequisites
- Python 3.12+ (`py -3.12`)
- Node.js 20+ & npm
- PostgreSQL 16 running locally on port 5432

### Step-by-Step Setup

```bash
# 1. Database Setup
# Ensure PostgreSQL is running and database 'loki_db' exists:
# psql -U postgres -c "CREATE DATABASE loki_db;"

# 2. Backend Setup
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

pip install -r requirements.txt

# Run migrations (Schema head: 0008_phase8_fellowships)
alembic upgrade head

# Seed synthetic demo data
python scripts/seed_sih_demo.py

# Launch backend API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

In a separate terminal:

```bash
# 3. Frontend Setup
cd frontend
npm install
npm run build    # Verify production build compiles cleanly
npm run dev      # Start Vite local development server at http://localhost:5173
```

---

## 4. Security Hardening Configuration

### 1. Non-Root Execution
The backend `Dockerfile` enforces non-root execution via a dedicated system user:
```dockerfile
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin -M appuser
USER appuser:appgroup
```

### 2. HTTP Security Headers
All API responses automatically attach standard defense-in-depth headers:
- `X-Frame-Options: SAMEORIGIN` (prevents clickjacking while allowing embedded PDF inspection)
- `X-Content-Type-Options: nosniff` (prevents MIME-type sniffing attacks)
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy`: Concrete policy forbidding wildcard `*` allowances.
- `Strict-Transport-Security`: Environment-aware HSTS enabled when `ENVIRONMENT=production`.

### 3. Payload Size Guardrails
- Global network limit: `25 MB` via `PayloadSizeLimitMiddleware` and Nginx `client_max_body_size 25M`.
- Document upload limit: `5 MB` strictly enforced by Phase 2 document validation logic.

### 4. Single-Instance Rate Limiting
- Scoped strictly to authentication endpoints (`/auth/login`, `/auth/demo-login`).
- Limits bursts to 30 requests/minute per client IP (respecting `X-Forwarded-For` reverse-proxy headers).

---

## 5. Health Monitoring & Orchestrator Probes

The system separates liveness from readiness to prevent cascading restarts during high load:

1. **Liveness Probe** (`GET /health`):
   - Confirms process is responsive without querying downstream database.
   - HTTP 200 OK: `{"status": "alive", "version": "1.0.0-phase9", ...}`

2. **Readiness Probe** (`GET /api/health`):
   - Validates PostgreSQL connectivity and queries latency in milliseconds.
   - Checks storage directory writeability.
   - Verifies Alembic migration head matches `0008_phase8_fellowships`.
   - Returns subsystem statuses (AI OCR pipeline, PFMS gateway).
   - Responds HTTP 503 if the database is unreachable.
