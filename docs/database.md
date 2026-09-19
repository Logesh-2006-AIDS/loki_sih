# Database Schema & Data Dictionary: PostgreSQL 18
**Ministry of Tribal Affairs | AI-Enabled Scholarship & Fellowship Management System**

---

## 1. Database Overview

The persistence architecture strictly utilizes **PostgreSQL 18** (database: `loki_db`). Schema migrations are automated and version-controlled using **Alembic**.

All primary keys use RFC 4122 **UUIDv4** types. Timestamps store UTC timezone-aware datetimes (`TIMESTAMP WITH TIME ZONE`). Unstructured or dynamic data (form schemas, eligibility rules, OCR raw extractions, and scoring breakdowns) leverage PostgreSQL's binary JSON format (`JSONB`).

---

## 2. Table Catalog (14 Tables)

### 2.1 Core Identity & Schemes

#### `users`
Stores system actors with role-based segregation.
- `id` (UUID, PK)
- `full_name` (VARCHAR(128))
- `email` (VARCHAR(255), UNIQUE, INDEX)
- `phone` (VARCHAR(32), NULLABLE)
- `password_hash` (VARCHAR(255))
- `role` (VARCHAR(32), INDEX) - `APPLICANT`, `OFFICER`, `COMMITTEE`, `ADMIN`
- `is_active` (BOOLEAN, DEFAULT TRUE)
- `mocked_ekyc_ref` (VARCHAR(64), NULLABLE)
- `created_at`, `updated_at` (TIMESTAMPTZ)

#### `schemes`
Configures fellowship and scholarship schemes (e.g. NFST, NOS).
- `id` (UUID, PK)
- `scheme_code` (VARCHAR(32), UNIQUE, INDEX) - e.g. `NFST`, `NOS`
- `name` (VARCHAR(255))
- `description` (TEXT)
- `scheme_version` (VARCHAR(16), DEFAULT '1.0') - *Note: Foundation for future scheme version management*
- `is_demo` (BOOLEAN, DEFAULT TRUE) - *Marks demo/prototype rules*
- `eligibility_rules` (JSONB) - Dynamic rule parameters
- `form_schema` (JSONB) - Dynamic form fields
- `required_documents` (JSONB) - List of mandatory documents
- `scoring_weights` (JSONB) - Merit calculation weights
- `deadline` (TIMESTAMPTZ, NULLABLE)
- `is_active` (BOOLEAN, DEFAULT TRUE)
- `created_at`, `updated_at` (TIMESTAMPTZ)

---

### 2.2 Applications & Documents

#### `applications`
Central entity capturing applicant submissions.
- `id` (UUID, PK)
- `reference_id` (VARCHAR(64), UNIQUE, INDEX) - e.g. `MTA-NFST-202609-AB12CD`
- `applicant_id` (UUID, FK -> `users.id`, INDEX)
- `scheme_id` (UUID, FK -> `schemes.id`, INDEX)
- `status` (VARCHAR(32), INDEX) - State machine managed status
- `form_data` (JSONB) - Submitted application form values
- `merit_score` (FLOAT, NULLABLE)
- `submitted_at` (TIMESTAMPTZ, NULLABLE)
- `created_at`, `updated_at` (TIMESTAMPTZ)

#### `documents`
Stores metadata and filesystem pointers for uploaded evidence.
- `id` (UUID, PK)
- `application_id` (UUID, FK -> `applications.id`, INDEX)
- `document_type` (VARCHAR(64), INDEX) - e.g. `CASTE_CERTIFICATE`, `PG_MARKSHEET`
- `original_filename` (VARCHAR(255))
- `storage_path` (VARCHAR(512))
- `mime_type` (VARCHAR(128))
- `file_size` (INTEGER)
- `status` (VARCHAR(32), INDEX) - `PENDING`, `PROCESSING`, `VERIFIED`, `FLAGGED`, `REJECTED`, `RESUBMISSION_REQUIRED`
- `uploaded_at`, `updated_at` (TIMESTAMPTZ)

#### `document_verifications`
Detailed verification records from manual or AI checks.
- `id` (UUID, PK)
- `document_id` (UUID, FK -> `documents.id`, INDEX)
- `verification_status` (VARCHAR(32))
- `extracted_data` (JSONB)
- `matched_fields` (JSONB)
- `mismatched_fields` (JSONB)
- `verification_source` (VARCHAR(32)) - `AI_OCR` or `MANUAL_OFFICER`
- `verified_by` (UUID, FK -> `users.id`, NULLABLE)
- `verified_at`, `created_at` (TIMESTAMPTZ)

#### `deficiencies`
Actionable notices raised for deficient documents or data.
- `id` (UUID, PK)
- `application_id` (UUID, FK -> `applications.id`, INDEX)
- `document_id` (UUID, FK -> `documents.id`, NULLABLE)
- `reason` (TEXT)
- `applicant_message` (TEXT)
- `status` (VARCHAR(32)) - `OPEN`, `RESOLVED`, `EXPIRED`
- `created_at`, `resolved_at` (TIMESTAMPTZ)

---

### 2.3 Evaluation, Selection & Fellowship Records

#### `officer_assignments`
Assigns verification officers to specific states or schemes.
- `id` (UUID, PK)
- `officer_id` (UUID, FK -> `users.id`, INDEX)
- `state` (VARCHAR(64), NULLABLE)
- `scheme_id` (UUID, FK -> `schemes.id`, NULLABLE)
- `assigned_at` (TIMESTAMPTZ)
- `is_active` (BOOLEAN)

#### `merit_scores`
Persists calculated merit scores and breakdowns.
- `id` (UUID, PK)
- `application_id` (UUID, FK -> `applications.id`, INDEX)
- `total_score` (FLOAT)
- `score_breakdown` (JSONB)
- `calculated_at` (TIMESTAMPTZ)
- `calculated_by` (UUID, FK -> `users.id`, NULLABLE)

#### `selection_results`
Final decisions recorded by the Selection Committee.
- `id` (UUID, PK)
- `application_id` (UUID, FK -> `applications.id`, INDEX)
- `result` (VARCHAR(32)) - `SELECTED`, `WAITLISTED`, `REJECTED`
- `rank` (INTEGER, NULLABLE)
- `reason` (TEXT, NULLABLE)
- `finalized_by` (UUID, FK -> `users.id`, NULLABLE)
- `finalized_at` (TIMESTAMPTZ)

#### `fellowship_records`
Tracks ongoing multi-year tenure for awarded fellows.
- `id` (UUID, PK)
- `application_id` (UUID, FK -> `applications.id`, INDEX)
- `status` (VARCHAR(32)) - `ACTIVE`, `ON_HOLD`, `COMPLETED`, `TERMINATED`
- `current_year` (INTEGER, DEFAULT 1)
- `disbursement_status` (VARCHAR(32))
- `created_at`, `updated_at` (TIMESTAMPTZ)

#### `renewal_submissions`
Periodic renewal claims by active fellows.
- `id` (UUID, PK)
- `fellowship_id` (UUID, FK -> `fellowship_records.id`, INDEX)
- `academic_year` (INTEGER)
- `status` (VARCHAR(32))
- `documents` (JSONB)
- `submitted_at`, `reviewed_at` (TIMESTAMPTZ)

#### `progress_reports`
Academic supervisor quarterly/annual reports.
- `id` (UUID, PK)
- `fellowship_id` (UUID, FK -> `fellowship_records.id`, INDEX)
- `academic_year` (INTEGER)
- `file_path` (VARCHAR(512))
- `description` (TEXT)
- `status` (VARCHAR(32))
- `submitted_at`, `reviewed_at` (TIMESTAMPTZ)

---

### 2.4 Traceability & Communications

#### `audit_logs`
High-fidelity, entity-targeted audit trail.
- `id` (UUID, PK)
- `application_id` (UUID, FK -> `applications.id`, NULLABLE, INDEX)
- `entity_type` (VARCHAR(32), INDEX) - `APPLICATION`, `DOCUMENT`, `USER`, `SCHEME`, `FELLOWSHIP`, `SYSTEM`
- `entity_id` (VARCHAR(64), INDEX) - UUID or string reference
- `actor_id` (UUID, FK -> `users.id`, NULLABLE, INDEX)
- `action` (VARCHAR(64), INDEX) - e.g. `APPLICATION_SUBMITTED`, `DOCUMENT_VERIFIED`
- `previous_status` (VARCHAR(32), NULLABLE)
- `new_status` (VARCHAR(32), NULLABLE)
- `details` (JSONB) - Contextual diffs and metadata
- `created_at` (TIMESTAMPTZ, INDEX)

#### `notifications`
In-app and external dispatch logs.
- `id` (UUID, PK)
- `user_id` (UUID, FK -> `users.id`, INDEX)
- `application_id` (UUID, FK -> `applications.id`, NULLABLE)
- `channel` (VARCHAR(16)) - `IN_APP`, `EMAIL`, `SMS`
- `title` (VARCHAR(255))
- `message` (TEXT)
- `status` (VARCHAR(32))
- `created_at` (TIMESTAMPTZ)
