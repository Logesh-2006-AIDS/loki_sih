# API Specification & Catalog: /api/v1
**Ministry of Tribal Affairs | AI-Enabled Scholarship & Fellowship Management System**

---

## 1. Protocol Standards

- **Base URL**: `http://localhost:8000/api/v1`
- **Interactive Documentation**:
  - Swagger UI: `http://localhost:8000/api/v1/docs`
  - ReDoc: `http://localhost:8000/api/v1/redoc`
  - OpenAPI JSON: `http://localhost:8000/api/v1/openapi.json`
- **Format**: All payloads are sent and received as `application/json` (except document multipart uploads).
- **Authentication**: Bearer Token in standard HTTP Header:
  ```http
  Authorization: Bearer <jwt_access_token>
  ```

---

## 2. Standardized Endpoints Catalog

### 2.1 Health & System Probes
- `GET /api/v1/health` & `GET /api/health`
  - **Auth**: None (Public)
  - **Response (200)**:
    ```json
    {
      "status": "healthy",
      "service": "AI-Enabled Scholarship & Fellowship Management System (Phase 0)",
      "ministry": "Ministry of Tribal Affairs",
      "database": "connected",
      "timestamp": "2026-09-16T16:20:00.000Z"
    }
    ```

---

### 2.2 Authentication (`/auth`)
- `POST /api/v1/auth/register`
  - **Auth**: None (Public)
  - **Body**:
    ```json
    {
      "full_name": "Demo Applicant",
      "email": "applicant@demo.gov.in",
      "phone": "+91 9876543210",
      "password": "Demo@12345",
      "role": "APPLICANT"
    }
    ```
  - **Response (201)**: User profile without password.

- `POST /api/v1/auth/login`
  - **Auth**: None (Public)
  - **Body**: `{"email": "...", "password": "..."}`
  - **Response (200)**:
    ```json
    {
      "access_token": "<jwt>",
      "token_type": "bearer",
      "user": {
        "id": "uuid",
        "full_name": "...",
        "email": "...",
        "role": "APPLICANT",
        "is_active": true
      }
    }
    ```

- `GET /api/v1/auth/me`
  - **Auth**: Bearer Token
  - **Response (200)**: Profile of authenticated user.

---

### 2.3 Schemes (`/schemes`)
- `GET /api/v1/schemes/`
  - **Auth**: None (Public)
  - **Response (200)**: Array of active schemes with `scheme_version`, demo disclaimers, and form schema.
- `GET /api/v1/schemes/{scheme_id}`
  - **Auth**: None (Public)
  - **Response (200)**: Scheme detail.
- `POST /api/v1/schemes/`
  - **Auth**: Admin only
  - **Response (201)**: Newly created scheme.
- `PUT /api/v1/schemes/{scheme_id}`
  - **Auth**: Admin only
  - **Response (200)**: Updated scheme.

---

### 2.4 Applications (`/applications`)
- `GET /api/v1/applications/`
  - **Auth**: Authenticated (Applicants see own; Officers/Committee/Admins see all).
- `POST /api/v1/applications/`
  - **Auth**: Applicant
  - **Body**: `{"scheme_id": "uuid", "form_data": {...}}`
  - **Response (201)**: Application with `DRAFT` status and unique `reference_id`.
- `GET /api/v1/applications/{id}`
  - **Auth**: Owner or Staff.
- `POST /api/v1/applications/{id}/submit`
  - **Auth**: Applicant owner.
  - **Response (200)**: Status transitioned to `SUBMITTED`.
- `PATCH /api/v1/applications/{id}/status`
  - **Auth**: Officer / Committee / Admin.
  - **Body**: `{"status": "UNDER_MANUAL_REVIEW"}`.

---

### 2.5 Documents (`/documents`)
- `POST /api/v1/documents/upload`
  - **Auth**: Applicant owner / Staff.
  - **Type**: `multipart/form-data` (`application_id`, `document_type`, `file`).
  - **Response (201)**: Document record with relative `storage_path` and `PENDING` status.
- `GET /api/v1/documents/application/{application_id}`
  - **Auth**: Owner or Staff.
- `PATCH /api/v1/documents/{document_id}/status`
  - **Auth**: Officer / Admin.

---

### 2.6 Audit Logs (`/audit`)
- `GET /api/v1/audit/entity/{entity_type}/{entity_id}`
  - **Auth**: Officer / Committee / Admin.
  - **Response (200)**: Entity audit history.
- `GET /api/v1/audit/application/{application_id}`
  - **Auth**: Owner or Staff.

---

### 2.7 Users (`/users`)
- `GET /api/v1/users/`
  - **Auth**: Admin only.
- `GET /api/v1/users/{id}`
  - **Auth**: Self or Admin.
