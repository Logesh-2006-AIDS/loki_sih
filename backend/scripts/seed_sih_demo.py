"""
SIH 2026 Master Demo Seeding Suite
Ministry of Tribal Affairs (MoTA) AI-Enabled Fellowship & Scholarship Management System

Constructs an end-to-end living demonstration covering all 8 project phases:
  - 4 Standard Role Users (Applicant, Officer, Committee, Admin)
  - 2 Demo Schemes (DEMO-NFST and DEMO-NOS) with locked 1.0 SchemeVersion rules
  - 8 Multi-Stage Synthetic Tribal Scholar Dossiers with complete legal histories and audit trails:
      Dossier 1 (Phase 2): Sunita Soren (Draft Application)
      Dossier 2 (Phase 3): Rahul Munda (Submitted / AI OCR Verified)
      Dossier 3 (Phase 4): Priya Marandi (Under Officer Manual Scrutiny / Discrepancy Flagged)
      Dossier 4 (Phase 5): Amit Oraon (Deficiency Flagged / Replacement Upload Lineage v1->v2)
      Dossier 5 (Phase 6): Pooja Santhal (Verified in Committee Blind Scoring Batch)
      Dossier 6 (Phase 6): Vikram Gond (Merit Ranked 92.5 & Officially SELECTED)
      Dossier 7 (Phase 8): Dr. Ananya Bodo (Active Fellow / Year 1 DBT Settled via Mock PFMS)
      Dossier 8 (Phase 8): Rajeshwar Bhil (Installment APPROVED_FOR_PAYMENT ready for live DBT execution)

Idempotent: Safe to execute repeatedly without generating duplicate records.
"""

import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Add backend root to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.session import SessionLocal
from app.models.user import User
from app.models.scheme import Scheme
from app.models.scheme_version import SchemeVersion
from app.models.application import Application
from app.models.document import Document
from app.models.document_verification import DocumentVerification
from app.models.deficiency import Deficiency
from app.models.committee_evaluation_batch import CommitteeEvaluationBatch
from app.models.merit_score import MeritScore
from app.models.selection_result import SelectionResult
from app.models.fellowship import FellowshipRecord, DisbursementInstallment, RenewalSubmission
from app.models.audit_log import AuditLog
from app.core.enums import (
    UserRole,
    UserAccountStatus,
    ApplicationStatus,
    DocumentStatus,
    FellowshipStatus,
    DisbursementStatus,
    AuditEntityType,
    SelectionResultEnum,
)
from app.core.security import get_password_hash

DEMO_PASSWORD = "Demo@12345"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "loki@06")


def seed_sih_demo():
    db = SessionLocal()
    print("=" * 75)
    print("STARTING SIH 2026 MASTER DEMO SEEDING SUITE")
    print("Ministry of Tribal Affairs — AI-Enabled Scholarship & Fellowship Portal")
    print("=" * 75)

    try:
        # ---------------------------------------------------------------------
        # 1. Standard Persona Users
        # ---------------------------------------------------------------------
        print("\n[1/5] Seeding Standard Role Personas...")
        personas = [
            ("applicant@demo.gov.in", "Sunita Soren (Tribal Scholar)", UserRole.APPLICANT, DEMO_PASSWORD),
            ("officer@demo.gov.in", "Dr. Rajesh Verma (Scrutiny Officer)", UserRole.OFFICER, DEMO_PASSWORD),
            ("committee@demo.gov.in", "Prof. K. Nayak (Selection Committee)", UserRole.COMMITTEE, DEMO_PASSWORD),
            ("loki@gmail.com", "Ministry Administrator (MoTA HQ)", UserRole.ADMIN, ADMIN_PASSWORD),
        ]
        user_map = {}
        for email, name, role, pwd in personas:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email,
                    password_hash=get_password_hash(pwd),
                    full_name=name,
                    phone="+91 9876543210",
                    role=role.value,
                    account_status=UserAccountStatus.ACTIVE,
                    is_active=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                print(f"  [+] Created User: {email} ({role.value})")
            else:
                user.password_hash = get_password_hash(pwd)
                user.role = role.value
                user.account_status = UserAccountStatus.ACTIVE
                user.is_active = True
                db.commit()
                db.refresh(user)
                print(f"  [.] Updated Existing User: {email} ({role.value})")
            user_map[role] = user

        # Remove legacy admin account if present
        legacy_admin = db.query(User).filter(User.email == "admin@demo.gov.in").first()
        if legacy_admin:
            loki_admin = user_map.get(UserRole.ADMIN)
            if loki_admin:
                db.query(AuditLog).filter(AuditLog.actor_id == legacy_admin.id).update({"actor_id": loki_admin.id})
                db.query(DisbursementInstallment).filter(DisbursementInstallment.approved_by == legacy_admin.id).update({"approved_by": loki_admin.id})
            db.delete(legacy_admin)
            db.commit()
            print("  [-] Removed legacy admin@demo.gov.in account")

        # ---------------------------------------------------------------------
        # 2. Demo Schemes with Prototype Disclaimers & Scoring Weights
        # ---------------------------------------------------------------------
        print("\n[2/5] Seeding Demonstration Schemes (DEMO-NFST & DEMO-NOS)...")
        scheme_configs = [
            {
                "code": "DEMO-NFST",
                "name": "National Fellowship for Higher Education of ST Students [DEMO PROTOTYPE]",
                "desc": (
                    "Financial assistance to Scheduled Tribe (ST) students to pursue M.Phil and Ph.D. degrees in India. "
                    "[DEMO / PROTOTYPE configuration for SIH testing. Official scheme guidelines pending verification.]"
                ),
                "scoring_weights": {
                    "academic_merit": 50,
                    "vulnerability_index": 20,
                    "research_quality": 20,
                    "interview": 10,
                    "financial_rules": {
                        "monthly_stipend": 31000.0,
                        "annual_contingency": 10000.0,
                        "annual_hra": 0.0,
                    },
                    "quota_config": {
                        "total_slots": 750,
                        "st_quota": 100,
                        "pvtg_subquota": 10,
                        "female_subquota": 33,
                    },
                },
            },
            {
                "code": "DEMO-NOS",
                "name": "National Overseas Scholarship for ST Candidates [DEMO PROTOTYPE]",
                "desc": (
                    "Financial assistance to selected ST candidates for pursuing Master level courses and Ph.D. abroad. "
                    "[DEMO / PROTOTYPE configuration for SIH testing. Official scheme guidelines pending verification.]"
                ),
                "scoring_weights": {
                    "academic_merit": 60,
                    "vulnerability_index": 20,
                    "interview": 20,
                    "financial_rules": {
                        "monthly_stipend": 85000.0,
                        "annual_contingency": 50000.0,
                        "annual_hra": 20000.0,
                    },
                    "quota_config": {
                        "total_slots": 100,
                        "st_quota": 100,
                        "female_subquota": 30,
                    },
                },
            },
        ]

        scheme_map = {}
        version_map = {}
        for sc in scheme_configs:
            scheme = db.query(Scheme).filter(Scheme.scheme_code == sc["code"]).first()
            if not scheme:
                scheme = Scheme(
                    scheme_code=sc["code"],
                    name=sc["name"],
                    scheme_version="1.0",
                    is_demo=True,
                    description=sc["desc"],
                    eligibility_rules={
                        "community": "ST",
                        "min_qualifying_percentage": 55.0,
                        "max_annual_family_income": 600000,
                        "valid_course_types": ["Ph.D.", "M.Phil"],
                    },
                    form_schema={"type": "object", "properties": {"education": {"type": "object"}}},
                    required_documents={
                        "documents": [
                            {"code": "caste_certificate", "name": "ST Community / Caste Certificate", "required": True},
                            {"code": "income_certificate", "name": "Income Certificate", "required": True},
                            {"code": "marksheet", "name": "Academic Marksheet", "required": True},
                        ],
                        "disclaimer": "DEMO / PROTOTYPE DOCUMENT LIST",
                    },
                    scoring_weights=sc["scoring_weights"],
                    is_active=True,
                )
                db.add(scheme)
                db.commit()
                db.refresh(scheme)
                print(f"  [+] Created Scheme: {scheme.scheme_code}")
            else:
                # Ensure existing demo schemes conform to dict schema
                if isinstance(scheme.required_documents, list):
                    scheme.required_documents = {
                        "documents": [
                            {"code": doc, "name": doc.replace("_", " ").title(), "required": True}
                            for doc in scheme.required_documents
                        ],
                        "disclaimer": "DEMO / PROTOTYPE DOCUMENT LIST",
                    }
                    db.commit()
            scheme_map[sc["code"]] = scheme

            version = (
                db.query(SchemeVersion)
                .filter(SchemeVersion.scheme_id == scheme.id, SchemeVersion.scheme_version == "1.0")
                .first()
            )
            if not version:
                version = SchemeVersion(
                    scheme_id=scheme.id,
                    scheme_code=scheme.scheme_code,
                    scheme_version="1.0",
                    name=scheme.name,
                    description=scheme.description,
                    is_demo=True,
                    eligibility_rules=scheme.eligibility_rules,
                    form_schema=scheme.form_schema,
                    required_documents=scheme.required_documents,
                    scoring_weights=scheme.scoring_weights,
                    is_active=True,
                    is_locked=True,
                )
                db.add(version)
                db.commit()
                db.refresh(version)
                print(f"  [+] Created SchemeVersion: {version.scheme_code} v1.0")
            else:
                if isinstance(version.required_documents, list):
                    version.required_documents = scheme.required_documents
                    db.commit()
            version_map[sc["code"]] = version

        nfst_scheme = scheme_map["DEMO-NFST"]
        nfst_version = version_map["DEMO-NFST"]

        # ---------------------------------------------------------------------
        # 3. Dedicated Scholar Applicants for Multi-Stage Demonstrations
        # ---------------------------------------------------------------------
        print("\n[3/5] Provisioning Synthetic Tribal Scholar Accounts...")
        scholars = [
            ("sunita.soren@demo.gov.in", "Sunita Soren", "Santhal", "Odisha"),
            ("rahul.munda@demo.gov.in", "Rahul Munda", "Munda", "Jharkhand"),
            ("priya.marandi@demo.gov.in", "Priya Marandi", "Santhal", "West Bengal"),
            ("amit.oraon@demo.gov.in", "Amit Oraon", "Oraon", "Chhattisgarh"),
            ("pooja.santhal@demo.gov.in", "Pooja Santhal", "Santhal", "Jharkhand"),
            ("vikram.gond@demo.gov.in", "Vikram Gond", "Gond", "Madhya Pradesh"),
            ("ananya.bodo@demo.gov.in", "Dr. Ananya Bodo", "Bodo", "Assam"),
            ("rajeshwar.bhil@demo.gov.in", "Rajeshwar Bhil", "Bhil", "Rajasthan"),
        ]

        scholar_users = {}
        for email, name, community, state in scholars:
            usr = db.query(User).filter(User.email == email).first()
            if not usr:
                usr = User(
                    email=email,
                    password_hash=get_password_hash(DEMO_PASSWORD),
                    full_name=name,
                    phone="+91 9876543200",
                    role=UserRole.APPLICANT.value,
                    is_active=True,
                )
                db.add(usr)
                db.commit()
                db.refresh(usr)
                print(f"  [+] Created Scholar: {name} ({community}, {state})")
            scholar_users[email] = usr

        # ---------------------------------------------------------------------
        # 4. Multi-Stage Synthetic Dossiers (Preserving State Invariants)
        # ---------------------------------------------------------------------
        print("\n[4/5] Seeding Multi-Stage Lifecycle Dossiers (Phases 2 through 8)...")

        # Ensure demo physical PDF assets exist in storage/demo
        import pypdf
        from app.core.config import settings
        demo_storage_dir = Path(settings.STORAGE_PATH).resolve() / "demo"
        demo_storage_dir.mkdir(parents=True, exist_ok=True)
        for demo_filename in ["caste_rahul.pdf", "income_priya.pdf", "marksheet_v1.pdf"]:
            pdf_target = demo_storage_dir / demo_filename
            if not pdf_target.exists():
                writer = pypdf.PdfWriter()
                writer.add_blank_page(width=612, height=792)
                with open(pdf_target, "wb") as f:
                    writer.write(f)

        # Dossier 1: Phase 2 - Incomplete Draft
        ref1 = "DEMO-APP-2026-001"
        app1 = db.query(Application).filter(Application.reference_id == ref1).first()
        if not app1:
            app1 = Application(
                reference_id=ref1,
                applicant_id=scholar_users["sunita.soren@demo.gov.in"].id,
                scheme_id=nfst_scheme.id,
                scheme_version_id=nfst_version.id,
                status=ApplicationStatus.DRAFT,
                form_data={
                    "personal": {"name": "Sunita Soren", "gender": "Female", "community": "ST"},
                    "education": {"degree": "M.Sc. Environmental Science", "institution": "IIT Bombay"},
                },
                frozen_rules_snapshot=nfst_version.scoring_weights,
            )
            db.add(app1)
            db.commit()
            print("  [+] Dossier 1: Sunita Soren -> DRAFT")

        # Dossier 2: Phase 3 - Submitted & AI OCR Processed
        ref2 = "DEMO-APP-2026-002"
        app2 = db.query(Application).filter(Application.reference_id == ref2).first()
        if not app2:
            app2 = Application(
                reference_id=ref2,
                applicant_id=scholar_users["rahul.munda@demo.gov.in"].id,
                scheme_id=nfst_scheme.id,
                scheme_version_id=nfst_version.id,
                status=ApplicationStatus.UNDER_AI_VERIFICATION,
                form_data={
                    "personal": {"name": "Rahul Munda", "gender": "Male", "community": "ST"},
                    "education": {"degree": "M.Tech Metallurgical Eng", "institution": "NIT Jamshedpur", "marks_percentage": 78.5},
                    "income": {"annual_family_income": 320000},
                },
                frozen_rules_snapshot=nfst_version.scoring_weights,
                submitted_at=datetime.now(timezone.utc) - timedelta(days=5),
            )
            db.add(app2)
            db.flush()

            # Add document and OCR extraction record
            doc2 = Document(
                application_id=app2.id,
                document_type="caste_certificate",
                original_filename="caste_certificate_rahul.pdf",
                storage_path="/storage/demo/caste_rahul.pdf",
                file_size=245000,
                mime_type="application/pdf",
                status=DocumentStatus.VERIFIED,
            )
            db.add(doc2)
            db.flush()

            ver2 = DocumentVerification(
                document_id=doc2.id,
                verification_status="VERIFIED",
                ocr_text="GOVERNMENT OF JHARKHAND CASTE CERTIFICATE. Name: Rahul Munda. Community: ST (Munda).",
                extracted_fields={"candidate_name": "Rahul Munda", "community": "ST", "state": "Jharkhand"},
                field_confidences={"candidate_name": 0.96, "community": 0.99},
                comparison_results={"candidate_name": {"match": True, "confidence": 0.96}},
                overall_confidence=0.98,
                flags=[],
            )
            db.add(ver2)
            db.commit()
            print("  [+] Dossier 2: Rahul Munda -> UNDER_AI_VERIFICATION (OCR matching: 98%)")

        # Dossier 3: Phase 4 - Under Manual Officer Scrutiny (Discrepancy Flagged)
        ref3 = "DEMO-APP-2026-003"
        app3 = db.query(Application).filter(Application.reference_id == ref3).first()
        if not app3:
            app3 = Application(
                reference_id=ref3,
                applicant_id=scholar_users["priya.marandi@demo.gov.in"].id,
                scheme_id=nfst_scheme.id,
                scheme_version_id=nfst_version.id,
                status=ApplicationStatus.UNDER_MANUAL_REVIEW,
                form_data={
                    "personal": {"name": "Priya Marandi", "community": "ST"},
                    "education": {"degree": "M.A. Anthropology", "institution": "Visva-Bharati"},
                    "income": {"annual_family_income": 250000},
                },
                frozen_rules_snapshot=nfst_version.scoring_weights,
                submitted_at=datetime.now(timezone.utc) - timedelta(days=8),
            )
            db.add(app3)
            db.flush()

            doc3 = Document(
                application_id=app3.id,
                document_type="income_certificate",
                original_filename="income_cert_priya.pdf",
                storage_path="/storage/demo/income_priya.pdf",
                file_size=180000,
                mime_type="application/pdf",
                status=DocumentStatus.FLAGGED,
            )
            db.add(doc3)
            db.flush()

            ver3 = DocumentVerification(
                document_id=doc3.id,
                verification_status="FLAGGED",
                ocr_text="REVENUE DEPARTMENT. Annual Income: Rs 4,50,000.",
                extracted_fields={"annual_income": 450000},
                field_confidences={"annual_income": 0.82},
                comparison_results={"annual_income": {"match": False, "confidence": 0.82}},
                overall_confidence=0.75,
                flags=[{"type": "INCOME_MISMATCH_SUSPECTED", "description": "Reported 2.5L vs OCR 4.5L"}],
            )
            db.add(ver3)
            db.commit()
            print("  [+] Dossier 3: Priya Marandi -> UNDER_MANUAL_REVIEW (Officer Discrepancy Desk)")

        # Dossier 4: Phase 5 - Deficiency Flagged / Replacement Upload Lineage
        ref4 = "DEMO-APP-2026-004"
        app4 = db.query(Application).filter(Application.reference_id == ref4).first()
        if not app4:
            app4 = Application(
                reference_id=ref4,
                applicant_id=scholar_users["amit.oraon@demo.gov.in"].id,
                scheme_id=nfst_scheme.id,
                scheme_version_id=nfst_version.id,
                status=ApplicationStatus.DEFICIENT,
                form_data={
                    "personal": {"name": "Amit Oraon", "community": "ST"},
                    "education": {"degree": "M.Sc. Physics", "institution": "Central Univ of Jharkhand"},
                },
                frozen_rules_snapshot=nfst_version.scoring_weights,
                submitted_at=datetime.now(timezone.utc) - timedelta(days=12),
            )
            db.add(app4)
            db.flush()

            doc4 = Document(
                application_id=app4.id,
                document_type="marksheet",
                original_filename="marksheet_v1_amit.pdf",
                storage_path="/storage/demo/marksheet_v1.pdf",
                file_size=310000,
                mime_type="application/pdf",
                status=DocumentStatus.RESUBMISSION_REQUIRED,
            )
            db.add(doc4)
            db.flush()

            # Phase 5 Deficiency Model Record
            def4 = Deficiency(
                application_id=app4.id,
                document_id=doc4.id,
                reason="DOCUMENT_ILLEGIBLE",
                applicant_message="The semester 4 grade sheet page 2 is blurred. Please upload a clear scanned copy.",
                status="OPEN",
            )
            db.add(def4)
            db.commit()
            print("  [+] Dossier 4: Amit Oraon -> DEFICIENT (Phase 5 Lineage v1 awaiting v2 upload)")

        # Dossier 5 & 6: Phase 6 - Committee Evaluation & Selection
        batch = db.query(CommitteeEvaluationBatch).filter(CommitteeEvaluationBatch.name == "DEMO-SIH-BATCH-2026").first()
        if not batch:
            batch = CommitteeEvaluationBatch(
                scheme_id=nfst_scheme.id,
                scheme_version_id=nfst_version.id,
                name="DEMO-SIH-BATCH-2026",
                status="FINALIZED",
                is_locked=True,
                locked_at=datetime.now(timezone.utc),
                locked_by=user_map[UserRole.COMMITTEE].id,
            )
            db.add(batch)
            db.commit()
            db.refresh(batch)

        # Dossier 5: Committee Blind Evaluation
        ref5 = "DEMO-APP-2026-005"
        app5 = db.query(Application).filter(Application.reference_id == ref5).first()
        if not app5:
            app5 = Application(
                reference_id=ref5,
                applicant_id=scholar_users["pooja.santhal@demo.gov.in"].id,
                scheme_id=nfst_scheme.id,
                scheme_version_id=nfst_version.id,
                status=ApplicationStatus.VERIFIED,
                form_data={"personal": {"community": "ST"}, "education": {"marks_percentage": 84.0}},
                frozen_rules_snapshot=nfst_version.scoring_weights,
                submitted_at=datetime.now(timezone.utc) - timedelta(days=20),
            )
            db.add(app5)
            db.commit()
            print("  [+] Dossier 5: Pooja Santhal -> VERIFIED (Committee Blind Scoring Queue)")

        # Dossier 6: Merit Ranked & Officially Selected
        ref6 = "DEMO-APP-2026-006"
        app6 = db.query(Application).filter(Application.reference_id == ref6).first()
        if not app6:
            app6 = Application(
                reference_id=ref6,
                applicant_id=scholar_users["vikram.gond@demo.gov.in"].id,
                scheme_id=nfst_scheme.id,
                scheme_version_id=nfst_version.id,
                status=ApplicationStatus.SELECTED,
                form_data={"personal": {"name": "Vikram Gond", "community": "ST"}, "education": {"marks_percentage": 92.5}},
                frozen_rules_snapshot=nfst_version.scoring_weights,
                submitted_at=datetime.now(timezone.utc) - timedelta(days=30),
            )
            db.add(app6)
            db.flush()

            # Merit Score
            ms6 = MeritScore(
                batch_id=batch.id,
                application_id=app6.id,
                scheme_version_id=nfst_version.id,
                total_score=92.5,
                score_breakdown={
                    "academic_score": 48.5,
                    "category_score": 19.0,
                    "financial_score": 15.0,
                    "interview_score": 10.0,
                },
                rank=1,
                is_current=True,
                formula_version="1.0",
                calculated_by=user_map[UserRole.COMMITTEE].id,
            )
            db.add(ms6)

            # Selection Result
            sr6 = SelectionResult(
                batch_id=batch.id,
                application_id=app6.id,
                scheme_version_id=nfst_version.id,
                result=SelectionResultEnum.SELECTED,
                rank=1,
                quota_category="MERIT_OPEN_ST",
                finalized_by=user_map[UserRole.COMMITTEE].id,
                finalized_at=datetime.now(timezone.utc),
            )
            db.add(sr6)
            db.commit()
            print("  [+] Dossier 6: Vikram Gond -> SELECTED (Merit Rank #1, Score: 92.5)")

        # Dossier 7: Phase 8 - Active Fellow with Year 1 DBT Settled
        ref7 = "DEMO-APP-2026-007"
        app7 = db.query(Application).filter(Application.reference_id == ref7).first()
        if not app7:
            app7 = Application(
                reference_id=ref7,
                applicant_id=scholar_users["ananya.bodo@demo.gov.in"].id,
                scheme_id=nfst_scheme.id,
                scheme_version_id=nfst_version.id,
                status=ApplicationStatus.FELLOWSHIP_ACTIVE,
                form_data={"personal": {"name": "Dr. Ananya Bodo", "community": "ST"}, "education": {"marks_percentage": 88.0}},
                frozen_rules_snapshot=nfst_version.scoring_weights,
                submitted_at=datetime.now(timezone.utc) - timedelta(days=60),
            )
            db.add(app7)
            db.flush()

            # Fellowship Record
            fel7 = FellowshipRecord(
                application_id=app7.id,
                fellowship_number="DEMO-MTA-FEL-2026-001",
                sanction_order_number="DEMO-SANCTION-2026-001",
                sanction_mode="DEMO_SIMULATED",
                sanction_date=date(2026, 1, 15),
                scheme_id=nfst_scheme.id,
                scheme_version_id=nfst_version.id,
                applicant_id=app7.applicant_id,
                status=FellowshipStatus.ACTIVE.value,
                current_year=1,
                tenure_years=5,
                start_date=date(2026, 1, 1),
                end_date=date(2031, 1, 1),
                institution_name="IIT Guwahati",
                department="Computer Science & Engineering",
                guide_name="Prof. D. Borah",
                research_topic="Natural Language Processing for Bodo and Tribal Dialects",
                disbursement_status=DisbursementStatus.SUCCESS,
            )
            db.add(fel7)
            db.flush()

            # Year 1 DBT Installment - SUCCESS
            inst7_1 = DisbursementInstallment(
                fellowship_id=fel7.id,
                installment_number=1,
                academic_year=1,
                period_start=date(2026, 1, 1),
                period_end=date(2027, 1, 1),
                stipend_amount=372000.0,
                contingency_amount=10000.0,
                hra_amount=0.0,
                total_amount=382000.0,
                payment_status=DisbursementStatus.SUCCESS.value,
                integration_mode="SIMULATED_MOCK",
                payment_request_id=uuid.uuid4(),
                pfms_reference_id="DEMO-PFMS-TXN-001",
                bank_reference_utr="DEMO-PFMS-UTR-20260901",
                account_number_last4="4321",
                ifsc_code="SBIN0001234",
                retry_count=0,
                processed_at=datetime.now(timezone.utc) - timedelta(days=20),
                approved_by=user_map[UserRole.ADMIN].id,
                approved_at=datetime.now(timezone.utc) - timedelta(days=22),
            )
            db.add(inst7_1)

            # Year 2 DBT Installment - SCHEDULED
            inst7_2 = DisbursementInstallment(
                fellowship_id=fel7.id,
                installment_number=2,
                academic_year=2,
                period_start=date(2027, 1, 1),
                period_end=date(2028, 1, 1),
                stipend_amount=372000.0,
                contingency_amount=10000.0,
                hra_amount=0.0,
                total_amount=382000.0,
                payment_status=DisbursementStatus.SCHEDULED.value,
                integration_mode="SIMULATED_MOCK",
                payment_request_id=uuid.uuid4(),
                account_number_last4="4321",
                ifsc_code="SBIN0001234",
                retry_count=0,
            )
            db.add(inst7_2)
            db.commit()
            print("  [+] Dossier 7: Dr. Ananya Bodo -> FELLOWSHIP_ACTIVE (Year 1 DBT Settled: UTR DEMO-PFMS-UTR-20260901)")

        # Dossier 8: Phase 8 - Ready for Live 1-Click DBT Dispatch in Admin Desk
        ref8 = "DEMO-APP-2026-008"
        app8 = db.query(Application).filter(Application.reference_id == ref8).first()
        if not app8:
            app8 = Application(
                reference_id=ref8,
                applicant_id=scholar_users["rajeshwar.bhil@demo.gov.in"].id,
                scheme_id=nfst_scheme.id,
                scheme_version_id=nfst_version.id,
                status=ApplicationStatus.FELLOWSHIP_ACTIVE,
                form_data={"personal": {"name": "Rajeshwar Bhil", "community": "ST"}, "education": {"marks_percentage": 86.5}},
                frozen_rules_snapshot=nfst_version.scoring_weights,
                submitted_at=datetime.now(timezone.utc) - timedelta(days=40),
            )
            db.add(app8)
            db.flush()

            fel8 = FellowshipRecord(
                application_id=app8.id,
                fellowship_number="DEMO-MTA-FEL-2026-002",
                sanction_order_number="DEMO-SANCTION-2026-002",
                sanction_mode="DEMO_SIMULATED",
                sanction_date=date(2026, 2, 1),
                scheme_id=nfst_scheme.id,
                scheme_version_id=nfst_version.id,
                applicant_id=app8.applicant_id,
                status=FellowshipStatus.ACTIVE.value,
                current_year=1,
                tenure_years=5,
                start_date=date(2026, 2, 1),
                end_date=date(2031, 2, 1),
                institution_name="MLSU Udaipur",
                department="Tribal Studies & Folklore",
                guide_name="Prof. S. L. Sharma",
                research_topic="Oral Traditions and Ethnomedicine of Bhil Tribes in Rajasthan",
                disbursement_status=DisbursementStatus.APPROVED_FOR_PAYMENT,
            )
            db.add(fel8)
            db.flush()

            # Installment 1 in APPROVED_FOR_PAYMENT (Locked amounts, ready for 1-click dispatch!)
            inst8 = DisbursementInstallment(
                fellowship_id=fel8.id,
                installment_number=1,
                academic_year=1,
                period_start=date(2026, 2, 1),
                period_end=date(2027, 2, 1),
                stipend_amount=372000.0,
                contingency_amount=10000.0,
                hra_amount=0.0,
                total_amount=382000.0,
                payment_status=DisbursementStatus.APPROVED_FOR_PAYMENT.value,
                integration_mode="SIMULATED_MOCK",
                payment_request_id=uuid.uuid4(),
                account_number_last4="7890",
                ifsc_code="SBIN0005678",
                retry_count=0,
                approved_by=user_map[UserRole.ADMIN].id,
                approved_at=datetime.now(timezone.utc) - timedelta(hours=2),
            )
            db.add(inst8)
            db.commit()
            print("  [+] Dossier 8: Rajeshwar Bhil -> APPROVED_FOR_PAYMENT (Ready for live 1-click DBT execution)")

        # ---------------------------------------------------------------------
        # 5. Summary & SIH Evaluation Credentials
        # ---------------------------------------------------------------------
        print("\n" + "=" * 75)
        print("SIH 2026 DEMO SEEDING COMPLETED SUCCESSFULLY!")
        print("All identifiers prefixed with 'DEMO-' (Unmistakably Synthetic).")
        print("\nDemo Credentials (Password for all: Demo@12345):")
        print("  1. APPLICANT:  applicant@demo.gov.in    (Scholar Self-Service & Forms)")
        print("  2. OFFICER:    officer@demo.gov.in      (OCR Side-by-Side Desk Scrutiny)")
        print("  3. COMMITTEE:  committee@demo.gov.in    (Blind Evaluation & Merit Scoring)")
        print("  4. ADMIN:      loki@gmail.com           (Analytics, Schemes & DBT Desk)")
        print("=" * 75)

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Demo seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_sih_demo()
