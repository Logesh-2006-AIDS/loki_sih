# Ministry of Tribal Affairs - AI-Enabled Scholarship & Fellowship Management System

> **SIH 2026 Evaluation Prototype Notice:** This system is an evaluation-ready prototype engineered for the Smart India Hackathon 2026 Grand Finale. External integrations (such as the PFMS Direct Benefit Transfer gateway and OCR ingestion pipelines) operate in deterministic standalone simulated mode with synthetic test dossiers (`DEMO-*`). No live government funds or sensitive citizen credentials are used.

## Project Overview

The Ministry of Tribal Affairs (MoTA) AI-Enabled Scholarship & Fellowship Management System is an evaluation-grade digital portal engineered to automate, streamline, and secure the end-to-end lifecycle of scholarship schemes for Scheduled Tribe (ST) students across India.

The platform provides an integrated environment for tribal scholars, desk scrutiny officers, selection committees, and ministry administrators. It pairs automated document optical character recognition (OCR) and rule verification engines with a human-in-the-loop desk scrutiny workflow, strict role-based access control, tamper-evident audit logging, and closed-loop deficiency resolution.

---

## Core Capabilities

### 1. Dynamic Scheme Engine and Self-Eligibility Explorer
- Public scheme explorer presenting active national scholarship schemes (such as NFST and NOS) with clear eligibility criteria, funding details, and required document checklists.
- Interactive self-eligibility checker allowing students to evaluate their qualification across community, age, academic thresholds, and income limits prior to initiating an application.
- Authoritative scheme versioning system enabling administrators to configure, version, lock, and activate rule definitions without breaking historical dossiers.

### 2. Dynamic Application Wizard and Document Vault
- Multi-step application submission wizard bound to scheme-specific form schemas and validation rules.
- Draft autosave functionality allowing applicants to complete dossiers across multiple sessions.
- Secure document upload subsystem supporting MIME verification, magic-byte inspection, file size boundaries, and extension whitelisting.
- Storage layer using pure UUID-based file paths to prevent directory traversal and metadata exposure.

### 3. Automated OCR and AI Document Verification Pipeline
- Asynchronous document processing pipeline extracting text and structured data from government-issued certificates (Caste Certificates, Income Certificates, Academic Marksheets, and Admission Letters).
- Field-level matching matrix comparing application claims against extracted document evidence with confidence scoring and fuzzy string normalization.
- Non-punitive AI policy: AI findings never reject an application. Ambiguities, mismatches, or low extraction confidences are flagged for human officer scrutiny.

### 4. Officer Scrutiny Workbench and Human Verification
- Workload queue with role-based jurisdiction filtering (National, State-level, or Scheme-specific desks) and applicant PII minimization.
- Side-by-side verification workbench juxtaposing applicant form entries against extracted OCR text and high-resolution document previews.
- Document-level scrutiny determinations (Verified, Resubmission Required, Rejected). Rejection of an individual document never triggers automated application rejection.
- Structured AI override mechanism requiring mandatory justification when an officer accepts documents with low AI confidence or detected mismatches.

### 5. Deficiency Management and Applicant Resubmission Workflow
- Itemized deficiency tracking notifying applicants of specific document defects without exposing internal officer notes.
- In-place replacement document upload enforcing document lineage tracking (v1, v2, v3) with parent and superseded pointers.
- Concurrency control with database row locking guaranteeing exactly one active version per document lineage.
- Strict applicant immutability preventing modification of form fields or approved documents while an application is in deficient status.
- Deficiency resolution semantics requiring human verification of replacement documents before a deficiency is marked resolved.

### 6. Audit Trail and Security Architecture
- Immutable audit log recording every user action, workflow state transition, document inspection, and administrative decision.
- JWT-based authentication with role-based access control (Applicant, Officer, Committee Member, Administrator).
- Tenant and object-level authorization preventing cross-user data leakage and horizontal privilege escalation.

---

## Architecture and Technology Stack

### Backend
- Language: Python 3.12+
- Framework: FastAPI (high performance, asynchronous REST API)
- Database ORM: SQLAlchemy 2.0 with PostgreSQL 18
- Migrations: Alembic
- Authentication: OAuth2 with JWT (HS256) and Passlib (Bcrypt)
- PDF/OCR Processing: PyMuPDF (fitz) and Tesseract OCR engine
- Testing: Pytest with AnyIO/AsyncIO test runners

### Frontend
- Framework: React 18 with TypeScript
- Build Tool: Vite
- Styling: Tailwind CSS
- Routing: React Router DOM v6
- Icons: Lucide React
- HTTP Client: Axios with request/response interceptors

### Database and Infrastructure
- Database: PostgreSQL 18
- Containerization: Docker and Docker Compose

---

## System Requirements

Before running the application, ensure the following software is installed on your machine:
- Python 3.12 or higher
- Node.js 18.x or 20.x and npm 9.x or higher
- PostgreSQL 18 (or Docker Desktop if running via containers)
- Git

---

## Installation and Setup (Local Development)

Follow these instructions to run the website locally on your machine.

### Step 1: Clone the Repository
```bash
git clone <repository_url>
cd loki_sih
```

### Step 2: Configure Environment Variables

Create a `.env` file in the `backend/` directory or update the existing file:
```env
PROJECT_NAME="AI-Enabled Scholarship & Fellowship Management System"
API_V1_STR="/api/v1"

# Database Configuration (PostgreSQL 18)
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_postgres_password
POSTGRES_DB=loki_db
DATABASE_URL=postgresql://postgres:your_postgres_password@localhost:5432/loki_db

# Security
JWT_SECRET_KEY=demo_secret_key_change_in_production_tribal_affairs_sih_2026
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# File Storage
STORAGE_PATH=../storage

# CORS
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
```

Ensure the target PostgreSQL database exists. If it does not exist, create it:
```sql
CREATE DATABASE loki_db;
```

### Step 3: Set Up and Start the Backend

1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   - On Windows (PowerShell):
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - On Linux / macOS:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run database migrations:
   ```bash
   python -m alembic upgrade head
   ```

5. Seed the database with demo users, roles, and default schemes:
   ```bash
   python scripts/seed.py
   ```

6. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

The backend server will be operational at:
- API Root: `http://localhost:8000`
- Interactive API Documentation (Swagger UI): `http://localhost:8000/api/v1/docs`
- Alternative API Documentation (ReDoc): `http://localhost:8000/api/v1/redoc`

### Step 4: Set Up and Start the Frontend

1. Open a new terminal window and navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```

2. Install Node dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```

The frontend web application will be accessible at:
- Web Portal: `http://localhost:5173`

The Vite development server is pre-configured to proxy all `/api` requests directly to `http://localhost:8000`.

---

## Running with Docker Compose

If you have Docker and Docker Compose installed, you can build and run the entire stack with a single command:

1. In the root directory (`loki_sih`), execute:
   ```bash
   docker-compose up --build
   ```

2. This will spin up:
   - PostgreSQL 18 container on port 5432
   - FastAPI Backend container on port 8000
   - React Frontend container on port 5173

3. To stop the containers:
   ```bash
   docker-compose down
   ```

---

## Default Demo Credentials

The database seeding script (`scripts/seed.py`) provisions standard accounts for testing each functional role in the system. The password for all default accounts is: `Demo@12345`

| Role | Email Address | Description | Primary Functions |
|---|---|---|---|
| Applicant | applicant@demo.gov.in | Tribal Student Scholar | Check eligibility, draft dossiers, upload certificates, resolve deficiencies |
| Desk Officer | officer@demo.gov.in | Regional Scrutiny Officer | Review application queues, inspect OCR extractions, flag deficiencies |
| Committee Member | committee@demo.gov.in | Selection Committee Member | Review shortlisted applications, evaluate academic merit, submit scores |
| Administrator | admin@demo.gov.in | System Administrator | Manage scheme configurations, lock versions, audit system events |

---

## Running the Automated Test Suite

The repository includes a comprehensive automated test suite covering authentication, RBAC, scheme engine rules, dynamic forms, file safety, OCR pipeline handoffs, officer scrutiny, and deficiency resubmission.

1. Ensure you are in the `backend` directory with the virtual environment activated:
   ```bash
   cd backend
   ```

2. Run the complete pytest suite:
   ```bash
   python -m pytest tests/ -v
   ```

3. Verify frontend TypeScript compilation and production build:
   ```bash
   cd ../frontend
   npm run build
   ```

---

## Directory Structure

```text
loki_sih/
├── backend/
│   ├── alembic/                 # Database schema migration scripts
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py          # Dependency injection (Auth, DB, RBAC)
│   │   │   └── routes/          # API route definitions
│   │   ├── core/                # Configuration, security, exceptions, state machines
│   │   ├── db/                  # Database session and declarative base
│   │   ├── models/              # SQLAlchemy database models
│   │   ├── repositories/        # Data access layer
│   │   ├── schemas/             # Pydantic validation schemas
│   │   └── services/            # Core business logic (OCR, Scrutiny, Deficiency)
│   ├── scripts/
│   │   └── seed.py              # Database seeding script
│   └── tests/                   # Automated pytest suite
├── frontend/
│   ├── public/                  # Static assets
│   ├── src/
│   │   ├── components/          # Reusable React components
│   │   ├── pages/               # Route-level views (Applicant, Officer, Admin)
│   │   ├── services/            # Axios API client services
│   │   ├── types/               # TypeScript interface definitions
│   │   ├── App.tsx              # Root component and client routing
│   │   └── main.tsx             # Application entry point
│   ├── package.json
│   └── vite.config.ts
├── storage/                     # Uploaded document storage
├── docker-compose.yml           # Multi-container deployment specification
└── README.md                    # System documentation
```

---

## Implementation Roadmap and Status

- Phase 0: Foundation, Authentication, PostgreSQL Persistence, and RBAC (Completed)
- Phase 1: Scheme Engine, Rule Evaluation, Scheme Versioning, and Self-Eligibility (Completed)
- Phase 2: Dynamic Application Wizard, Document Uploads, and State Machines (Completed)
- Phase 3: OCR Extraction Pipeline and AI-Assisted Document Verification (Completed)
- Phase 4: Desk Officer Scrutiny Workbench and Human Override Workflow (Completed)
- Phase 5: Closed-Loop Deficiency Management and Document Resubmission (Completed)
- Phase 6: Merit Scoring, Quota Allocation, and Committee Selection (Next Phase)
- Phase 7: Sanction Orders, Disbursement Tracking, and PFMS Integration (Planned)
- Phase 8: Renewal Workflows and Ongoing Academic Progression (Planned)
- Phase 9: Reporting, Analytics Dashboard, and Ministry Audit Export (Planned)

---

## Technical Support and Maintenance

For configuration assistance, database connection adjustments, or extending validation rule sets, consult the `/api/v1/docs` endpoint when running the server, or review the schema files in `backend/app/schemas/`.





Instructions for Running the Whole Website
Prerequisites
Make sure you have the following installed on your machine:

Python 3.12 or higher
Node.js 18.x or 20.x with npm 9.x or higher
PostgreSQL 18 (running locally on port 5432) OR Docker Desktop
Method A: Local Development Setup (Recommended)
1. Backend Setup
Open a terminal and navigate to the backend directory:

bash
cd d:/loki/loki_sih/backend
Create and activate a Python virtual environment:

On Windows (PowerShell):
powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
On Linux / macOS:
bash
python3 -m venv venv
source venv/bin/activate
Install required Python packages:

bash
pip install -r requirements.txt
Verify database credentials in backend/.env:

env
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=loki_db
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/loki_db
Run database migrations to apply the latest schema:

bash
python -m alembic upgrade head
Seed the database with default users and schemes:

bash
python scripts/seed.py
Start the backend API server:

bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
The backend will be running at http://localhost:8000. API documentation is available at http://localhost:8000/api/v1/docs.

2. Frontend Setup
Open a second terminal and navigate to the frontend directory:

bash
cd d:/loki/loki_sih/frontend
Install Node dependencies:

bash
npm install
Start the Vite development server:

bash
npm run dev
The frontend web portal will be accessible at:

text
http://localhost:5173
All API calls from the browser to /api are automatically proxied by Vite to the backend on http://localhost:8000.

Method B: Docker Compose Setup
If you prefer to run the entire stack inside containers without local installations of Python and Node:

Open a terminal in the root directory:

bash
cd d:/loki/loki_sih
Build and start all services (PostgreSQL, FastAPI Backend, React Frontend):

bash
docker-compose up --build
Access the portal at http://localhost:5173.

To stop the containers:

bash
docker-compose down
Default Login Credentials
The database seed script (scripts/seed.py) configures four default user accounts covering all portal roles. The password for all accounts is: Demo@12345

Role	Email Address	Password	Function in System
Applicant	

applicant@demo.gov.in
Demo@12345	Browse schemes, test eligibility, fill applications, upload certificates, resolve deficiencies
Scrutiny Officer	

officer@demo.gov.in
Demo@12345	Access officer queue, examine side-by-side OCR evidence, flag deficiencies, override AI flags
Committee Member	

committee@demo.gov.in
Demo@12345	Review verified applications, evaluate academic merit, enter scores
Administrator	

admin@demo.gov.in
Demo@12345	Manage schemes and versions, lock configurations, inspect audit logs
To verify backend integrity and all 141 unit/integration tests:

```bash
cd backend
python -m pytest tests/ -q
```

To verify frontend TypeScript compilation and production bundling:

```bash
cd frontend
npm run build
```

---

## Phase 9 Hardening & SIH Evaluation Documentation

- [Deployment & Security Hardening Guide](docs/deployment.md)
- [SIH 2026 Grand Finale Evaluation & Demo Script](docs/sih_demo_guide.md)




How to View the Data:
Option 1: Directly via Terminal (psql in Docker)
Run this command in PowerShell:

docker exec -it loki_postgres psql -U postgres -d loki_db -c "SELECT id, full_name, email, role, account_status, is_active, password_hash FROM users;"


To see staff registration requests and rejection reasons:

docker exec -it loki_postgres psql -U postgres -d loki_db -c "SELECT id, requested_role, employee_id, department, status, rejection_reason FROM staff_registration_requests;"





Method C: Using pgAdmin 4
Open pgAdmin 4.
Right-click Servers in the left panel ➔ Register ➔ Server...
In the General tab:
Name: Loki Local DB
In the Connection tab:
Host name/address: localhost
Port: 5432
Maintenance database: loki_db
Username: postgres
Password: postgres_secure_password
Check Save password?.
Click Save.
Expand Loki Local DB ➔ Databases ➔ loki_db ➔ Schemas ➔ public ➔ Tables ➔ right-click users ➔ View/Edit Data ➔ All Rows.
NOTE

Make sure the Docker container is running before attempting to connect. You can verify it is running in your terminal anytime with:

powershell
docker ps --filter "name=loki_postgres"