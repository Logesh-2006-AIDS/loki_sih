import uuid
from fastapi.testclient import TestClient
from app.services.audit_service import AuditService


def test_audit_service_log_and_retrieve(db):
    service = AuditService(db)
    test_entity_id = str(uuid.uuid4())

    # Log an event with entity targeting
    log_entry = service.log(
        entity_type="SCHEME",
        entity_id=test_entity_id,
        action="TEST_ACTION_AUDIT",
        previous_status=None,
        new_status="ACTIVE",
        details={"test_key": "test_value"},
    )

    assert log_entry.id is not None
    assert log_entry.entity_type == "SCHEME"
    assert log_entry.entity_id == test_entity_id

    # Retrieve logs by entity
    logs = service.get_logs_for_entity(entity_type="SCHEME", entity_id=test_entity_id)
    assert len(logs) >= 1
    assert logs[0].action == "TEST_ACTION_AUDIT"
    assert logs[0].entity_id == test_entity_id


def test_audit_endpoint_staff_only(client: TestClient, officer_token: str, applicant_token: str):
    # Applicant cannot access entity audit logs
    res_applicant = client.get(
        "/api/v1/audit/entity/USER/any-id",
        headers={"Authorization": f"Bearer {applicant_token}"},
    )
    assert res_applicant.status_code == 403

    # Officer can access entity audit logs
    res_officer = client.get(
        "/api/v1/audit/entity/USER/any-id",
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert res_officer.status_code == 200
    assert isinstance(res_officer.json(), list)
