import io
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.scheme import Scheme
from app.models.officer_assignment import OfficerAssignment
from app.core.enums import UserRole, ApplicationStatus
from app.core.security import get_password_hash


def _get_token_for(client: TestClient, email: str, password: str = "Demo@12345") -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def test_applicant_a_cannot_read_applicant_b_application(client: TestClient, db: Session):
    # Ensure two distinct applicants
    email_a = "applicant_a@demo.gov.in"
    email_b = "applicant_b@demo.gov.in"
    for email in [email_a, email_b]:
        if not db.query(User).filter(User.email == email).first():
            user = User(
                full_name=f"User {email}",
                email=email,
                password_hash=get_password_hash("Demo@12345"),
                role=UserRole.APPLICANT,
                is_active=True,
            )
            db.add(user)
    db.commit()

    token_a = _get_token_for(client, email_a)
    token_b = _get_token_for(client, email_b)

    scheme = db.query(Scheme).filter(Scheme.is_active == True).first()
    assert scheme is not None, "At least one active scheme is required"

    # Applicant B creates application
    res_create = client.post(
        "/api/v1/applications/",
        json={"scheme_id": str(scheme.id), "form_data": {"test": "data_b"}},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_create.status_code == 201
    app_b_id = res_create.json()["id"]

    # Applicant A attempts to read Applicant B's application
    res_read = client.get(
        f"/api/v1/applications/{app_b_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_read.status_code == 403
    assert "cannot access application belonging to another user" in res_read.json()["error"].lower()


def test_applicant_cannot_modify_another_applicant_application(client: TestClient, db: Session):
    email_a = "applicant_a@demo.gov.in"
    email_b = "applicant_b@demo.gov.in"
    token_a = _get_token_for(client, email_a)
    token_b = _get_token_for(client, email_b)

    scheme = db.query(Scheme).filter(Scheme.is_active == True).first()

    # Applicant B creates draft application
    res_create = client.post(
        "/api/v1/applications/",
        json={"scheme_id": str(scheme.id), "form_data": {"personal": {"name": "Bob"}}},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_create.status_code == 201
    app_b_id = res_create.json()["id"]

    # Applicant A tries to modify Applicant B's application draft via PUT
    res_modify = client.put(
        f"/api/v1/applications/{app_b_id}",
        json={"form_data": {"personal": {"name": "Malicious Alice"}}},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_modify.status_code == 403
    assert "cannot modify application belonging to another user" in res_modify.json()["error"].lower()

    # Applicant A tries to submit Applicant B's application
    res_submit = client.post(
        f"/api/v1/applications/{app_b_id}/submit",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_submit.status_code == 403
    assert "cannot submit application belonging to another user" in res_submit.json()["error"].lower()


def test_applicant_cannot_change_protected_workflow_status_directly(client: TestClient, db: Session):
    email_a = "applicant_a@demo.gov.in"
    token_a = _get_token_for(client, email_a)
    scheme = db.query(Scheme).filter(Scheme.is_active == True).first()

    # Applicant A creates own draft application
    res_create = client.post(
        "/api/v1/applications/",
        json={"scheme_id": str(scheme.id), "form_data": {"test": "data_a"}},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_create.status_code == 201
    app_a_id = res_create.json()["id"]

    # Attempt 1: Applicant calls status patch endpoint directly (Staff only)
    res_patch = client.patch(
        f"/api/v1/applications/{app_a_id}/status",
        json={"status": "VERIFIED"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_patch.status_code == 403

    # Attempt 2: Applicant attempts to inject status transition in draft PUT update
    res_put = client.put(
        f"/api/v1/applications/{app_a_id}",
        json={"status": "SELECTED"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_put.status_code == 403
    assert "cannot directly modify application workflow status" in res_put.json()["error"].lower()


def test_officer_cannot_access_application_outside_assigned_scope(client: TestClient, db: Session):
    # Retrieve two distinct schemes (e.g. NFST and NOS)
    schemes = db.query(Scheme).filter(Scheme.is_active == True).all()
    assert len(schemes) >= 2, "Requires at least 2 schemes to test scoped officer jurisdiction"
    scheme_nfst = schemes[0]
    scheme_nos = schemes[1]

    # Create an officer specifically assigned ONLY to scheme_nfst
    scoped_officer_email = "scoped_officer@demo.gov.in"
    scoped_officer = db.query(User).filter(User.email == scoped_officer_email).first()
    if not scoped_officer:
        scoped_officer = User(
            full_name="Scoped Officer NFST Only",
            email=scoped_officer_email,
            password_hash=get_password_hash("Demo@12345"),
            role=UserRole.OFFICER,
            is_active=True,
        )
        db.add(scoped_officer)
        db.commit()

    # Assign officer to scheme_nfst only
    assignment = (
        db.query(OfficerAssignment)
        .filter(OfficerAssignment.officer_id == scoped_officer.id)
        .first()
    )
    if not assignment:
        assignment = OfficerAssignment(
            officer_id=scoped_officer.id,
            scheme_id=scheme_nfst.id,
            is_active=True,
        )
        db.add(assignment)
        db.commit()

    token_scoped_officer = _get_token_for(client, scoped_officer_email)
    token_applicant = _get_token_for(client, "applicant@demo.gov.in")

    # Create application for scheme_nos (OUTSIDE officer's scope)
    res_create = client.post(
        "/api/v1/applications/",
        json={"scheme_id": str(scheme_nos.id), "form_data": {"course": "Overseas PhD"}},
        headers={"Authorization": f"Bearer {token_applicant}"},
    )
    assert res_create.status_code == 201
    app_out_of_scope_id = res_create.json()["id"]

    # Scoped officer tries to access application outside their scheme
    res_get = client.get(
        f"/api/v1/applications/{app_out_of_scope_id}",
        headers={"Authorization": f"Bearer {token_scoped_officer}"},
    )
    assert res_get.status_code == 403
    assert "jurisdiction" in res_get.json()["error"].lower()

    # Scoped officer tries to update status of application outside scope
    res_patch = client.patch(
        f"/api/v1/applications/{app_out_of_scope_id}/status",
        json={"status": "UNDER_MANUAL_REVIEW"},
        headers={"Authorization": f"Bearer {token_scoped_officer}"},
    )
    assert res_patch.status_code == 403
    assert "jurisdiction" in res_patch.json()["error"].lower()


def test_unauthorized_document_access_rejected(client: TestClient, db: Session):
    token_a = _get_token_for(client, "applicant_a@demo.gov.in")
    token_b = _get_token_for(client, "applicant_b@demo.gov.in")
    scheme = db.query(Scheme).filter(Scheme.is_active == True).first()

    # Applicant B creates application and uploads a document
    res_app = client.post(
        "/api/v1/applications/",
        json={"scheme_id": str(scheme.id), "form_data": {}},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    app_b_id = res_app.json()["id"]

    fake_file = io.BytesIO(b"%PDF-1.4 Mock Certificate Content")
    res_upload = client.post(
        "/api/v1/documents/upload",
        data={"application_id": app_b_id, "document_type": "CASTE_CERTIFICATE"},
        files={"file": ("st_cert.pdf", fake_file, "application/pdf")},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_upload.status_code == 201
    doc_b_id = res_upload.json()["id"]

    # 1. Applicant A cannot read Applicant B's document metadata directly
    res_doc_get = client.get(
        f"/api/v1/documents/{doc_b_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_doc_get.status_code == 403
    assert "cannot access document belonging to another applicant" in res_doc_get.json()["error"].lower()

    # 2. Applicant A cannot list documents of Applicant B's application
    res_doc_list = client.get(
        f"/api/v1/documents/application/{app_b_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_doc_list.status_code == 403
    assert "cannot access documents belonging to another user" in res_doc_list.json()["error"].lower()

    # 3. Applicant A cannot upload documents to Applicant B's application
    another_file = io.BytesIO(b"%PDF-1.4 Intrusion attempt")
    res_unauth_upload = client.post(
        "/api/v1/documents/upload",
        data={"application_id": app_b_id, "document_type": "INCOME_CERTIFICATE"},
        files={"file": ("income.pdf", another_file, "application/pdf")},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_unauth_upload.status_code == 403
    assert "cannot upload documents for another applicant's application" in res_unauth_upload.json()["error"].lower()

    # 4. Applicant B cannot change document status directly (officer/admin only)
    res_status = client.patch(
        f"/api/v1/documents/{doc_b_id}/status",
        json={"status": "VERIFIED"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_status.status_code == 403
