import io
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import pypdf

from app.main import app
from app.models.user import User
from app.models.scheme import Scheme
from app.models.application import Application
from app.models.document import Document
from app.models.document_verification import DocumentVerification
from app.models.audit_log import AuditLog
from app.core.enums import UserRole, ApplicationStatus, DocumentStatus
from app.schemas.application import ApplicationCreate
from app.services.ocr_service import LocalOCRService, ExtractedField
from app.services.test_ocr_provider import TestOCRProvider
from app.services.comparison_service import DocumentComparisonService
from app.services.verification_service import DocumentVerificationService
from app.services.application_service import ApplicationService
from app.services.document_service import DocumentService


def _get_token(client: TestClient, email: str, password: str = "Demo@12345") -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def create_sample_pdf_bytes(text_lines: list[str]) -> bytes:
    """Helper to create a valid digital PDF with embedded text stream."""
    writer = pypdf.PdfWriter()
    page = writer.add_blank_page(width=612, height=792)

    from pypdf.generic import DecodedStreamObject, NameObject, DictionaryObject

    stream_content = "BT\n/F1 12 Tf\n72 712 Td\n"
    for line in text_lines:
        safe_line = line.replace("(", "\\(").replace(")", "\\)")
        stream_content += f"({safe_line}) '\n"
    stream_content += "ET\n"

    stream = DecodedStreamObject()
    stream.set_data(stream_content.encode("latin1"))
    page[NameObject("/Contents")] = stream

    font_dict = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({
            NameObject("/F1"): font_dict
        })
    })

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 1. OCR Unit Tests
# ---------------------------------------------------------------------------

def test_ocr_service_digital_pdf(tmp_path: Path):
    """Test high-confidence text extraction from a digitally generated PDF."""
    pdf_bytes = create_sample_pdf_bytes([
        "GOVERNMENT OF INDIA - REVENUE DEPARTMENT",
        "INCOME CERTIFICATE",
        "Certificate No: INC/2026/89412",
        "This is to certify that Shri Ramesh Chandra Meena",
        "Annual Family Income: Rs. 2,50,000",
        "Date of Issue: 15/01/2026",
    ])

    test_file = tmp_path / "income_cert.pdf"
    test_file.write_bytes(pdf_bytes)

    ocr = LocalOCRService()
    doc_id = uuid.uuid4()
    result = ocr.extract_document(
        document_id=doc_id,
        file_path=test_file,
        mime_type="application/pdf",
        document_type="INCOME_CERTIFICATE",
    )

    assert result.document_id == doc_id
    assert not result.is_scanned
    assert result.error is None
    assert "RAMESH CHANDRA MEENA" in result.raw_text.upper()
    assert "annual_family_income" in result.extracted_fields
    assert result.extracted_fields["annual_family_income"].value == "250000"
    assert result.extracted_fields["annual_family_income"].confidence >= 0.70


def test_ocr_service_unreadable_file_handling(tmp_path: Path):
    """Corrupted/non-existent files return clean error, never raise 500."""
    ocr = LocalOCRService()
    non_existent = tmp_path / "does_not_exist.pdf"
    result = ocr.extract_document(
        document_id=uuid.uuid4(),
        file_path=non_existent,
        mime_type="application/pdf",
        document_type="INCOME_CERTIFICATE",
    )
    assert result.error is not None
    assert result.overall_confidence == 0.0


def test_ocr_missing_engine_fallback(tmp_path: Path):
    """Test image extraction when pytesseract/binary is absent degrades gracefully."""
    ocr = LocalOCRService()
    dummy_img = tmp_path / "scan.png"
    dummy_img.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    )

    result = ocr.extract_document(
        document_id=uuid.uuid4(),
        file_path=dummy_img,
        mime_type="image/png",
        document_type="CASTE_CERTIFICATE",
    )
    assert result.is_scanned is True


# ---------------------------------------------------------------------------
# 2. Normalizer Unit Tests
# ---------------------------------------------------------------------------

def test_normalizer_names():
    normalizer = DocumentComparisonService()
    assert normalizer.normalize_name("Shri Ramesh Chandra Meena") == "ramesh chandra meena"
    assert normalizer.normalize_name("Dr. Arun Kumar, Ph.D.") == "arun kumar phd"
    assert normalizer.normalize_name("  smt.  PRIYA   RANI ") == "priya rani"
    assert normalizer.normalize_name("Kumari Sunita S.") == "sunita s"


def test_normalizer_currency():
    normalizer = DocumentComparisonService()
    assert normalizer.normalize_currency("₹ 2,50,000") == 250000.0
    assert normalizer.normalize_currency("Rs. 6.5 Lakhs") == 650000.0
    assert normalizer.normalize_currency("450000/-") == 450000.0
    assert normalizer.normalize_currency("INR 800000.00") == 800000.0
    assert normalizer.normalize_currency("invalid") is None


def test_normalizer_date_and_percentage():
    normalizer = DocumentComparisonService()
    assert normalizer.normalize_date("12/05/2004") == "2004-05-12"
    assert normalizer.normalize_date("2004-05-12") == "2004-05-12"
    assert normalizer.normalize_date("12-05-2004") == "2004-05-12"
    assert normalizer.normalize_percentage("64.5%") == 64.5
    assert normalizer.normalize_percentage("72.0") == 72.0


# ---------------------------------------------------------------------------
# 3. Comparison Engine Unit Tests
# ---------------------------------------------------------------------------

def test_comparison_exact_match():
    service = DocumentComparisonService()
    app_form = {
        "annual_family_income": 250000,
        "full_name": "Ramesh Chandra Meena",
    }
    extracted = {
        "annual_family_income": ExtractedField(value="250000", confidence=0.92),
        "full_name": ExtractedField(value="Shri Ramesh Chandra Meena", confidence=0.88),
    }
    rules = [
        {"document_field": "annual_family_income", "application_field": "annual_family_income", "comparison": "currency", "label": "Annual Income", "required": True},
        {"document_field": "full_name", "application_field": "full_name", "comparison": "name", "label": "Full Name", "required": True},
    ]

    comp_results, flags, is_verified = service.compare_document_fields(app_form, extracted, rules)
    assert is_verified is True
    assert len(flags) == 0
    assert comp_results["annual_family_income"]["status"] == "MATCH"
    assert comp_results["full_name"]["status"] == "MATCH"


def test_comparison_income_mismatch():
    """Key SIH Demonstration: Income mismatch must be detected with HIGH severity."""
    service = DocumentComparisonService()
    app_form = {
        "annual_family_income": 250000,
        "full_name": "Arun Kumar",
    }
    extracted = {
        "annual_family_income": ExtractedField(value="500000", confidence=0.94),
        "full_name": ExtractedField(value="Arun Kumar", confidence=0.92),
    }
    rules = [
        {"document_field": "annual_family_income", "application_field": "annual_family_income", "comparison": "currency", "label": "Annual Income", "required": True},
        {"document_field": "full_name", "application_field": "full_name", "comparison": "name", "label": "Full Name", "required": True},
    ]

    comp_results, flags, is_verified = service.compare_document_fields(app_form, extracted, rules)
    assert is_verified is False
    assert comp_results["annual_family_income"]["status"] == "MISMATCH"
    assert len(flags) == 1
    assert flags[0]["severity"] == "HIGH"
    assert "₹500,000" in flags[0]["reason"] or "500000" in flags[0]["reason"]


def test_comparison_low_confidence_flagged():
    """Low extraction confidence (<0.70) must flag UNCLEAR with MEDIUM severity."""
    service = DocumentComparisonService()
    app_form = {
        "annual_family_income": 250000,
    }
    extracted = {
        "annual_family_income": ExtractedField(value="250000", confidence=0.55),
    }
    rules = [
        {"document_field": "annual_family_income", "application_field": "annual_family_income", "comparison": "currency", "label": "Annual Income", "required": True},
    ]

    comp_results, flags, is_verified = service.compare_document_fields(app_form, extracted, rules)
    assert is_verified is False
    assert comp_results["annual_family_income"]["status"] == "UNCLEAR"
    assert len(flags) == 1
    assert flags[0]["severity"] == "MEDIUM"


# ---------------------------------------------------------------------------
# 4. End-to-End Orchestration & Lifecycle Tests
# ---------------------------------------------------------------------------

@pytest.fixture
def nfst_scheme(db: Session) -> Scheme:
    scheme = db.query(Scheme).filter(Scheme.scheme_code == "NFST").first()
    assert scheme is not None
    return scheme


@pytest.fixture
def applicant_user(db: Session) -> User:
    user = db.query(User).filter(User.email == "applicant@demo.gov.in").first()
    assert user is not None
    return user


@pytest.fixture
def officer_user(db: Session) -> User:
    user = db.query(User).filter(User.email == "officer@demo.gov.in").first()
    assert user is not None
    return user


def test_verification_idempotency(db: Session, nfst_scheme: Scheme, applicant_user: User):
    """Triggering verification on an already PROCESSING document returns state idempotently."""
    app_svc = ApplicationService(db)
    doc_svc = DocumentService(db)

    app_res = app_svc.create_draft(applicant_user.id, ApplicationCreate(scheme_id=nfst_scheme.id, form_data={}))

    pdf_bytes = create_sample_pdf_bytes(["Test Certificate"])
    doc = doc_svc.upload_document(
        application_id=app_res.id,
        document_type="INCOME_CERTIFICATE",
        filename="income.pdf",
        file_obj=io.BytesIO(pdf_bytes),
        actor_id=applicant_user.id,
    )

    db_doc = db.get(Document, doc.id)
    db_doc.status = DocumentStatus.PROCESSING
    v_rec = DocumentVerification(
        document_id=doc.id,
        verification_status="PROCESSING",
        extracted_fields={},
        field_confidences={},
        comparison_results={},
        flags=[],
    )
    db.add(v_rec)
    db.commit()

    verif_svc = DocumentVerificationService(db)
    res = verif_svc.verify_document(doc.id, force_rerun=False)
    assert res.id == v_rec.id


def test_application_verification_transitions_to_manual_review(
    db: Session, nfst_scheme: Scheme, applicant_user: User
):
    """
    When all required documents for the scheme version are uploaded and verified,
    application transitions from UNDER_AI_VERIFICATION -> UNDER_MANUAL_REVIEW.
    """
    app_svc = ApplicationService(db)
    doc_svc = DocumentService(db)

    app_res = app_svc.create_draft(
        applicant_user.id,
        ApplicationCreate(
            scheme_id=nfst_scheme.id,
            form_data={
                "full_name": "Ramesh Chandra Meena",
                "dob": "2000-01-15",
                "gender": "Male",
                "email": "applicant@demo.gov.in",
                "phone": "9876543210",
                "caste_tribe_name": "Meena",
                "community": "ST",
                "pg_degree": "M.Sc.",
                "university_name": "Jawaharlal Nehru University",
                "year_of_passing": 2024,
                "percentage_marks": 65.5,
                "course_type": "Ph.D.",
                "department": "Department of Biotechnology",
                "admission_date": "2024-08-01",
                "research_topic": "Ethnobotanical flora in tribal medicine",
                "annual_family_income": 250000,
                "is_employed": "No",
                "st_community_declaration": True,
                "authenticity_declaration": True,
            },
        ),
    )

    pdf_bytes = create_sample_pdf_bytes(["Sample Official Document"])
    for doc_type in ["CASTE_CERTIFICATE", "INCOME_CERTIFICATE", "PG_MARKSHEET", "ADMISSION_LETTER"]:
        doc_svc.upload_document(
            application_id=app_res.id,
            document_type=doc_type,
            filename=f"{doc_type.lower()}.pdf",
            file_obj=io.BytesIO(pdf_bytes),
            actor_id=applicant_user.id,
        )

    app_sub = app_svc.submit_application(app_res.id, applicant_user.id)
    assert app_sub.status == ApplicationStatus.UNDER_AI_VERIFICATION

    mock_ocr = TestOCRProvider()
    mock_ocr.set_mock_type_fields("INCOME_CERTIFICATE", {
        "annual_family_income": ("250000", 0.95),
        "full_name": ("Ramesh Chandra Meena", 0.90),
    })
    mock_ocr.set_mock_type_fields("CASTE_CERTIFICATE", {
        "community": ("ST", 0.95),
        "full_name": ("Ramesh Chandra Meena", 0.90),
    })
    mock_ocr.set_mock_type_fields("PG_MARKSHEET", {
        "percentage_marks": ("65.5", 0.95),
        "full_name": ("Ramesh Chandra Meena", 0.90),
    })
    mock_ocr.set_mock_type_fields("ADMISSION_LETTER", {
        "university_name": ("Jawaharlal Nehru University", 0.90),
        "full_name": ("Ramesh Chandra Meena", 0.90),
    })

    verif_svc = DocumentVerificationService(db, ocr_service=mock_ocr)
    result = verif_svc.verify_application_documents(app_res.id)

    assert result["status"] == ApplicationStatus.UNDER_MANUAL_REVIEW.value
    reloaded_app = db.get(Application, app_res.id)
    assert reloaded_app.status == ApplicationStatus.UNDER_MANUAL_REVIEW


def test_ai_never_rejects_application(
    db: Session, nfst_scheme: Scheme, applicant_user: User
):
    """
    AI MUST NEVER REJECT.
    Even with severe income mismatch, application transitions to UNDER_MANUAL_REVIEW
    with evidence preserved for the human officer.
    """
    app_svc = ApplicationService(db)
    doc_svc = DocumentService(db)

    app_res = app_svc.create_draft(
        applicant_user.id,
        ApplicationCreate(
            scheme_id=nfst_scheme.id,
            form_data={
                "full_name": "Arun Kumar",
                "dob": "2000-01-15",
                "gender": "Male",
                "email": "applicant@demo.gov.in",
                "phone": "9876543210",
                "caste_tribe_name": "Meena",
                "community": "ST",
                "pg_degree": "M.Sc.",
                "university_name": "Jawaharlal Nehru University",
                "year_of_passing": 2024,
                "percentage_marks": 65.5,
                "course_type": "Ph.D.",
                "department": "Biotech",
                "admission_date": "2024-08-01",
                "research_topic": "Research topic",
                "annual_family_income": 250000,
                "is_employed": "No",
                "st_community_declaration": True,
                "authenticity_declaration": True,
            },
        ),
    )

    pdf_bytes = create_sample_pdf_bytes(["Sample Official Document"])
    for doc_type in ["CASTE_CERTIFICATE", "INCOME_CERTIFICATE", "PG_MARKSHEET", "ADMISSION_LETTER"]:
        doc_svc.upload_document(
            application_id=app_res.id,
            document_type=doc_type,
            filename=f"{doc_type.lower()}.pdf",
            file_obj=io.BytesIO(pdf_bytes),
            actor_id=applicant_user.id,
        )

    app_svc.submit_application(app_res.id, applicant_user.id)

    mock_ocr = TestOCRProvider()
    mock_ocr.set_mock_type_fields("INCOME_CERTIFICATE", {
        "annual_family_income": ("500000", 0.95),  # Severe mismatch
        "full_name": ("Arun Kumar", 0.90),
    })
    mock_ocr.set_mock_type_fields("CASTE_CERTIFICATE", {
        "community": ("ST", 0.95),
        "full_name": ("Arun Kumar", 0.90),
    })
    mock_ocr.set_mock_type_fields("PG_MARKSHEET", {
        "percentage_marks": ("65.5", 0.95),
        "full_name": ("Arun Kumar", 0.90),
    })
    mock_ocr.set_mock_type_fields("ADMISSION_LETTER", {
        "university_name": ("Jawaharlal Nehru University", 0.90),
        "full_name": ("Arun Kumar", 0.90),
    })

    verif_svc = DocumentVerificationService(db, ocr_service=mock_ocr)
    result = verif_svc.verify_application_documents(app_res.id)

    income_doc = next(d for d in result["verifications"] if d.document.document_type == "INCOME_CERTIFICATE")
    assert income_doc.verification_status == "FLAGGED"
    assert len(income_doc.flags) > 0
    assert income_doc.flags[0]["severity"] == "HIGH"

    assert result["status"] == ApplicationStatus.UNDER_MANUAL_REVIEW.value
    reloaded_app = db.get(Application, app_res.id)
    assert reloaded_app.status == ApplicationStatus.UNDER_MANUAL_REVIEW


# ---------------------------------------------------------------------------
# 5. Security & RBAC Tests
# ---------------------------------------------------------------------------

def test_applicant_cannot_trigger_verification(
    client: TestClient, db: Session, nfst_scheme: Scheme, applicant_user: User
):
    """Applicants are forbidden (HTTP 403) from triggering verification."""
    token = _get_token(client, "applicant@demo.gov.in", "Demo@12345")
    headers = {"Authorization": f"Bearer {token}"}

    app_svc = ApplicationService(db)
    app_rec = app_svc.create_draft(applicant_user.id, ApplicationCreate(scheme_id=nfst_scheme.id, form_data={}))

    res = client.post(f"/api/v1/applications/{app_rec.id}/verify", headers=headers)
    assert res.status_code == 403


def test_applicant_cannot_view_verification_evidence(
    client: TestClient, db: Session, nfst_scheme: Scheme, applicant_user: User
):
    """Applicants are forbidden (HTTP 403) from viewing internal verification evidence."""
    token = _get_token(client, "applicant@demo.gov.in", "Demo@12345")
    headers = {"Authorization": f"Bearer {token}"}

    app_svc = ApplicationService(db)
    app_rec = app_svc.create_draft(applicant_user.id, ApplicationCreate(scheme_id=nfst_scheme.id, form_data={}))

    res = client.get(f"/api/v1/applications/{app_rec.id}/verifications", headers=headers)
    assert res.status_code == 403


def test_applicant_cannot_trigger_document_verify(
    client: TestClient, db: Session, nfst_scheme: Scheme, applicant_user: User
):
    """Applicants are forbidden (HTTP 403) from triggering single-document verification."""
    token = _get_token(client, "applicant@demo.gov.in", "Demo@12345")
    headers = {"Authorization": f"Bearer {token}"}

    app_svc = ApplicationService(db)
    doc_svc = DocumentService(db)
    app_rec = app_svc.create_draft(applicant_user.id, ApplicationCreate(scheme_id=nfst_scheme.id, form_data={}))
    pdf_bytes = create_sample_pdf_bytes(["Test document"])
    doc = doc_svc.upload_document(
        application_id=app_rec.id,
        document_type="INCOME_CERTIFICATE",
        filename="income.pdf",
        file_obj=io.BytesIO(pdf_bytes),
        actor_id=applicant_user.id,
    )

    res = client.post(f"/api/v1/documents/{doc.id}/verify", headers=headers)
    assert res.status_code == 403


def test_applicant_cannot_get_document_verification(
    client: TestClient, db: Session, nfst_scheme: Scheme, applicant_user: User
):
    """Applicants are forbidden (HTTP 403) from viewing single-document verification evidence."""
    token = _get_token(client, "applicant@demo.gov.in", "Demo@12345")
    headers = {"Authorization": f"Bearer {token}"}

    app_svc = ApplicationService(db)
    doc_svc = DocumentService(db)
    app_rec = app_svc.create_draft(applicant_user.id, ApplicationCreate(scheme_id=nfst_scheme.id, form_data={}))
    pdf_bytes = create_sample_pdf_bytes(["Test document"])
    doc = doc_svc.upload_document(
        application_id=app_rec.id,
        document_type="INCOME_CERTIFICATE",
        filename="income.pdf",
        file_obj=io.BytesIO(pdf_bytes),
        actor_id=applicant_user.id,
    )

    res = client.get(f"/api/v1/documents/{doc.id}/verification", headers=headers)
    assert res.status_code == 403


def test_authorized_officer_can_view_verification_summary(
    client: TestClient, db: Session, nfst_scheme: Scheme, applicant_user: User, officer_user: User
):
    """Officers within authorized scope can view verification summary."""
    officer_token = _get_token(client, "officer@demo.gov.in", "Demo@12345")
    officer_headers = {"Authorization": f"Bearer {officer_token}"}

    app_svc = ApplicationService(db)
    doc_svc = DocumentService(db)

    app_rec = app_svc.create_draft(applicant_user.id, ApplicationCreate(scheme_id=nfst_scheme.id, form_data={}))
    pdf_bytes = create_sample_pdf_bytes(["Test document"])
    doc = doc_svc.upload_document(
        application_id=app_rec.id,
        document_type="INCOME_CERTIFICATE",
        filename="income.pdf",
        file_obj=io.BytesIO(pdf_bytes),
        actor_id=applicant_user.id,
    )

    verif_svc = DocumentVerificationService(db)
    verif_svc.verify_document(doc.id)

    res = client.get(f"/api/v1/applications/{app_rec.id}/verifications", headers=officer_headers)
    assert res.status_code == 200
    data = res.json()
    assert "verified_count" in data
    assert "flagged_count" in data
    assert len(data["document_verifications"]) >= 1


def test_audit_events_emitted_during_verification(
    db: Session, nfst_scheme: Scheme, applicant_user: User
):
    """Verify granular audit logs are created for OCR extraction and comparison events."""
    app_svc = ApplicationService(db)
    doc_svc = DocumentService(db)

    app_rec = app_svc.create_draft(applicant_user.id, ApplicationCreate(scheme_id=nfst_scheme.id, form_data={}))
    pdf_bytes = create_sample_pdf_bytes(["Income: Rs. 2,50,000", "Name: Ramesh Chandra Meena"])
    doc = doc_svc.upload_document(
        application_id=app_rec.id,
        document_type="INCOME_CERTIFICATE",
        filename="income.pdf",
        file_obj=io.BytesIO(pdf_bytes),
        actor_id=applicant_user.id,
    )

    mock_ocr = TestOCRProvider()
    mock_ocr.set_mock_type_fields("INCOME_CERTIFICATE", {
        "annual_family_income": ("250000", 0.95),
        "full_name": ("Ramesh Chandra Meena", 0.90),
    })
    verif_svc = DocumentVerificationService(db, ocr_service=mock_ocr)
    verif_svc.verify_document(doc.id)

    actions = [
        a.action
        for a in db.query(AuditLog)
        .filter(AuditLog.application_id == app_rec.id)
        .all()
    ]
    assert "DOCUMENT_OCR_STARTED" in actions
    assert "DOCUMENT_OCR_COMPLETED" in actions
    assert "DOCUMENT_FIELDS_EXTRACTED" in actions
    assert "DOCUMENT_VERIFICATION_STARTED" in actions
    assert "DOCUMENT_VERIFICATION_COMPLETED" in actions
