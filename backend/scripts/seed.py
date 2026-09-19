"""
Idempotent Database Seed Script - Phase 0 Foundation
AI-Enabled Scholarship & Fellowship Management System (Ministry of Tribal Affairs)

Seeds:
  - 4 Demo Users (APPLICANT, OFFICER, COMMITTEE, ADMIN)
  - 2 Demo Schemes (NFST, NOS) with clear DEMO/PROTOTYPE disclaimers
"""

import sys
from pathlib import Path

# Add backend root to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.session import SessionLocal
from app.models.user import User
from app.models.scheme import Scheme
from app.core.enums import UserRole
from app.core.security import get_password_hash
from app.repositories.audit_repo import AuditRepository

DEMO_PASSWORD = "Demo@12345"

DEMO_USERS = [
    {
        "full_name": "Demo Applicant (Tribal Scholar)",
        "email": "applicant@demo.gov.in",
        "phone": "+91 9876543210",
        "password": DEMO_PASSWORD,
        "role": UserRole.APPLICANT,
    },
    {
        "full_name": "Verification Officer (Regional Desk)",
        "email": "officer@demo.gov.in",
        "phone": "+91 9876543211",
        "password": DEMO_PASSWORD,
        "role": UserRole.OFFICER,
    },
    {
        "full_name": "Selection Committee Member",
        "email": "committee@demo.gov.in",
        "phone": "+91 9876543212",
        "password": DEMO_PASSWORD,
        "role": UserRole.COMMITTEE,
    },
    {
        "full_name": "System Administrator",
        "email": "admin@demo.gov.in",
        "phone": "+91 9876543213",
        "password": DEMO_PASSWORD,
        "role": UserRole.ADMIN,
    },
]

DEMO_SCHEMES = [
    {
        "scheme_code": "NFST",
        "name": "National Fellowship for Higher Education of ST Students",
        "scheme_version": "1.0",
        "is_demo": True,
        "description": (
            "Financial assistance to Scheduled Tribe (ST) students to pursue higher studies "
            "such as M.Phil and Ph.D. degrees in Sciences, Humanities, and Engineering in India. "
            "[DEMO / PROTOTYPE configuration for SIH testing. Official scheme guidelines pending verification. "
            "Note: scheme_version is the foundation for future versioning, not full history.]"
        ),
        "eligibility_rules": {
            "disclaimer": "DEMO / PROTOTYPE RULES",
            "community": "ST",
            "min_qualifying_percentage": 55.0,
            "max_annual_family_income": 600000,
            "valid_course_types": ["M.Phil", "Ph.D.", "Integrated Ph.D."],
            "mode": "Full-Time",
        },
        "form_schema": {
            "disclaimer": "DEMO / PROTOTYPE SCHEMA",
            "sections": [
                {
                    "id": "personal",
                    "title": "Personal & Identity Details",
                    "fields": ["full_name", "dob", "gender", "caste_tribe_name", "aadhaar_ref"],
                },
                {
                    "id": "academic",
                    "title": "Postgraduate Academic Details",
                    "fields": ["pg_degree", "university_name", "year_of_passing", "percentage_cgpa"],
                },
                {
                    "id": "research",
                    "title": "Doctoral Research Details",
                    "fields": ["research_topic", "supervisor_name", "department", "admission_date"],
                },
            ],
        },
        "required_documents": {
            "disclaimer": "DEMO / PROTOTYPE DOCUMENT LIST",
            "documents": [
                {"type": "CASTE_CERTIFICATE", "label": "Valid ST Community Certificate", "required": True},
                {"type": "PG_MARKSHEET", "label": "Postgraduate Final Marksheet / Degree", "required": True},
                {"type": "ADMISSION_LETTER", "label": "University Doctoral Admission Letter", "required": True},
                {"type": "INCOME_CERTIFICATE", "label": "Competent Authority Income Certificate", "required": True},
            ],
        },
        "scoring_weights": {
            "academic_percentage": 40,
            "research_proposal_rating": 30,
            "institution_nirf_score": 30,
        },
    },
    {
        "scheme_code": "NOS",
        "name": "National Overseas Scholarship for ST Candidates",
        "scheme_version": "1.0",
        "is_demo": True,
        "description": (
            "Financial assistance to selected ST candidates for pursuing Master level courses and "
            "Ph.D. in recognized foreign universities/institutions abroad. "
            "[DEMO / PROTOTYPE configuration for SIH testing. Official scheme guidelines pending verification. "
            "Note: scheme_version is the foundation for future versioning, not full history.]"
        ),
        "eligibility_rules": {
            "disclaimer": "DEMO / PROTOTYPE RULES",
            "community": "ST",
            "min_qualifying_percentage": 55.0,
            "max_annual_family_income": 800000,
            "max_age": 35,
            "passport_required": True,
            "target_institution_ranking": "Top 500 QS World University Rankings",
        },
        "form_schema": {
            "disclaimer": "DEMO / PROTOTYPE SCHEMA",
            "sections": [
                {
                    "id": "personal",
                    "title": "Personal & Passport Information",
                    "fields": ["full_name", "dob", "gender", "passport_number", "passport_validity"],
                },
                {
                    "id": "academic",
                    "title": "Prior Qualifications",
                    "fields": ["qualifying_degree", "institution", "percentage_cgpa"],
                },
                {
                    "id": "overseas",
                    "title": "Foreign Admission Details",
                    "fields": ["foreign_university", "country", "course_name", "qs_rank", "intake_session"],
                },
            ],
        },
        "required_documents": {
            "disclaimer": "DEMO / PROTOTYPE DOCUMENT LIST",
            "documents": [
                {"type": "CASTE_CERTIFICATE", "label": "Valid ST Community Certificate", "required": True},
                {"type": "DEGREE_CERTIFICATE", "label": "Qualifying Degree Marksheet", "required": True},
                {"type": "FOREIGN_OFFER_LETTER", "label": "Unconditional Foreign Admission Offer", "required": True},
                {"type": "PASSPORT_COPY", "label": "Valid Indian Passport (Bio Pages)", "required": True},
                {"type": "INCOME_CERTIFICATE", "label": "Income Certificate / ITR", "required": True},
            ],
        },
        "scoring_weights": {
            "academic_percentage": 35,
            "institution_qs_rank": 35,
            "sop_and_interview": 30,
        },
    },
]


def seed_database():
    db = SessionLocal()
    audit_repo = AuditRepository(db)
    print("=" * 70)
    print("MTA Scholarship & Fellowship System - Phase 0 Foundation Database Seed")
    print("=" * 70)

    try:
        # Seed Demo Users
        print("\n[1/2] Checking and seeding Demo Users...")
        for user_data in DEMO_USERS:
            existing = db.query(User).filter(User.email == user_data["email"]).first()
            if existing:
                print(f"  -> User '{user_data['email']}' already exists. Skipping.")
            else:
                user = User(
                    full_name=user_data["full_name"],
                    email=user_data["email"],
                    phone=user_data["phone"],
                    password_hash=get_password_hash(user_data["password"]),
                    role=user_data["role"],
                    is_active=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)

                audit_repo.log_event(
                    entity_type="USER",
                    entity_id=str(user.id),
                    actor_id=user.id,
                    action="SEED_USER_CREATED",
                    details={"email": user.email, "role": str(user.role.value)},
                )
                print(f"  [+] Created User: {user.email} (Role: {user.role.value})")

        # Seed Demo Schemes
        print("\n[2/2] Checking and seeding Demo Schemes...")
        for s_data in DEMO_SCHEMES:
            existing_scheme = (
                db.query(Scheme).filter(Scheme.scheme_code == s_data["scheme_code"]).first()
            )
            if existing_scheme:
                print(f"  -> Scheme '{s_data['scheme_code']}' already exists. Skipping.")
            else:
                scheme = Scheme(
                    scheme_code=s_data["scheme_code"],
                    name=s_data["name"],
                    scheme_version=s_data["scheme_version"],
                    is_demo=s_data["is_demo"],
                    description=s_data["description"],
                    eligibility_rules=s_data["eligibility_rules"],
                    form_schema=s_data["form_schema"],
                    required_documents=s_data["required_documents"],
                    scoring_weights=s_data["scoring_weights"],
                    is_active=True,
                )
                db.add(scheme)
                db.commit()
                db.refresh(scheme)

                audit_repo.log_event(
                    entity_type="SCHEME",
                    entity_id=str(scheme.id),
                    action="SEED_SCHEME_CREATED",
                    details={"scheme_code": scheme.scheme_code, "version": scheme.scheme_version},
                )
                print(f"  [+] Created Scheme: {scheme.scheme_code} - {scheme.name}")

        print("\n" + "=" * 70)
        print("SEEDING COMPLETED SUCCESSFULLY")
        print("Demo Credentials (Password for all: Demo@12345):")
        print("  - Applicant: applicant@demo.gov.in")
        print("  - Officer:   officer@demo.gov.in")
        print("  - Committee: committee@demo.gov.in")
        print("  - Admin:     admin@demo.gov.in")
        print("=" * 70)

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
