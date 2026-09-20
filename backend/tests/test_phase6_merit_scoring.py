import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.enums import ApplicationStatus, UserRole
from app.core.security import get_password_hash
from app.core.status_transitions import can_transition_application
from app.models.user import User
from app.models.scheme import Scheme
from app.models.scheme_version import SchemeVersion
from app.models.application import Application
from app.models.committee_assignment import CommitteeAssignment
from app.models.committee_evaluation_batch import CommitteeEvaluationBatch
from app.models.committee_review import CommitteeReview
from app.models.merit_score import MeritScore
from app.models.selection_result import SelectionResult


def _create_user(db: Session, email: str, role: UserRole, full_name: str) -> User:
    u = db.query(User).filter(User.email == email).first()
    if not u:
        u = User(
            email=email,
            password_hash=get_password_hash("Demo@12345"),
            full_name=full_name,
            role=role,
            is_active=True,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
    return u


def _get_token(client: TestClient, email: str, password: str = "Demo@12345") -> str:
    res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


@pytest.fixture(autouse=True)
def cleanup_phase6_test_schemes(db: Session):
    yield
    test_schemes = db.query(Scheme).filter(Scheme.scheme_code.like("TEST_SCHEME_%")).all()
    for s in test_schemes:
        db.delete(s)
    db.commit()


def _setup_phase6_test_data(db: Session):
    """Sets up a test scheme with selection rules and 3 verified applications."""
    # 1. Scheme
    scheme_code = f"TEST_SCHEME_{uuid.uuid4().hex[:6].upper()}"
    scheme = Scheme(
        scheme_code=scheme_code,
        name="Phase 6 Test Fellowship",
        description="[DEMO PROTOTYPE] Scheme for testing merit scoring and committee scrutiny",
        is_active=True,
    )
    db.add(scheme)
    db.commit()

    # 2. Scheme Version with selection rules
    scoring_config = {
        "scoring_components": [
            {
                "code": "academic",
                "label": "Academic Merit",
                "weight": 50.0,
                "source_type": "APPLICATION_FORM_FIELD",
                "field_path": "academic.percentage_marks",
                "evaluation_type": "PERCENTAGE_NORMALIZED",
                "max_raw": 100.0,
            },
            {
                "code": "feasibility",
                "label": "Research Feasibility",
                "weight": 50.0,
                "source_type": "COMMITTEE_EVALUATION",
                "max_raw": 25.0,
            },
        ],
        "committee_config": {
            "required_quorum": 2,
            "blind_evaluation": True,
        },
        "quotas": {
            "total_slots": 2,
            "waitlist_slots": 2,
        },
        "tie_breaking_order": ["ACADEMIC_PERCENTAGE", "AGE_SENIORITY"],
    }

    sv = SchemeVersion(
        scheme_id=scheme.id,
        scheme_code=scheme_code,
        scheme_version="1.0",
        name=f"{scheme.name} v1.0",
        form_schema={},
        eligibility_rules={},
        required_documents={},
        scoring_weights=scoring_config,
        is_active=True,
    )
    db.add(sv)
    db.commit()

    # 3. Applicants & Applications in VERIFIED status
    apps = []
    for i in range(1, 4):
        applicant = _create_user(
            db, f"cand{i}_{uuid.uuid4().hex[:6]}@test.gov.in", UserRole.APPLICANT, f"Candidate {i}"
        )
        app = Application(
            reference_id=f"REF-{uuid.uuid4().hex[:8].upper()}",
            applicant_id=applicant.id,
            scheme_id=scheme.id,
            scheme_version_id=sv.id,
            status=ApplicationStatus.VERIFIED,
            form_data={
                "academic": {"percentage_marks": 80.0 + (i * 2)},  # Cand 1: 82%, Cand 2: 84%, Cand 3: 86%
                "personal": {"dob": f"199{i}-01-01", "full_name": f"Candidate {i}"},
            },
            submitted_at=datetime.now(timezone.utc),
        )
        db.add(app)
        apps.append(app)

    db.commit()
    for a in apps:
        db.refresh(a)

    return scheme, sv, apps


def test_state_machine_verified_transition_delta():
    """Verify VERIFIED -> MERIT_RANKED is legal, while VERIFIED -> REJECTED is illegal."""
    # Legal transition
    assert can_transition_application(ApplicationStatus.VERIFIED, ApplicationStatus.MERIT_RANKED) is True

    # Illegal transition (preventing bypass)
    assert can_transition_application(ApplicationStatus.VERIFIED, ApplicationStatus.REJECTED) is False
    assert can_transition_application(ApplicationStatus.VERIFIED, ApplicationStatus.SELECTED) is False


def test_batch_creation_and_immutability(client: TestClient, db: Session, admin_token: str):
    """Test committee evaluation batch creation, scheme-binding, and membership immutability."""
    scheme, sv, apps = _setup_phase6_test_data(db)

    # 1. Create batch
    res = client.post(
        "/api/v1/committee/batches",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": f"Batch-{scheme.scheme_code}",
            "scheme_id": str(scheme.id),
            "scheme_version_id": str(sv.id),
            "application_ids": [str(apps[0].id), str(apps[1].id)],
        },
    )
    assert res.status_code == 201, res.text
    batch_data = res.json()
    batch_id = batch_data["id"]
    assert batch_data["application_count"] == 2
    assert batch_data["status"] == "OPEN_FOR_EVALUATION"

    # 2. Add an application while reviews haven't started (should succeed)
    res_add = client.post(
        f"/api/v1/committee/batches/{batch_id}/applications",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"application_id": str(apps[2].id)},
    )
    assert res_add.status_code == 200
    assert res_add.json()["application_count"] == 3

    # 3. Create committee reviewer and submit a review
    reviewer = _create_user(db, f"rev_{uuid.uuid4().hex[:6]}@test.gov.in", UserRole.COMMITTEE, "Reviewer 1")
    # Assign reviewer to scheme
    assignment = CommitteeAssignment(
        user_id=reviewer.id,
        scheme_id=scheme.id,
        role_in_committee="CHAIRPERSON",
    )
    db.add(assignment)
    db.commit()

    rev_token = _get_token(client, reviewer.email)

    review_res = client.post(
        f"/api/v1/committee/applications/{apps[0].id}/review?batch_id={batch_id}",
        headers={"Authorization": f"Bearer {rev_token}"},
        json={
            "scores": {"feasibility": 20.0},
            "recommendation": "RECOMMEND",
            "remarks": "Strong proposal",
        },
    )
    assert review_res.status_code == 200, review_res.text

    # 4. Now that reviews have started, batch membership MUST be immutable!
    cand_x = _create_user(db, f"candx_{uuid.uuid4().hex[:6]}@test.gov.in", UserRole.APPLICANT, "Cand X")
    app_x = Application(
        reference_id=f"REF-{uuid.uuid4().hex[:8].upper()}",
        applicant_id=cand_x.id,
        scheme_id=scheme.id,
        scheme_version_id=sv.id,
        status=ApplicationStatus.VERIFIED,
        form_data={"academic": {"percentage_marks": 90.0}},
    )
    db.add(app_x)
    db.commit()

    res_forbidden_add = client.post(
        f"/api/v1/committee/batches/{batch_id}/applications",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"application_id": str(app_x.id)},
    )
    assert res_forbidden_add.status_code == 409, "Batch membership must be immutable once review begins!"


def test_blind_committee_evaluation_and_confidentiality(client: TestClient, db: Session, admin_token: str):
    """Test blind evaluation: members cannot see peer reviews or scores."""
    scheme, sv, apps = _setup_phase6_test_data(db)

    res = client.post(
        "/api/v1/committee/batches",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": f"Blind-Batch-{scheme.scheme_code}",
            "scheme_id": str(scheme.id),
            "scheme_version_id": str(sv.id),
            "application_ids": [str(apps[0].id)],
        },
    )
    batch_id = res.json()["id"]

    # 2 reviewers
    rev1 = _create_user(db, f"blind1_{uuid.uuid4().hex[:6]}@test.gov.in", UserRole.COMMITTEE, "Reviewer A")
    rev2 = _create_user(db, f"blind2_{uuid.uuid4().hex[:6]}@test.gov.in", UserRole.COMMITTEE, "Reviewer B")
    for r in [rev1, rev2]:
        db.add(CommitteeAssignment(user_id=r.id, scheme_id=scheme.id, role_in_committee="MEMBER"))
    db.commit()

    token1 = _get_token(client, rev1.email)
    token2 = _get_token(client, rev2.email)

    # Reviewer 1 submits review
    res1 = client.post(
        f"/api/v1/committee/applications/{apps[0].id}/review?batch_id={batch_id}",
        headers={"Authorization": f"Bearer {token1}"},
        json={
            "scores": {"feasibility": 20.0},
            "recommendation": "RECOMMEND",
            "remarks": "Top candidate remarks confidential",
        },
    )
    assert res1.status_code == 200

    # Reviewer 2 views application dossiers in committee queue
    queue_res = client.get(
        f"/api/v1/committee/batches/{batch_id}/applications",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert queue_res.status_code == 200
    queue_items = queue_res.json()
    assert len(queue_items) == 1
    # Check that Reviewer 2 sees their own review status as None, and does NOT see Reviewer 1's scores or comments
    app_view = queue_items[0]
    assert app_view["my_review"] is None
    assert "Top candidate remarks confidential" not in str(app_view)

    # Reviewer 2 attempts to fetch peer reviews before lock -> 403 Forbidden
    res_peer = client.get(
        f"/api/v1/committee/applications/{apps[0].id}/reviews?batch_id={batch_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert res_peer.status_code == 403, "Peer reviews must be sealed until batch is locked"


def test_object_level_committee_authorization(client: TestClient, db: Session, admin_token: str):
    """Ensure committee member assigned to Scheme A cannot access Scheme B."""
    scheme_a, sv_a, apps_a = _setup_phase6_test_data(db)
    scheme_b, sv_b, apps_b = _setup_phase6_test_data(db)

    # Member assigned only to Scheme A
    member_a = _create_user(db, f"mem_a_{uuid.uuid4().hex[:6]}@test.gov.in", UserRole.COMMITTEE, "Member A")
    db.add(CommitteeAssignment(user_id=member_a.id, scheme_id=scheme_a.id, role_in_committee="MEMBER"))
    db.commit()

    token_a = _get_token(client, member_a.email)

    # Create batch for Scheme B
    res_b = client.post(
        "/api/v1/committee/batches",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Batch B",
            "scheme_id": str(scheme_b.id),
            "scheme_version_id": str(sv_b.id),
            "application_ids": [str(apps_b[0].id)],
        },
    )
    batch_b_id = res_b.json()["id"]

    # Member A attempts to view Batch B applications -> 403 Forbidden
    res_forbidden = client.get(
        f"/api/v1/committee/batches/{batch_b_id}/applications",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_forbidden.status_code == 403, "Committee member must not access unassigned scheme batches"


def test_per_application_quorum_enforcement_and_atomic_rollback(client: TestClient, db: Session, admin_token: str):
    """Test that if any candidate in batch does not meet quorum, calculation aborts atomically."""
    scheme, sv, apps = _setup_phase6_test_data(db)

    # Batch with apps[0] and apps[1]. Quorum requirement is 2 reviews.
    res = client.post(
        "/api/v1/committee/batches",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": f"Quorum-Batch-{scheme.scheme_code}",
            "scheme_id": str(scheme.id),
            "scheme_version_id": str(sv.id),
            "application_ids": [str(apps[0].id), str(apps[1].id)],
        },
    )
    batch_id = res.json()["id"]

    rev1 = _create_user(db, f"qrev1_{uuid.uuid4().hex[:6]}@test.gov.in", UserRole.COMMITTEE, "Q Rev 1")
    rev2 = _create_user(db, f"qrev2_{uuid.uuid4().hex[:6]}@test.gov.in", UserRole.COMMITTEE, "Q Rev 2")
    for r in [rev1, rev2]:
        db.add(CommitteeAssignment(user_id=r.id, scheme_id=scheme.id, role_in_committee="CHAIRPERSON"))
    db.commit()

    t1 = _get_token(client, rev1.email)
    t2 = _get_token(client, rev2.email)

    # apps[0] gets 2 reviews (meets quorum)
    client.post(
        f"/api/v1/committee/applications/{apps[0].id}/review?batch_id={batch_id}",
        headers={"Authorization": f"Bearer {t1}"},
        json={"scores": {"feasibility": 20.0}, "recommendation": "RECOMMEND"},
    )
    client.post(
        f"/api/v1/committee/applications/{apps[0].id}/review?batch_id={batch_id}",
        headers={"Authorization": f"Bearer {t2}"},
        json={"scores": {"feasibility": 22.0}, "recommendation": "RECOMMEND"},
    )

    # apps[1] gets only 1 review (lacks quorum: 1 < 2)
    client.post(
        f"/api/v1/committee/applications/{apps[1].id}/review?batch_id={batch_id}",
        headers={"Authorization": f"Bearer {t1}"},
        json={"scores": {"feasibility": 18.0}, "recommendation": "RECOMMEND"},
    )

    # Attempt to lock evaluations -> Should fail because apps[1] has not met quorum!
    lock_fail = client.post(
        f"/api/v1/committee/batches/{batch_id}/lock-evaluations",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert lock_fail.status_code == 400
    assert "quorum" in lock_fail.text.lower()

    # Verify atomic rollback: apps[0] must NOT be MERIT_RANKED and no MeritScore rows committed
    db.expire_all()
    app0_check = db.query(Application).filter(Application.id == apps[0].id).first()
    assert app0_check.status == ApplicationStatus.VERIFIED
    scores_count = db.query(MeritScore).filter(MeritScore.batch_id == uuid.UUID(batch_id)).count()
    assert scores_count == 0

    # Now provide second review for apps[1]
    client.post(
        f"/api/v1/committee/applications/{apps[1].id}/review?batch_id={batch_id}",
        headers={"Authorization": f"Bearer {t2}"},
        json={"scores": {"feasibility": 20.0}, "recommendation": "RECOMMEND"},
    )

    # Lock batch evaluations -> Succeeds now!
    lock_success = client.post(
        f"/api/v1/committee/batches/{batch_id}/lock-evaluations",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert lock_success.status_code == 200

    # Calculate merit scores -> Succeeded!
    calc_res = client.post(
        f"/api/v1/merit/batches/{batch_id}/calculate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert calc_res.status_code == 200
    res_data = calc_res.json()
    assert res_data["scored_count"] == 2

    # Check status transitioned to MERIT_RANKED
    db.expire_all()
    app0_after = db.query(Application).filter(Application.id == apps[0].id).first()
    app1_after = db.query(Application).filter(Application.id == apps[1].id).first()
    assert app0_after.status == ApplicationStatus.MERIT_RANKED
    assert app1_after.status == ApplicationStatus.MERIT_RANKED


def test_batch_scoped_evaluation_locking(client: TestClient, db: Session, admin_token: str):
    """Test that locked batch rejects new reviews or review edits with 409 Conflict."""
    scheme, sv, apps = _setup_phase6_test_data(db)

    # Quorum is 1 for this test to easily lock
    sv.scoring_weights["committee_config"]["required_quorum"] = 1
    db.commit()

    res = client.post(
        "/api/v1/committee/batches",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": f"Lock-Batch-{scheme.scheme_code}",
            "scheme_id": str(scheme.id),
            "scheme_version_id": str(sv.id),
            "application_ids": [str(apps[0].id)],
        },
    )
    batch_id = res.json()["id"]

    rev = _create_user(db, f"lrev_{uuid.uuid4().hex[:6]}@test.gov.in", UserRole.COMMITTEE, "Lock Rev")
    db.add(CommitteeAssignment(user_id=rev.id, scheme_id=scheme.id, role_in_committee="CHAIRPERSON"))
    db.commit()
    t = _get_token(client, rev.email)

    # Submit 1 review
    client.post(
        f"/api/v1/committee/applications/{apps[0].id}/review?batch_id={batch_id}",
        headers={"Authorization": f"Bearer {t}"},
        json={"scores": {"feasibility": 20.0}, "recommendation": "RECOMMEND"},
    )

    # Set quorum to 1 by creating a fresh dictionary for scoring_weights
    w = dict(sv.scoring_weights)
    w["committee_config"] = {"required_quorum": 1, "blind_evaluation": True}
    sv.scoring_weights = w
    db.commit()

    # Lock the batch
    lock_res = client.post(
        f"/api/v1/committee/batches/{batch_id}/lock-evaluations",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert lock_res.status_code == 200
    assert lock_res.json()["is_locked"] is True

    # Attempt to submit review post-lock -> 409 Conflict
    rev_res = client.post(
        f"/api/v1/committee/applications/{apps[0].id}/review?batch_id={batch_id}",
        headers={"Authorization": f"Bearer {t}"},
        json={"scores": {"feasibility": 22.0}, "recommendation": "RECOMMEND"},
    )
    assert rev_res.status_code == 409, "Must return 409 Conflict when submitting review to locked batch"


def test_selection_boundary_tie_halting_and_chairperson_resolution(client: TestClient, db: Session, admin_token: str):
    """Test boundary-crossing tie halts finalization until chairperson resolution occurs."""
    scheme, sv, apps = _setup_phase6_test_data(db)

    # Set scheme version total_slots = 1 so that rank 1 is selected and rank 2 is waitlisted
    w = dict(sv.scoring_weights)
    w["quotas"] = {"total_slots": 1, "waitlist_slots": 1}
    w["quota_config"] = {"total_slots": 1, "waitlist_slots": 1}
    sv.scoring_weights = w

    # Make apps[0] and apps[1] have IDENTICAL academic data, DOB, and submission timestamp
    same_time = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    apps[0].submitted_at = same_time
    apps[1].submitted_at = same_time
    apps[0].form_data = {"academic": {"percentage_marks": 85.0}, "personal": {"dob": "1995-01-01"}}
    apps[1].form_data = {"academic": {"percentage_marks": 85.0}, "personal": {"dob": "1995-01-01"}}
    db.commit()

    # Create batch
    res = client.post(
        "/api/v1/committee/batches",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": f"Tie-Batch-{scheme.scheme_code}",
            "scheme_id": str(scheme.id),
            "scheme_version_id": str(sv.id),
            "application_ids": [str(apps[0].id), str(apps[1].id)],
        },
    )
    batch_id = res.json()["id"]

    # 2 Reviewers give identical scores to both candidates
    chair = _create_user(db, f"chair_{uuid.uuid4().hex[:6]}@test.gov.in", UserRole.COMMITTEE, "Chairperson")
    member = _create_user(db, f"mem_{uuid.uuid4().hex[:6]}@test.gov.in", UserRole.COMMITTEE, "Member")
    db.add(CommitteeAssignment(user_id=chair.id, scheme_id=scheme.id, role_in_committee="CHAIRPERSON"))
    db.add(CommitteeAssignment(user_id=member.id, scheme_id=scheme.id, role_in_committee="MEMBER"))
    db.commit()

    t_chair = _get_token(client, chair.email)
    t_mem = _get_token(client, member.email)

    for a in [apps[0], apps[1]]:
        client.post(
            f"/api/v1/committee/applications/{a.id}/review?batch_id={batch_id}",
            headers={"Authorization": f"Bearer {t_chair}"},
            json={"scores": {"feasibility": 20.0}, "recommendation": "RECOMMEND"},
        )
        client.post(
            f"/api/v1/committee/applications/{a.id}/review?batch_id={batch_id}",
            headers={"Authorization": f"Bearer {t_mem}"},
            json={"scores": {"feasibility": 20.0}, "recommendation": "RECOMMEND"},
        )

    # Lock batch and calculate scores
    client.post(f"/api/v1/committee/batches/{batch_id}/lock-evaluations", headers={"Authorization": f"Bearer {admin_token}"})
    calc_res = client.post(
        f"/api/v1/merit/batches/{batch_id}/calculate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert calc_res.status_code == 200
    calc_data = calc_res.json()
    assert calc_data["boundary_tie_flag"] is True

    # Attempt finalization without resolving the boundary tie -> Should fail with 409 Conflict
    fin_res = client.post(
        f"/api/v1/committee/batches/{batch_id}/finalize",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "resolution_reference": "MTA-SEL-2026-001",
            "committee_minutes": "Minutes detailing review and scrutiny by the committee members",
            "meeting_date": "2026-09-20T10:00:00Z",
        },
    )
    assert fin_res.status_code == 409
    assert "tie" in fin_res.text.lower() or "conflict" in fin_res.text.lower()

    # Now Chairperson resolves the tie: apps[0] preferred over apps[1]
    res_tie = client.post(
        f"/api/v1/committee/batches/{batch_id}/resolve-tie",
        headers={"Authorization": f"Bearer {t_chair}"},
        json={
            "preferred_candidate_id": str(apps[0].id),
            "secondary_candidate_id": str(apps[1].id),
            "statutory_justification": "Prior published research in relevant peer-reviewed journal domain",
            "authority_order_reference": "MTA-ORDER-2026-TIE",
        },
    )
    assert res_tie.status_code == 200, res_tie.text

    # Finalization can now proceed cleanly!
    fin_res2 = client.post(
        f"/api/v1/committee/batches/{batch_id}/finalize",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "resolution_reference": "MTA-SEL-2026-001",
            "committee_minutes": "Minutes detailing review and scrutiny by the committee members",
            "meeting_date": "2026-09-20T10:00:00Z",
        },
    )
    assert fin_res2.status_code == 200, fin_res2.text
    fin_data = fin_res2.json()
    assert fin_data["status"] == "FINALIZED"
    assert fin_data["selected_count"] == 1
    assert fin_data["waitlisted_count"] == 1

    # Check outcomes from batch results
    res_batch_results = client.get(
        f"/api/v1/committee/batches/{batch_id}/results",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_batch_results.status_code == 200
    allocations = res_batch_results.json()
    assert len(allocations) == 2

    # apps[0] should be SELECTED (rank 1 <= total_slots 1)
    # apps[1] should be WAITLISTED (rank 2 <= total_slots + waitlist_slots 2)
    alloc_map = {str(a["application_id"]): a for a in allocations}
    assert alloc_map[str(apps[0].id)]["result"] == "SELECTED"
    assert alloc_map[str(apps[1].id)]["result"] == "WAITLISTED"


def test_administrative_selection_override_and_rank_preservation(client: TestClient, db: Session, admin_token: str, officer_token: str):
    """Test administrative override retains original MeritScore.rank and creates audited history."""
    scheme, sv, apps = _setup_phase6_test_data(db)

    # Configure slots: 1 slot selected, 1 waitlisted
    w = dict(sv.scoring_weights)
    w["quotas"] = {"total_slots": 1, "waitlist_slots": 1}
    w["quota_config"] = {"total_slots": 1, "waitlist_slots": 1}
    sv.scoring_weights = w
    db.commit()

    # Batch with apps[0] and apps[1]
    res = client.post(
        "/api/v1/committee/batches",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": f"Override-Batch-{scheme.scheme_code}",
            "scheme_id": str(scheme.id),
            "scheme_version_id": str(sv.id),
            "application_ids": [str(apps[0].id), str(apps[1].id)],
        },
    )
    batch_id = res.json()["id"]

    # Reviewers: apps[0] gets higher score than apps[1]
    r1 = _create_user(db, f"or1_{uuid.uuid4().hex[:6]}@test.gov.in", UserRole.COMMITTEE, "O Rev 1")
    r2 = _create_user(db, f"or2_{uuid.uuid4().hex[:6]}@test.gov.in", UserRole.COMMITTEE, "O Rev 2")
    for r in [r1, r2]:
        db.add(CommitteeAssignment(user_id=r.id, scheme_id=scheme.id, role_in_committee="CHAIRPERSON"))
    db.commit()

    t1 = _get_token(client, r1.email)
    t2 = _get_token(client, r2.email)

    for r_tok in [t1, t2]:
        client.post(
            f"/api/v1/committee/applications/{apps[0].id}/review?batch_id={batch_id}",
            headers={"Authorization": f"Bearer {r_tok}"},
            json={"scores": {"feasibility": 25.0}, "recommendation": "RECOMMEND"},
        )
        client.post(
            f"/api/v1/committee/applications/{apps[1].id}/review?batch_id={batch_id}",
            headers={"Authorization": f"Bearer {r_tok}"},
            json={"scores": {"feasibility": 15.0}, "recommendation": "RECOMMEND"},
        )

    # Lock, calculate, finalize
    client.post(f"/api/v1/committee/batches/{batch_id}/lock-evaluations", headers={"Authorization": f"Bearer {admin_token}"})
    client.post(f"/api/v1/merit/batches/{batch_id}/calculate", headers={"Authorization": f"Bearer {admin_token}"})
    client.post(
        f"/api/v1/committee/batches/{batch_id}/finalize",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "resolution_reference": "MTA-SEL-REV",
            "committee_minutes": "Minutes detailing review and scrutiny by the committee members",
            "meeting_date": "2026-09-20T10:00:00Z",
        },
    )

    # apps[1] is WAITLISTED (rank 2)
    db.expire_all()
    orig_merit = db.query(MeritScore).filter(MeritScore.application_id == apps[1].id, MeritScore.is_current == True).first()
    assert orig_merit.rank == 2

    # 1. Non-admin cannot override -> 403 Forbidden
    res_officer_override = client.post(
        f"/api/v1/committee/admin/selection-override",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={
            "application_id": str(apps[1].id),
            "target_status": "SELECTED",
            "override_reason": "Special sports quota dispensation approved by Secretary under clause 4",
            "authority_reference": "Order #482",
        },
    )
    assert res_officer_override.status_code == 403

    # 2. Admin performs override
    res_admin_override = client.post(
        f"/api/v1/committee/admin/selection-override",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "application_id": str(apps[1].id),
            "target_status": "SELECTED",
            "override_reason": "Special sports quota dispensation approved by Secretary under clause 4",
            "authority_reference": "Order #482",
        },
    )
    assert res_admin_override.status_code == 200, res_admin_override.text
    override_data = res_admin_override.json()
    assert override_data["is_override"] is True
    assert override_data["selection_round"] == 2
    assert override_data["result"] == "SELECTED"

    # 3. Verify rank is preserved and NEVER modified!
    db.expire_all()
    preserved_merit = db.query(MeritScore).filter(MeritScore.application_id == apps[1].id, MeritScore.is_current == True).first()
    assert preserved_merit.rank == 2, "Original MeritScore rank must be immutable upon administrative override!"

    # 4. Verify historical SelectionResult retention (both round 1 and round 2 exist)
    results = db.query(SelectionResult).filter(SelectionResult.application_id == apps[1].id).order_by(SelectionResult.selection_round).all()
    assert len(results) == 2
    assert results[0].selection_round == 1
    assert results[0].result == "WAITLISTED"
    assert results[0].is_override is False
    assert results[1].selection_round == 2
    assert results[1].result == "SELECTED"
    assert results[1].is_override is True



def test_applicant_sanitized_result_view(client: TestClient, db: Session, admin_token: str):
    """Verify applicant can query their sanitized selection outcome without seeing committee member IDs or notes."""
    scheme, sv, apps = _setup_phase6_test_data(db)

    res = client.post(
        "/api/v1/committee/batches",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": f"App-View-{scheme.scheme_code}",
            "scheme_id": str(scheme.id),
            "scheme_version_id": str(sv.id),
            "application_ids": [str(apps[0].id)],
        },
    )
    batch_id = res.json()["id"]

    rev1 = _create_user(db, f"rv1_{uuid.uuid4().hex[:6]}@test.gov.in", UserRole.COMMITTEE, "R1")
    rev2 = _create_user(db, f"rv2_{uuid.uuid4().hex[:6]}@test.gov.in", UserRole.COMMITTEE, "R2")
    for r in [rev1, rev2]:
        db.add(CommitteeAssignment(user_id=r.id, scheme_id=scheme.id, role_in_committee="CHAIRPERSON"))
    db.commit()

    for r in [rev1, rev2]:
        tok = _get_token(client, r.email)
        client.post(
            f"/api/v1/committee/applications/{apps[0].id}/review?batch_id={batch_id}",
            headers={"Authorization": f"Bearer {tok}"},
            json={"scores": {"feasibility": 25.0}, "recommendation": "RECOMMEND", "remarks": "CONFIDENTIAL_COMMITTEE_NOTE"},
        )

    client.post(f"/api/v1/committee/batches/{batch_id}/lock-evaluations", headers={"Authorization": f"Bearer {admin_token}"})
    client.post(f"/api/v1/merit/batches/{batch_id}/calculate", headers={"Authorization": f"Bearer {admin_token}"})

    # Query as candidate 1 BEFORE finalization (Status is MERIT_RANKED)
    applicant = db.query(User).filter(User.id == apps[0].applicant_id).first()
    cand_token = _get_token(client, applicant.email)

    pre_final_res = client.get(
        f"/api/v1/applications/{apps[0].id}/result",
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert pre_final_res.status_code == 200
    pre_body = pre_final_res.json()
    assert pre_body["result"] == "PENDING_ANNOUNCEMENT", "Internal rank/decision must be hidden before official selection"
    assert pre_body["rank"] is None, "Rank must be None for applicant before finalization"

    # Now finalize batch selection
    client.post(
        f"/api/v1/committee/batches/{batch_id}/finalize",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "resolution_reference": "MTA-OUT-2026",
            "committee_minutes": "CONFIDENTIAL_MINUTES_MINUTES_MINUTES_MINUTES",
            "meeting_date": "2026-09-20T10:00:00Z",
        },
    )

    # Query as candidate 1 AFTER finalization
    res_result = client.get(
        f"/api/v1/applications/{apps[0].id}/result",
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert res_result.status_code == 200, res_result.text
    result_body = res_result.json()
    assert result_body["result"] == "SELECTED"
    assert result_body["rank"] == 1
    assert "CONFIDENTIAL_COMMITTEE_NOTE" not in str(result_body)
    assert "CONFIDENTIAL_MINUTES" not in str(result_body)


def test_concurrent_batch_finalization_conflict(client: TestClient, db: Session, admin_token: str):
    """Test that concurrent or duplicate finalization calls are blocked with 409 Conflict."""
    scheme, sv, apps = _setup_phase6_test_data(db)

    res = client.post(
        "/api/v1/committee/batches",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": f"Concurrent-Batch-{scheme.scheme_code}",
            "scheme_id": str(scheme.id),
            "scheme_version_id": str(sv.id),
            "application_ids": [str(apps[0].id)],
        },
    )
    batch_id = res.json()["id"]

    rev1 = _create_user(db, f"crv1_{uuid.uuid4().hex[:6]}@test.gov.in", UserRole.COMMITTEE, "CR1")
    rev2 = _create_user(db, f"crv2_{uuid.uuid4().hex[:6]}@test.gov.in", UserRole.COMMITTEE, "CR2")
    for r in [rev1, rev2]:
        db.add(CommitteeAssignment(user_id=r.id, scheme_id=scheme.id, role_in_committee="CHAIRPERSON"))
    db.commit()

    for r in [rev1, rev2]:
        tok = _get_token(client, r.email)
        client.post(
            f"/api/v1/committee/applications/{apps[0].id}/review?batch_id={batch_id}",
            headers={"Authorization": f"Bearer {tok}"},
            json={"scores": {"feasibility": 25.0}, "recommendation": "RECOMMEND"},
        )

    client.post(f"/api/v1/committee/batches/{batch_id}/lock-evaluations", headers={"Authorization": f"Bearer {admin_token}"})
    client.post(f"/api/v1/merit/batches/{batch_id}/calculate", headers={"Authorization": f"Bearer {admin_token}"})

    finalize_payload = {
        "resolution_reference": "MTA-CONCUR-2026",
        "committee_minutes": "Minutes detailing concurrent test execution",
        "meeting_date": "2026-09-20T10:00:00Z",
    }

    # First finalization succeeds
    fin1 = client.post(
        f"/api/v1/committee/batches/{batch_id}/finalize",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=finalize_payload,
    )
    assert fin1.status_code == 200

    # Second finalization attempt fails with 409 Conflict
    fin2 = client.post(
        f"/api/v1/committee/batches/{batch_id}/finalize",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=finalize_payload,
    )
    assert fin2.status_code == 409, "Duplicate or concurrent finalization must return 409 Conflict"


def test_scheme_version_and_batch_isolation(client: TestClient, db: Session, admin_token: str):
    """Test that evaluation batches maintain strict scheme-version isolation."""
    scheme, sv, apps = _setup_phase6_test_data(db)

    # Create Scheme B and SchemeVersion B
    scheme_b = Scheme(
        scheme_code=f"TEST_SCHEME_ISOL_{uuid.uuid4().hex[:4].upper()}",
        name="Isolated Scheme B",
        description="[DEMO PROTOTYPE] Isolation testing",
        is_active=True,
    )
    db.add(scheme_b)
    db.commit()

    sv_b = SchemeVersion(
        scheme_id=scheme_b.id,
        scheme_code=scheme_b.scheme_code,
        scheme_version="1.0",
        name="Scheme B v1.0",
        form_schema={},
        eligibility_rules={},
        required_documents={},
        scoring_weights=sv.scoring_weights,
        is_active=True,
    )
    db.add(sv_b)
    db.commit()

    # Attempt to create batch with Scheme A's scheme_id but Scheme B's scheme_version_id
    res_mismatch = client.post(
        "/api/v1/committee/batches",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Mismatched Batch",
            "scheme_id": str(scheme.id),
            "scheme_version_id": str(sv_b.id),
            "application_ids": [str(apps[0].id)],
        },
    )
    assert res_mismatch.status_code == 400, "Must reject scheme_id / scheme_version_id mismatch"

    # Cleanup
    db.delete(sv_b)
    db.delete(scheme_b)
    db.commit()


def test_finalized_batch_scores_and_ranks_immutable(client: TestClient, db: Session, admin_token: str):
    """Verify that once finalized, neither merit re-calculation nor tie resolution can alter scores/ranks."""
    scheme, sv, apps = _setup_phase6_test_data(db)

    res = client.post(
        "/api/v1/committee/batches",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": f"Immutable-Batch-{scheme.scheme_code}",
            "scheme_id": str(scheme.id),
            "scheme_version_id": str(sv.id),
            "application_ids": [str(apps[0].id), str(apps[1].id)],
        },
    )
    batch_id = res.json()["id"]

    rev1 = _create_user(db, f"im1_{uuid.uuid4().hex[:6]}@test.gov.in", UserRole.COMMITTEE, "IM1")
    rev2 = _create_user(db, f"im2_{uuid.uuid4().hex[:6]}@test.gov.in", UserRole.COMMITTEE, "IM2")
    for r in [rev1, rev2]:
        db.add(CommitteeAssignment(user_id=r.id, scheme_id=scheme.id, role_in_committee="CHAIRPERSON"))
    db.commit()

    for a in [apps[0], apps[1]]:
        for r in [rev1, rev2]:
            tok = _get_token(client, r.email)
            client.post(
                f"/api/v1/committee/applications/{a.id}/review?batch_id={batch_id}",
                headers={"Authorization": f"Bearer {tok}"},
                json={"scores": {"feasibility": 20.0}, "recommendation": "RECOMMEND"},
            )

    client.post(f"/api/v1/committee/batches/{batch_id}/lock-evaluations", headers={"Authorization": f"Bearer {admin_token}"})
    client.post(f"/api/v1/merit/batches/{batch_id}/calculate", headers={"Authorization": f"Bearer {admin_token}"})
    client.post(
        f"/api/v1/committee/batches/{batch_id}/finalize",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "resolution_reference": "MTA-IMMUT-2026",
            "committee_minutes": "Minutes detailing finalization immutability",
            "meeting_date": "2026-09-20T10:00:00Z",
        },
    )

    # 1. Attempt to re-calculate merit on finalized batch -> 409 Conflict
    recalc_res = client.post(
        f"/api/v1/merit/batches/{batch_id}/calculate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert recalc_res.status_code == 409, "Must return 409 Conflict when attempting to recalculate finalized batch"

    # 2. Attempt to resolve tie on finalized batch -> 409 Conflict
    tok_chair = _get_token(client, rev1.email)
    tie_res = client.post(
        f"/api/v1/committee/batches/{batch_id}/resolve-tie",
        headers={"Authorization": f"Bearer {tok_chair}"},
        json={
            "preferred_candidate_id": str(apps[0].id),
            "secondary_candidate_id": str(apps[1].id),
            "statutory_justification": "Post-finalization tampering attempt",
            "authority_order_reference": "ILLEGAL-ORDER",
        },
    )
    assert tie_res.status_code == 409, "Must return 409 Conflict when attempting tie resolution on finalized batch"

