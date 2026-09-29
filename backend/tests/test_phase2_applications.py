import io
import uuid
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.scheme import Scheme
from app.models.scheme_version import SchemeVersion
from app.models.application import Application
from app.models.document import Document
from app.models.audit_log import AuditLog
from app.core.enums import UserRole, ApplicationStatus, DocumentStatus
from app.core.security import get_password_hash


def _get_token(client: TestClient, email: str, password: str = "Demo@12345") -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


@pytest.fixture
def applicant_token(client: TestClient, db: Session) -> str:
    email = "applicant@demo.gov.in"
    if not db.query(User).filter(User.email == email).first():
        user = User(
            full_name="Demo Applicant",
            email=email,
            password_hash=get_password_hash("Demo@12345"),
            role=UserRole.APPLICANT,
            is_active=True,
        )
        db.add(user)
        db.commit()
    return _get_token(client, email)


@pytest.fixture
def applicant_b_token(client: TestClient, db: Session) -> str:
    email = "applicant_b@demo.gov.in"
    if not db.query(User).filter(User.email == email).first():
        user = User(
            full_name="Applicant B",
            email=email,
            password_hash=get_password_hash("Demo@12345"),
            role=UserRole.APPLICANT,
            is_active=True,
        )
        db.add(user)
        db.commit()
    return _get_token(client, email)


@pytest.fixture
def nfst_scheme(db: Session) -> Scheme:
    scheme = db.query(Scheme).filter(Scheme.scheme_code == "NFST").first()
    assert scheme is not None, "NFST scheme must be seeded"
    return scheme


# Helper to generate valid dummy files with genuine magic bytes
def create_fake_pdf(content: str = "Test PDF Document") -> io.BytesIO:
    bio = io.BytesIO()
    bio.write(b"%PDF-1.4\n")
    bio.write(content.encode("utf-8"))
    bio.write(b"\n%%EOF")
    bio.seek(0)
    return bio


def create_fake_jpg() -> io.BytesIO:
    bio = io.BytesIO()
    bio.write(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00")
    bio.write(b"IMAGE DATA CONTENT")
    bio.seek(0)
    return bio


# ---------------------------------------------------------------------------
# Test 1 & 2: Applicant can create and retrieve own draft
# ---------------------------------------------------------------------------

def test_applicant_can_create_and_retrieve_own_draft(
    client: TestClient, db: Session, applicant_token: str, nfst_scheme: Scheme
):
    headers = {"Authorization": f"Bearer {applicant_token}"}
    create_res = client.post(
        "/api/v1/applications/",
        headers=headers,
        json={"scheme_id": str(nfst_scheme.id), "form_data": {"full_name": "Ramesh Meena"}},
    )
    assert create_res.status_code == 201
    data = create_res.json()
    assert data["status"] == "DRAFT"
    assert data["reference_id"].startswith("MTA-NFST-")
    assert data["scheme_version_id"] is not None

    app_id = data["id"]
    get_res = client.get(f"/api/v1/applications/{app_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == app_id


# ---------------------------------------------------------------------------
# Test 3: Applicant cannot retrieve another applicant's application
# ---------------------------------------------------------------------------

def test_applicant_cannot_retrieve_another_applicant_application(
    client: TestClient, db: Session, applicant_token: str, applicant_b_token: str, nfst_scheme: Scheme
):
    headers_a = {"Authorization": f"Bearer {applicant_token}"}
    headers_b = {"Authorization": f"Bearer {applicant_b_token}"}

    create_res = client.post(
        "/api/v1/applications/",
        headers=headers_b,
        json={"scheme_id": str(nfst_scheme.id), "form_data": {"full_name": "Bob"}},
    )
    assert create_res.status_code == 201
    app_b_id = create_res.json()["id"]

    # Applicant A tries to retrieve Applicant B's application
    res = client.get(f"/api/v1/applications/{app_b_id}", headers=headers_a)
    assert res.status_code == 403
    assert "belonging to another user" in res.json()["error"].lower()


# ---------------------------------------------------------------------------
# Test 4: Applicant can update own draft
# ---------------------------------------------------------------------------

def test_applicant_can_update_own_draft(
    client: TestClient, applicant_token: str, nfst_scheme: Scheme
):
    headers = {"Authorization": f"Bearer {applicant_token}"}
    create_res = client.post(
        "/api/v1/applications/",
        headers=headers,
        json={"scheme_id": str(nfst_scheme.id), "form_data": {"full_name": "Initial"}},
    )
    app_id = create_res.json()["id"]

    update_res = client.put(
        f"/api/v1/applications/{app_id}",
        headers=headers,
        json={"form_data": {"full_name": "Updated Name", "phone": "9876543210"}},
    )
    assert update_res.status_code == 200
    assert update_res.json()["form_data"]["full_name"] == "Updated Name"


# ---------------------------------------------------------------------------
# Test 5: Submitted application cannot be edited by applicant
# ---------------------------------------------------------------------------

def test_submitted_application_cannot_be_edited_by_applicant(
    client: TestClient, db: Session, applicant_token: str, nfst_scheme: Scheme
):
    headers = {"Authorization": f"Bearer {applicant_token}"}
    # Create an application directly in submitted status for this test
    user = db.query(User).filter(User.email == "applicant@demo.gov.in").first()
    app = Application(
        reference_id=f"MTA-TEST-{uuid.uuid4().hex[:6].upper()}",
        applicant_id=user.id,
        scheme_id=nfst_scheme.id,
        status=ApplicationStatus.UNDER_AI_VERIFICATION,
        form_data={"full_name": "Immutable User"},
    )
    db.add(app)
    db.commit()
    db.refresh(app)

    # Attempt to edit via PUT
    edit_res = client.put(
        f"/api/v1/applications/{app.id}",
        headers=headers,
        json={"form_data": {"full_name": "Hacked"}},
    )
    assert edit_res.status_code == 403
    assert "cannot modify submitted application" in edit_res.json()["error"].lower()


# ---------------------------------------------------------------------------
# Test 6 & 7: Dynamic form schema and required documents loaded from scheme version
# ---------------------------------------------------------------------------

def test_form_schema_and_required_documents_loaded(
    client: TestClient, applicant_token: str, nfst_scheme: Scheme
):
    headers = {"Authorization": f"Bearer {applicant_token}"}
    res = client.get(f"/api/v1/schemes/{nfst_scheme.id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    active_v = data.get("active_version")
    assert active_v is not None
    form_schema = active_v["form_schema"]
    assert "sections" in form_schema
    assert len(form_schema["sections"]) >= 4

    req_docs = active_v["required_documents"]
    assert "documents" in req_docs
    doc_codes = [d.get("code") or d.get("type") for d in req_docs["documents"]]
    assert "CASTE_CERTIFICATE" in doc_codes
    assert "INCOME_CERTIFICATE" in doc_codes


# ---------------------------------------------------------------------------
# Test 8: Missing required fields prevent submission
# ---------------------------------------------------------------------------

def test_missing_required_fields_prevent_submission(
    client: TestClient, applicant_token: str, nfst_scheme: Scheme
):
    headers = {"Authorization": f"Bearer {applicant_token}"}
    create_res = client.post(
        "/api/v1/applications/",
        headers=headers,
        json={"scheme_id": str(nfst_scheme.id), "form_data": {"full_name": "Incomplete Candidate"}},
    )
    app_id = create_res.json()["id"]

    submit_res = client.post(f"/api/v1/applications/{app_id}/submit", headers=headers)
    assert submit_res.status_code == 400
    assert "missing required application fields" in submit_res.json()["error"].lower()


# ---------------------------------------------------------------------------
# Test 9: Missing required documents prevent submission
# ---------------------------------------------------------------------------

def test_missing_required_documents_prevent_submission(
    client: TestClient, applicant_token: str, nfst_scheme: Scheme
):
    headers = {"Authorization": f"Bearer {applicant_token}"}
    # Provide all required fields for NFST
    complete_fields = {
        "full_name": "Ramesh Chandra Meena",
        "dob": "1998-05-12",
        "gender": "Male",
        "email": "ramesh@example.com",
        "phone": "9876543210",
        "caste_tribe_name": "Meena",
        "pg_degree": "M.Sc.",
        "university_name": "Delhi University",
        "year_of_passing": 2023,
        "percentage_marks": 65.5,
        "course_type": "Ph.D.",
        "department": "Biotechnology",
        "admission_date": "2024-01-15",
        "research_topic": "Genomic study of tribal biodiversity in Central India",
        "annual_family_income": 450000,
        "is_employed": "No",
        "st_community_declaration": True,
        "authenticity_declaration": True,
    }
    create_res = client.post(
        "/api/v1/applications/",
        headers=headers,
        json={"scheme_id": str(nfst_scheme.id), "form_data": complete_fields},
    )
    app_id = create_res.json()["id"]

    # Submit without uploading required documents
    submit_res = client.post(f"/api/v1/applications/{app_id}/submit", headers=headers)
    assert submit_res.status_code == 400
    assert "missing mandatory documents" in submit_res.json()["error"].lower()


# ---------------------------------------------------------------------------
# Test 10, 11, 12, 19: Valid application can be submitted to UNDER_AI_VERIFICATION
# ---------------------------------------------------------------------------

def test_valid_application_can_be_submitted(
    client: TestClient, db: Session, applicant_token: str, nfst_scheme: Scheme
):
    headers = {"Authorization": f"Bearer {applicant_token}"}
    complete_fields = {
        "full_name": "Ramesh Chandra Meena",
        "dob": "1998-05-12",
        "gender": "Male",
        "email": "ramesh@example.com",
        "phone": "9876543210",
        "caste_tribe_name": "Meena",
        "pg_degree": "M.Sc.",
        "university_name": "Delhi University",
        "year_of_passing": 2023,
        "percentage_marks": 65.5,
        "course_type": "Ph.D.",
        "department": "Biotechnology",
        "admission_date": "2024-01-15",
        "research_topic": "Genomic study of tribal biodiversity in Central India",
        "annual_family_income": 450000,
        "is_employed": "No",
        "st_community_declaration": True,
        "authenticity_declaration": True,
    }
    create_res = client.post(
        "/api/v1/applications/",
        headers=headers,
        json={"scheme_id": str(nfst_scheme.id), "form_data": complete_fields},
    )
    app_id = create_res.json()["id"]

    # Upload all 4 required NFST documents
    docs_to_upload = ["CASTE_CERTIFICATE", "INCOME_CERTIFICATE", "PG_MARKSHEET", "ADMISSION_LETTER"]
    for code in docs_to_upload:
        file_data = create_fake_pdf(f"Document content for {code}")
        up_res = client.post(
            f"/api/v1/applications/{app_id}/documents",
            headers=headers,
            data={"document_type": code},
            files={"file": (f"{code.lower()}.pdf", file_data, "application/pdf")},
        )
        assert up_res.status_code == 201

    # Now submit the application
    submit_res = client.post(f"/api/v1/applications/{app_id}/submit", headers=headers)
    assert submit_res.status_code == 200
    res_data = submit_res.json()

    # Verify status transition to UNDER_AI_VERIFICATION
    assert res_data["status"] == "UNDER_AI_VERIFICATION"
    assert res_data["submitted_at"] is not None
    assert res_data["scheme_version_id"] is not None
    assert res_data["frozen_rules_snapshot"] is not None


# ---------------------------------------------------------------------------
# Test 13: Unauthorized document access is rejected
# ---------------------------------------------------------------------------

def test_unauthorized_document_access_rejected(
    client: TestClient, applicant_token: str, applicant_b_token: str, nfst_scheme: Scheme
):
    headers_a = {"Authorization": f"Bearer {applicant_token}"}
    headers_b = {"Authorization": f"Bearer {applicant_b_token}"}

    create_res = client.post(
        "/api/v1/applications/",
        headers=headers_a,
        json={"scheme_id": str(nfst_scheme.id), "form_data": {}},
    )
    app_a_id = create_res.json()["id"]

    # Applicant A uploads document
    file_data = create_fake_pdf("Private document")
    up_res = client.post(
        f"/api/v1/applications/{app_a_id}/documents",
        headers=headers_a,
        data={"document_type": "CASTE_CERTIFICATE"},
        files={"file": ("caste.pdf", file_data, "application/pdf")},
    )
    doc_id = up_res.json()["id"]

    # Applicant B tries to access document metadata
    meta_res = client.get(f"/api/v1/documents/{doc_id}", headers=headers_b)
    assert meta_res.status_code == 403

    # Applicant B tries to download document
    dl_res = client.get(f"/api/v1/documents/{doc_id}/download", headers=headers_b)
    assert dl_res.status_code == 403

    # Applicant B tries to delete document
    del_res = client.delete(f"/api/v1/documents/{doc_id}", headers=headers_b)
    assert del_res.status_code == 403


# ---------------------------------------------------------------------------
# Test 14: Invalid file type rejected (magic bytes and extension check)
# ---------------------------------------------------------------------------

def test_invalid_file_type_rejected(
    client: TestClient, applicant_token: str, nfst_scheme: Scheme
):
    headers = {"Authorization": f"Bearer {applicant_token}"}
    create_res = client.post(
        "/api/v1/applications/",
        headers=headers,
        json={"scheme_id": str(nfst_scheme.id), "form_data": {}},
    )
    app_id = create_res.json()["id"]

    # Case A: Disallowed extension (.exe)
    exe_file = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00BinaryExe")
    res_a = client.post(
        f"/api/v1/applications/{app_id}/documents",
        headers=headers,
        data={"document_type": "CASTE_CERTIFICATE"},
        files={"file": ("malicious.exe", exe_file, "application/octet-stream")},
    )
    assert res_a.status_code == 400
    assert "extension" in res_a.json()["error"].lower()

    # Case B: Spoofed extension (.pdf extension but contents are executable)
    spoofed_file = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00BinaryExe")
    res_b = client.post(
        f"/api/v1/applications/{app_id}/documents",
        headers=headers,
        data={"document_type": "CASTE_CERTIFICATE"},
        files={"file": ("spoofed.pdf", spoofed_file, "application/pdf")},
    )
    assert res_b.status_code == 400
    assert "signature" in res_b.json()["error"].lower()


# ---------------------------------------------------------------------------
# Test 15: Oversized file rejected
# ---------------------------------------------------------------------------

def test_oversized_file_rejected(
    client: TestClient, applicant_token: str, nfst_scheme: Scheme
):
    headers = {"Authorization": f"Bearer {applicant_token}"}
    create_res = client.post(
        "/api/v1/applications/",
        headers=headers,
        json={"scheme_id": str(nfst_scheme.id), "form_data": {}},
    )
    app_id = create_res.json()["id"]

    # Create file larger than 5MB
    large_file = io.BytesIO()
    large_file.write(b"%PDF-1.4\n")
    large_file.write(b"0" * (6 * 1024 * 1024))  # 6MB
    large_file.seek(0)

    res = client.post(
        f"/api/v1/applications/{app_id}/documents",
        headers=headers,
        data={"document_type": "CASTE_CERTIFICATE"},
        files={"file": ("huge.pdf", large_file, "application/pdf")},
    )
    assert res.status_code == 400
    assert "exceeds" in res.json()["error"].lower()


# ---------------------------------------------------------------------------
# Test 16: Unsafe filename rejected or sanitized
# ---------------------------------------------------------------------------

def test_unsafe_filename_path_rejected(
    client: TestClient, applicant_token: str, nfst_scheme: Scheme
):
    headers = {"Authorization": f"Bearer {applicant_token}"}
    create_res = client.post(
        "/api/v1/applications/",
        headers=headers,
        json={"scheme_id": str(nfst_scheme.id), "form_data": {}},
    )
    app_id = create_res.json()["id"]

    # Path traversal in filename
    fake_file = create_fake_pdf("Testing traversal")
    res = client.post(
        f"/api/v1/applications/{app_id}/documents",
        headers=headers,
        data={"document_type": "CASTE_CERTIFICATE"},
        files={"file": ("../../../../etc/passwd.pdf", fake_file, "application/pdf")},
    )
    # The validator rejects directory traversal
    assert res.status_code == 400
    assert "unsafe filename" in res.json()["error"].lower()


# ---------------------------------------------------------------------------
# Test 17: Applicant cannot modify document verification status
# ---------------------------------------------------------------------------

def test_applicant_cannot_modify_document_verification_status(
    client: TestClient, applicant_token: str, nfst_scheme: Scheme
):
    headers = {"Authorization": f"Bearer {applicant_token}"}
    create_res = client.post(
        "/api/v1/applications/",
        headers=headers,
        json={"scheme_id": str(nfst_scheme.id), "form_data": {}},
    )
    app_id = create_res.json()["id"]

    file_data = create_fake_pdf("Testing doc")
    up_res = client.post(
        f"/api/v1/applications/{app_id}/documents",
        headers=headers,
        data={"document_type": "CASTE_CERTIFICATE"},
        files={"file": ("caste.pdf", file_data, "application/pdf")},
    )
    doc_id = up_res.json()["id"]

    patch_res = client.patch(
        f"/api/v1/documents/{doc_id}/status",
        headers=headers,
        json={"status": "VERIFIED"},
    )
    assert patch_res.status_code == 403


# ---------------------------------------------------------------------------
# Test 18: Audit events are created
# ---------------------------------------------------------------------------

def test_audit_events_created(
    client: TestClient, db: Session, applicant_token: str, nfst_scheme: Scheme
):
    headers = {"Authorization": f"Bearer {applicant_token}"}
    create_res = client.post(
        "/api/v1/applications/",
        headers=headers,
        json={"scheme_id": str(nfst_scheme.id), "form_data": {"test": "audit"}},
    )
    app_id = uuid.UUID(create_res.json()["id"])

    # Verify APPLICATION_DRAFT_CREATED exists in audit_logs
    draft_audit = (
        db.query(AuditLog)
        .filter(AuditLog.application_id == app_id, AuditLog.action == "APPLICATION_DRAFT_CREATED")
        .first()
    )
    assert draft_audit is not None


# ---------------------------------------------------------------------------
# Test 20: Applicant only sees their own applications
# ---------------------------------------------------------------------------

def test_applicant_only_sees_their_own_applications(
    client: TestClient, applicant_token: str, applicant_b_token: str, nfst_scheme: Scheme
):
    headers_a = {"Authorization": f"Bearer {applicant_token}"}
    headers_b = {"Authorization": f"Bearer {applicant_b_token}"}

    # Applicant A creates application
    client.post(
        "/api/v1/applications/",
        headers=headers_a,
        json={"scheme_id": str(nfst_scheme.id), "form_data": {"user": "A"}},
    )

    # Applicant B creates application
    client.post(
        "/api/v1/applications/",
        headers=headers_b,
        json={"scheme_id": str(nfst_scheme.id), "form_data": {"user": "B"}},
    )

    # Applicant A lists applications
    list_a = client.get("/api/v1/applications/", headers=headers_a).json()
    assert all(a["form_data"].get("user") != "B" for a in list_a)


# ---------------------------------------------------------------------------
# Test 21: Storage path normalization protects against root escapes
# ---------------------------------------------------------------------------

def test_storage_service_path_normalization():
    from app.services.storage_service import LocalStorageService
    storage = LocalStorageService()
    
    # Path with leading slashes or redundant storage/ prefix
    p1 = storage.get_file_path("/storage/demo/caste_rahul.pdf")
    p2 = storage.get_file_path("demo/caste_rahul.pdf")
    p3 = storage.get_file_path(r"\storage\demo\caste_rahul.pdf")
    p4 = storage.get_file_path("applications/test-uuid/doc.pdf")
    
    # All must resolve inside storage base_path
    assert str(p1).startswith(str(storage.base_path))
    assert str(p2).startswith(str(storage.base_path))
    assert str(p3).startswith(str(storage.base_path))
    assert str(p4).startswith(str(storage.base_path))
    assert p1 == p2


# ---------------------------------------------------------------------------
# Test 22: Document download returns inline disposition and exact bytes
# ---------------------------------------------------------------------------

def test_document_download_inline_disposition(
    client: TestClient, applicant_token: str, nfst_scheme: Scheme
):
    headers = {"Authorization": f"Bearer {applicant_token}"}
    create_res = client.post(
        "/api/v1/applications/",
        headers=headers,
        json={"scheme_id": str(nfst_scheme.id), "form_data": {"test": "pdf_inline"}},
    )
    app_id = create_res.json()["id"]

    # Minimal valid PDF structure
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<\n>>\nendobj\ntrailer\n<<\n>>\n%%EOF"
    upload_res = client.post(
        f"/api/v1/applications/{app_id}/documents",
        headers=headers,
        data={"document_type": "caste_certificate"},
        files={"file": ("cert.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    dl_res = client.get(f"/api/v1/documents/{doc_id}/download", headers=headers)
    assert dl_res.status_code == 200
    assert dl_res.headers.get("content-type") == "application/pdf"
    assert "inline" in dl_res.headers.get("content-disposition", "")
    assert dl_res.content == pdf_bytes

