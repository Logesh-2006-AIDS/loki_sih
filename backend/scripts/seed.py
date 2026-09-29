"""
Idempotent Database Seed Script - Phase 1 Foundation
AI-Enabled Scholarship & Fellowship Management System (Ministry of Tribal Affairs)

Seeds:
  - 4 Demo Users (APPLICANT, OFFICER, COMMITTEE, ADMIN)
  - 2 Demo Schemes (NFST, NOS) with version 1.0 SchemeVersion records
  - Explicit rule definitions and visible PROTOTYPE / DEMO disclaimers
"""

import os
import sys
from pathlib import Path

# Add backend root to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.session import SessionLocal
from app.models.user import User
from app.models.scheme import Scheme
from app.models.scheme_version import SchemeVersion
from app.models.officer_assignment import OfficerAssignment
from app.core.enums import UserRole, UserAccountStatus
from app.core.security import get_password_hash
from app.repositories.audit_repo import AuditRepository

DEMO_PASSWORD = "Demo@12345"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "loki@06")

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
        "email": "loki@gmail.com",
        "phone": "+91 9876543213",
        "password": ADMIN_PASSWORD,
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
            "Note: scheme_version is the authoritative foundation for versioning.]"
        ),
        "eligibility_rules": {
            "disclaimer": "DEMO / PROTOTYPE CONFIGURATION (Indicative Only - Not Official Gazette Rules)",
            "community": "ST",
            "min_qualifying_percentage": 55.0,
            "max_annual_family_income": 600000,
            "valid_course_types": ["M.Phil", "Ph.D.", "Integrated Ph.D."],
            "mode": "Full-Time",
            "rules": [
                {
                    "field": "community",
                    "operator": "equals",
                    "value": "ST",
                    "label": "Community / Category",
                    "pass_message": "Category verified: Scheduled Tribe (ST).",
                    "fail_message": "Applicant must belong to the Scheduled Tribe (ST) community.",
                },
                {
                    "field": "min_qualifying_percentage",
                    "operator": "greater_than_or_equal",
                    "value": 55.0,
                    "label": "Qualifying Marks (%)",
                    "pass_message": "Qualifying marks requirement satisfied (>= 55.0%).",
                    "fail_message": "Minimum 55.0% marks in Master's degree required.",
                },
                {
                    "field": "max_annual_family_income",
                    "operator": "less_than_or_equal",
                    "value": 600000,
                    "label": "Annual Family Income Ceiling (₹)",
                    "pass_message": "Family income is within the ₹6,00,000 ceiling.",
                    "fail_message": "Family income exceeds the ₹6,00,000 ceiling.",
                },
                {
                    "field": "course_type",
                    "operator": "in",
                    "value": ["M.Phil", "Ph.D.", "Integrated Ph.D."],
                    "label": "Course Enrollment",
                    "pass_message": "Course enrollment is eligible (M.Phil / Ph.D. / Integrated Ph.D.).",
                    "fail_message": "Must be enrolled in regular M.Phil, Ph.D. or Integrated Ph.D.",
                },
            ],
        },
        "form_schema": {
            "disclaimer": "DEMO / PROTOTYPE SCHEMA",
            "sections": [
                {
                    "id": "personal",
                    "title": "Personal & Identity Details",
                    "description": "Basic identification and community details",
                    "fields": [
                        {
                            "name": "full_name",
                            "label": "Full Name as in Official Records",
                            "type": "text",
                            "required": True,
                            "placeholder": "e.g. Ramesh Chandra Meena",
                            "help_text": "Must match educational records and caste certificate.",
                        },
                        {
                            "name": "dob",
                            "label": "Date of Birth",
                            "type": "date",
                            "required": True,
                            "help_text": "As recorded in Secondary School Certificate (10th).",
                        },
                        {
                            "name": "gender",
                            "label": "Gender",
                            "type": "radio",
                            "required": True,
                            "options": [
                                {"label": "Male", "value": "Male"},
                                {"label": "Female", "value": "Female"},
                                {"label": "Other", "value": "Other"},
                            ],
                        },
                        {
                            "name": "email",
                            "label": "Email Address",
                            "type": "email",
                            "required": True,
                            "placeholder": "applicant@example.com",
                            "help_text": "All official notifications will be sent here.",
                        },
                        {
                            "name": "phone",
                            "label": "Primary Mobile Number",
                            "type": "phone",
                            "required": True,
                            "placeholder": "9876543210",
                        },
                        {
                            "name": "caste_tribe_name",
                            "label": "Specific ST Community / Tribe Name",
                            "type": "text",
                            "required": True,
                            "placeholder": "e.g. Gond / Santhal / Bhil / Meena",
                        },
                    ],
                },
                {
                    "id": "academic",
                    "title": "Postgraduate Academic Details",
                    "description": "Master's degree details for fellowship eligibility assessment",
                    "fields": [
                        {
                            "name": "pg_degree",
                            "label": "Postgraduate Degree Title",
                            "type": "select",
                            "required": True,
                            "options": [
                                {"label": "Master of Science (M.Sc.)", "value": "M.Sc."},
                                {"label": "Master of Arts (M.A.)", "value": "M.A."},
                                {"label": "Master of Technology (M.Tech.)", "value": "M.Tech."},
                                {"label": "Master of Commerce (M.Com.)", "value": "M.Com."},
                                {"label": "Master of Computer Applications (MCA)", "value": "MCA"},
                                {"label": "Other UGC-Recognized Master's", "value": "Other"},
                            ],
                        },
                        {
                            "name": "university_name",
                            "label": "University / Institute Name",
                            "type": "text",
                            "required": True,
                            "placeholder": "e.g. Jawaharlal Nehru University",
                        },
                        {
                            "name": "year_of_passing",
                            "label": "Year of Passing",
                            "type": "number",
                            "required": True,
                            "placeholder": "2024",
                        },
                        {
                            "name": "percentage_marks",
                            "label": "Postgraduate Aggregate Percentage (%)",
                            "type": "number",
                            "required": True,
                            "placeholder": "e.g. 64.5",
                            "help_text": "Minimum 55.0% marks required for NFST fellowship.",
                        },
                    ],
                },
                {
                    "id": "research",
                    "title": "Doctoral Research Enrollment",
                    "description": "Details of enrolled or admitted M.Phil / Ph.D. program",
                    "fields": [
                        {
                            "name": "course_type",
                            "label": "Enrolled Program Type",
                            "type": "select",
                            "required": True,
                            "options": [
                                {"label": "Ph.D. (Regular Full-Time)", "value": "Ph.D."},
                                {"label": "Integrated Ph.D.", "value": "Integrated Ph.D."},
                                {"label": "M.Phil", "value": "M.Phil"},
                            ],
                        },
                        {
                            "name": "department",
                            "label": "Department / Faculty",
                            "type": "text",
                            "required": True,
                            "placeholder": "e.g. Department of Biotechnology",
                        },
                        {
                            "name": "admission_date",
                            "label": "Date of Doctoral Admission / Registration",
                            "type": "date",
                            "required": True,
                        },
                        {
                            "name": "research_topic",
                            "label": "Approved Research Topic / Broad Proposal",
                            "type": "textarea",
                            "required": True,
                            "placeholder": "Describe the doctoral research subject and proposed methodology...",
                            "help_text": "Provide a brief synopsis of your research objective.",
                        },
                    ],
                },
                {
                    "id": "financial",
                    "title": "Financial & Employment Status",
                    "description": "Income assessment for scholarship entitlement",
                    "fields": [
                        {
                            "name": "annual_family_income",
                            "label": "Total Annual Family Income (₹)",
                            "type": "number",
                            "required": True,
                            "placeholder": "e.g. 450000",
                            "help_text": "Must not exceed ₹6,00,000 p.a. as per scheme ceiling.",
                        },
                        {
                            "name": "is_employed",
                            "label": "Currently Employed / Receiving Salary?",
                            "type": "radio",
                            "required": True,
                            "options": [
                                {"label": "No (Full-time Unemployed Scholar)", "value": "No"},
                                {"label": "Yes (On Study Leave / Deputation)", "value": "Yes"},
                            ],
                        },
                    ],
                },
                {
                    "id": "declaration",
                    "title": "Undertaking & Declarations",
                    "description": "Statutory declarations by the candidate",
                    "fields": [
                        {
                            "name": "st_community_declaration",
                            "label": "I hereby certify that I belong to the Scheduled Tribe (ST) category and hold a valid community certificate issued by a competent revenue authority.",
                            "type": "checkbox",
                            "required": True,
                        },
                        {
                            "name": "authenticity_declaration",
                            "label": "I solemnly declare that all particulars furnished and documents uploaded are authentic and correct to the best of my knowledge.",
                            "type": "checkbox",
                            "required": True,
                        },
                    ],
                },
            ],
        },
        "required_documents": {
            "disclaimer": "DEMO / PROTOTYPE DOCUMENT LIST",
            "documents": [
                {
                    "code": "CASTE_CERTIFICATE",
                    "type": "CASTE_CERTIFICATE",
                    "name": "ST Community / Caste Certificate",
                    "label": "ST Community / Caste Certificate",
                    "required": True,
                    "ocr_enabled": True,
                    "allowed_extensions": [".pdf", ".jpg", ".jpeg", ".png"],
                    "max_size_mb": 5,
                    "allow_multiple": False,
                    "verification_fields": [
                        {
                            "document_field": "community",
                            "application_field": "community",
                            "comparison": "text",
                            "label": "Community / Tribe Category",
                            "required": True,
                        },
                        {
                            "document_field": "full_name",
                            "application_field": "full_name",
                            "comparison": "name",
                            "label": "Full Name",
                            "required": True,
                        },
                    ],
                },
                {
                    "code": "INCOME_CERTIFICATE",
                    "type": "INCOME_CERTIFICATE",
                    "name": "Competent Authority Family Income Certificate",
                    "label": "Competent Authority Family Income Certificate",
                    "required": True,
                    "ocr_enabled": True,
                    "allowed_extensions": [".pdf", ".jpg", ".jpeg", ".png"],
                    "max_size_mb": 5,
                    "allow_multiple": False,
                    "verification_fields": [
                        {
                            "document_field": "annual_family_income",
                            "application_field": "annual_family_income",
                            "comparison": "currency",
                            "label": "Annual Family Income",
                            "required": True,
                        },
                        {
                            "document_field": "full_name",
                            "application_field": "full_name",
                            "comparison": "name",
                            "label": "Full Name",
                            "required": True,
                        },
                    ],
                },
                {
                    "code": "PG_MARKSHEET",
                    "type": "PG_MARKSHEET",
                    "name": "Postgraduate Final Marksheet / Degree Certificate",
                    "label": "Postgraduate Final Marksheet / Degree Certificate",
                    "required": True,
                    "ocr_enabled": True,
                    "allowed_extensions": [".pdf"],
                    "max_size_mb": 5,
                    "allow_multiple": False,
                    "verification_fields": [
                        {
                            "document_field": "percentage_marks",
                            "application_field": "percentage_marks",
                            "comparison": "percentage",
                            "label": "Postgraduate Aggregate Percentage",
                            "required": True,
                        },
                        {
                            "document_field": "full_name",
                            "application_field": "full_name",
                            "comparison": "name",
                            "label": "Full Name",
                            "required": True,
                        },
                    ],
                },
                {
                    "code": "ADMISSION_LETTER",
                    "type": "ADMISSION_LETTER",
                    "name": "University Doctoral Admission / Joining Letter",
                    "label": "University Doctoral Admission / Joining Letter",
                    "required": True,
                    "ocr_enabled": True,
                    "allowed_extensions": [".pdf"],
                    "max_size_mb": 5,
                    "allow_multiple": False,
                    "verification_fields": [
                        {
                            "document_field": "university_name",
                            "application_field": "university_name",
                            "comparison": "text",
                            "label": "University / Institute Name",
                            "required": True,
                        },
                        {
                            "document_field": "full_name",
                            "application_field": "full_name",
                            "comparison": "name",
                            "label": "Full Name",
                            "required": True,
                        },
                    ],
                },
            ],
        },
        "scoring_weights": {
            "disclaimer": "PROTOTYPE / DEMO CONFIGURATION — Indicative criteria for system validation only, pending official MoTA gazette verification.",
            "configuration_status": "PROTOTYPE",
            "total_max_score": 100.0,
            "scoring_components": [
                {
                    "code": "academic_percentage",
                    "label": "Postgraduate Qualifying Marks (%)",
                    "weight": 40.0,
                    "source_type": "APPLICATION_FORM_FIELD",
                    "field_path": "academic.percentage_marks",
                    "evaluation_type": "PERCENTAGE_NORMALIZED",
                    "max_raw": 100.0,
                },
                {
                    "code": "institution_reputation",
                    "label": "Admitted Institution NIRF / Accreditation Tier",
                    "weight": 30.0,
                    "source_type": "APPLICATION_FORM_FIELD",
                    "field_path": "research.nirf_rank",
                    "evaluation_type": "TIER_BRACKETS",
                    "brackets": [
                        {"max_rank": 50, "percentage_of_weight": 100.0, "label": "NIRF Top 50"},
                        {"max_rank": 100, "percentage_of_weight": 80.0, "label": "NIRF 51-100"},
                        {"max_rank": 200, "percentage_of_weight": 65.0, "label": "NIRF 101-200 / State Recognized"},
                    ],
                    "default_percentage_of_weight": 50.0,
                },
                {
                    "code": "research_proposal_rating",
                    "label": "Committee Research Proposal & Feasibility Rating",
                    "weight": 30.0,
                    "source_type": "COMMITTEE_EVALUATION",
                    "max_raw": 100.0,
                },
            ],
            "committee_config": {
                "min_assigned_evaluators": 1,
                "required_quorum": 1,
            },
            "quota_config": {
                "total_slots": 10,
                "waitlist_slots": 3,
            },
            "tie_breaking_order": [
                "ACADEMIC_PERCENTAGE",
                "AGE_SENIORITY",
                "FAMILY_INCOME",
                "SUBMISSION_TIMESTAMP",
            ],
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
            "Note: scheme_version is the authoritative foundation for versioning.]"
        ),
        "eligibility_rules": {
            "disclaimer": "DEMO / PROTOTYPE CONFIGURATION (Indicative Only - Not Official Gazette Rules)",
            "community": "ST",
            "min_qualifying_percentage": 55.0,
            "max_annual_family_income": 800000,
            "max_age": 35,
            "passport_required": True,
            "target_institution_ranking": "Top 500 QS World University Rankings",
            "rules": [
                {
                    "field": "community",
                    "operator": "equals",
                    "value": "ST",
                    "label": "Community / Category",
                    "pass_message": "Category verified: Scheduled Tribe (ST).",
                    "fail_message": "Applicant must belong to the Scheduled Tribe (ST) community.",
                },
                {
                    "field": "min_qualifying_percentage",
                    "operator": "greater_than_or_equal",
                    "value": 55.0,
                    "label": "Qualifying Degree Marks (%)",
                    "pass_message": "Qualifying marks requirement satisfied (>= 55.0%).",
                    "fail_message": "Minimum 55.0% marks in qualifying degree required.",
                },
                {
                    "field": "max_annual_family_income",
                    "operator": "less_than_or_equal",
                    "value": 800000,
                    "label": "Annual Family Income Ceiling (₹)",
                    "pass_message": "Family income is within the ₹8,00,000 ceiling.",
                    "fail_message": "Family income exceeds the ₹8,00,000 ceiling.",
                },
                {
                    "field": "max_age",
                    "operator": "less_than_or_equal",
                    "value": 35,
                    "label": "Maximum Age Limit",
                    "pass_message": "Candidate age is within the 35 years limit.",
                    "fail_message": "Candidate age must not exceed 35 years as on application deadline.",
                },
            ],
        },
        "form_schema": {
            "disclaimer": "DEMO / PROTOTYPE SCHEMA",
            "sections": [
                {
                    "id": "personal",
                    "title": "Personal & Passport Details",
                    "description": "Identity and international travel documentation",
                    "fields": [
                        {
                            "name": "full_name",
                            "label": "Full Name as in Passport",
                            "type": "text",
                            "required": True,
                            "placeholder": "e.g. Ananya Birsa",
                            "help_text": "Must match your Indian Passport exactly.",
                        },
                        {
                            "name": "dob",
                            "label": "Date of Birth",
                            "type": "date",
                            "required": True,
                        },
                        {
                            "name": "gender",
                            "label": "Gender",
                            "type": "radio",
                            "required": True,
                            "options": [
                                {"label": "Male", "value": "Male"},
                                {"label": "Female", "value": "Female"},
                                {"label": "Other", "value": "Other"},
                            ],
                        },
                        {
                            "name": "email",
                            "label": "Email Address",
                            "type": "email",
                            "required": True,
                            "placeholder": "applicant@example.com",
                        },
                        {
                            "name": "phone",
                            "label": "Mobile Number",
                            "type": "phone",
                            "required": True,
                            "placeholder": "9876543210",
                        },
                        {
                            "name": "passport_number",
                            "label": "Indian Passport Number",
                            "type": "text",
                            "required": True,
                            "placeholder": "A1234567",
                            "help_text": "Must be valid for at least 6 months beyond travel date.",
                        },
                        {
                            "name": "passport_expiry",
                            "label": "Passport Expiry Date",
                            "type": "date",
                            "required": True,
                        },
                    ],
                },
                {
                    "id": "academic",
                    "title": "Prior Qualifying Degree",
                    "description": "Qualifying degree obtained in India",
                    "fields": [
                        {
                            "name": "qualifying_degree",
                            "label": "Highest Qualification Attained",
                            "type": "select",
                            "required": True,
                            "options": [
                                {"label": "Bachelor's Degree (4 Years B.Tech/B.E./B.Sc.)", "value": "Bachelor's"},
                                {"label": "Master's Degree (M.A./M.Sc./M.Tech.)", "value": "Master's"},
                            ],
                        },
                        {
                            "name": "institution_name",
                            "label": "Name of Indian University / College",
                            "type": "text",
                            "required": True,
                            "placeholder": "e.g. IIT Delhi / Delhi University",
                        },
                        {
                            "name": "percentage_marks",
                            "label": "Qualifying Degree Aggregate Marks (%)",
                            "type": "number",
                            "required": True,
                            "placeholder": "e.g. 68.0",
                            "help_text": "Minimum 55.0% marks required for NOS.",
                        },
                    ],
                },
                {
                    "id": "overseas",
                    "title": "Foreign Admission Details",
                    "description": "Details of university and course abroad",
                    "fields": [
                        {
                            "name": "foreign_university",
                            "label": "Foreign University / Institution Name",
                            "type": "text",
                            "required": True,
                            "placeholder": "e.g. University of Oxford / MIT",
                        },
                        {
                            "name": "country",
                            "label": "Country of Study",
                            "type": "select",
                            "required": True,
                            "options": [
                                {"label": "United Kingdom", "value": "United Kingdom"},
                                {"label": "United States", "value": "United States"},
                                {"label": "Canada", "value": "Canada"},
                                {"label": "Australia", "value": "Australia"},
                                {"label": "Germany", "value": "Germany"},
                                {"label": "Other Recognized Foreign Country", "value": "Other"},
                            ],
                        },
                        {
                            "name": "course_level",
                            "label": "Level of Course Abroad",
                            "type": "radio",
                            "required": True,
                            "options": [
                                {"label": "Master's Degree", "value": "Master's"},
                                {"label": "Ph.D. / Doctoral Degree", "value": "Ph.D."},
                            ],
                        },
                        {
                            "name": "course_name",
                            "label": "Course / Degree Program Name",
                            "type": "text",
                            "required": True,
                            "placeholder": "e.g. M.Sc. in Data Science",
                        },
                        {
                            "name": "qs_rank",
                            "label": "Latest QS World University Ranking",
                            "type": "number",
                            "required": True,
                            "placeholder": "e.g. 45",
                            "help_text": "Must be within top 500 QS world rankings.",
                        },
                        {
                            "name": "statement_of_purpose",
                            "label": "Statement of Purpose (SOP)",
                            "type": "textarea",
                            "required": True,
                            "placeholder": "Explain your academic motivation, research interest, and how this study benefits community development in India...",
                        },
                    ],
                },
                {
                    "id": "financial",
                    "title": "Financial Declaration",
                    "description": "Family income ceiling compliance",
                    "fields": [
                        {
                            "name": "annual_family_income",
                            "label": "Total Combined Annual Family Income (₹)",
                            "type": "number",
                            "required": True,
                            "placeholder": "e.g. 650000",
                            "help_text": "Must not exceed ₹8,00,000 p.a. as per NOS scheme rules.",
                        },
                    ],
                },
                {
                    "id": "declaration",
                    "title": "Statutory Undertaking",
                    "description": "Statutory declarations for overseas scholars",
                    "fields": [
                        {
                            "name": "overseas_undertaking",
                            "label": "I undertake to return to India within 6 months of course completion or adhere to MoTA fellowship service terms.",
                            "type": "checkbox",
                            "required": True,
                        },
                        {
                            "name": "authenticity_declaration",
                            "label": "I declare that all admission offers, marksheets, and passport copies submitted are authentic.",
                            "type": "checkbox",
                            "required": True,
                        },
                    ],
                },
            ],
        },
        "required_documents": {
            "disclaimer": "DEMO / PROTOTYPE DOCUMENT LIST",
            "documents": [
                {
                    "code": "CASTE_CERTIFICATE",
                    "type": "CASTE_CERTIFICATE",
                    "name": "ST Community / Caste Certificate",
                    "label": "ST Community / Caste Certificate",
                    "required": True,
                    "ocr_enabled": True,
                    "allowed_extensions": [".pdf", ".jpg", ".jpeg", ".png"],
                    "max_size_mb": 5,
                    "allow_multiple": False,
                    "verification_fields": [
                        {
                            "document_field": "community",
                            "application_field": "community",
                            "comparison": "text",
                            "label": "Community / Tribe Category",
                            "required": True,
                        },
                        {
                            "document_field": "full_name",
                            "application_field": "full_name",
                            "comparison": "name",
                            "label": "Full Name",
                            "required": True,
                        },
                    ],
                },
                {
                    "code": "INCOME_CERTIFICATE",
                    "type": "INCOME_CERTIFICATE",
                    "name": "Competent Authority Family Income Certificate",
                    "label": "Competent Authority Family Income Certificate",
                    "required": True,
                    "ocr_enabled": True,
                    "allowed_extensions": [".pdf", ".jpg", ".jpeg", ".png"],
                    "max_size_mb": 5,
                    "allow_multiple": False,
                    "verification_fields": [
                        {
                            "document_field": "annual_family_income",
                            "application_field": "annual_family_income",
                            "comparison": "currency",
                            "label": "Annual Family Income",
                            "required": True,
                        },
                        {
                            "document_field": "full_name",
                            "application_field": "full_name",
                            "comparison": "name",
                            "label": "Full Name",
                            "required": True,
                        },
                    ],
                },
                {
                    "code": "PASSPORT_COPY",
                    "type": "PASSPORT_COPY",
                    "name": "Valid Indian Passport (Front & Back Bio Pages)",
                    "label": "Valid Indian Passport (Front & Back Bio Pages)",
                    "required": True,
                    "ocr_enabled": True,
                    "allowed_extensions": [".pdf", ".jpg", ".jpeg"],
                    "max_size_mb": 5,
                    "allow_multiple": False,
                    "verification_fields": [
                        {
                            "document_field": "full_name",
                            "application_field": "full_name",
                            "comparison": "name",
                            "label": "Full Name",
                            "required": True,
                        },
                        {
                            "document_field": "dob",
                            "application_field": "dob",
                            "comparison": "date",
                            "label": "Date of Birth",
                            "required": True,
                        },
                    ],
                },
                {
                    "code": "OFFER_LETTER",
                    "type": "OFFER_LETTER",
                    "name": "Unconditional Foreign University Admission Offer",
                    "label": "Unconditional Foreign University Admission Offer",
                    "required": True,
                    "ocr_enabled": True,
                    "allowed_extensions": [".pdf"],
                    "max_size_mb": 5,
                    "allow_multiple": False,
                    "verification_fields": [
                        {
                            "document_field": "university_name",
                            "application_field": "university_name",
                            "comparison": "text",
                            "label": "Foreign University Name",
                            "required": True,
                        },
                        {
                            "document_field": "full_name",
                            "application_field": "full_name",
                            "comparison": "name",
                            "label": "Full Name",
                            "required": True,
                        },
                    ],
                },
                {
                    "code": "MARKSHEET",
                    "type": "MARKSHEET",
                    "name": "Qualifying Degree Marksheet / Transcripts",
                    "label": "Qualifying Degree Marksheet / Transcripts",
                    "required": True,
                    "ocr_enabled": True,
                    "allowed_extensions": [".pdf"],
                    "max_size_mb": 5,
                    "allow_multiple": False,
                    "verification_fields": [
                        {
                            "document_field": "percentage_marks",
                            "application_field": "percentage_marks",
                            "comparison": "percentage",
                            "label": "Qualifying Marks",
                            "required": True,
                        },
                        {
                            "document_field": "full_name",
                            "application_field": "full_name",
                            "comparison": "name",
                            "label": "Full Name",
                            "required": True,
                        },
                    ],
                },
            ],
        },
        "scoring_weights": {
            "disclaimer": "PROTOTYPE / DEMO CONFIGURATION — Indicative criteria for system validation only, pending official MoTA gazette verification.",
            "configuration_status": "PROTOTYPE",
            "total_max_score": 100.0,
            "scoring_components": [
                {
                    "code": "academic_percentage",
                    "label": "Qualifying Degree Marks (%)",
                    "weight": 35.0,
                    "source_type": "APPLICATION_FORM_FIELD",
                    "field_path": "academic.percentage_marks",
                    "evaluation_type": "PERCENTAGE_NORMALIZED",
                    "max_raw": 100.0,
                },
                {
                    "code": "institution_reputation",
                    "label": "Foreign Institution QS World Ranking Tier",
                    "weight": 35.0,
                    "source_type": "APPLICATION_FORM_FIELD",
                    "field_path": "research.qs_rank",
                    "evaluation_type": "TIER_BRACKETS",
                    "brackets": [
                        {"max_rank": 50, "percentage_of_weight": 100.0, "label": "QS Top 50"},
                        {"max_rank": 100, "percentage_of_weight": 85.0, "label": "QS 51-100"},
                        {"max_rank": 200, "percentage_of_weight": 70.0, "label": "QS 101-200"},
                        {"max_rank": 300, "percentage_of_weight": 55.0, "label": "QS 201-300"},
                        {"max_rank": 500, "percentage_of_weight": 40.0, "label": "QS 301-500"},
                    ],
                    "default_percentage_of_weight": 30.0,
                },
                {
                    "code": "sop_and_interview",
                    "label": "Statement of Purpose & Technical Interview Rating",
                    "weight": 30.0,
                    "source_type": "COMMITTEE_EVALUATION",
                    "max_raw": 100.0,
                },
            ],
            "committee_config": {
                "min_assigned_evaluators": 1,
                "required_quorum": 1,
            },
            "quota_config": {
                "total_slots": 10,
                "waitlist_slots": 3,
            },
            "tie_breaking_order": [
                "ACADEMIC_PERCENTAGE",
                "AGE_SENIORITY",
                "FAMILY_INCOME",
                "SUBMISSION_TIMESTAMP",
            ],
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
    print("MTA Scholarship & Fellowship System - Phase 1 Foundation Database Seed")
    print("=" * 70)

    try:
        # Seed Demo Users
        print("\n[1/2] Checking and seeding Demo Users...")
        for user_data in DEMO_USERS:
            existing = db.query(User).filter(User.email == user_data["email"]).first()
            if existing:
                existing.password_hash = get_password_hash(user_data["password"])
                existing.account_status = UserAccountStatus.ACTIVE
                existing.is_active = True
                db.commit()
                print(f"  -> User '{user_data['email']}' already exists. Updated credentials.")
            else:
                user = User(
                    full_name=user_data["full_name"],
                    email=user_data["email"],
                    phone=user_data["phone"],
                    password_hash=get_password_hash(user_data["password"]),
                    role=user_data["role"],
                    account_status=UserAccountStatus.ACTIVE,
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

        # Remove legacy admin account if present
        legacy_admin = db.query(User).filter(User.email == "admin@demo.gov.in").first()
        if legacy_admin:
            loki_admin = db.query(User).filter(User.email == "loki@gmail.com").first()
            if loki_admin:
                db.query(AuditLog).filter(AuditLog.actor_id == legacy_admin.id).update({"actor_id": loki_admin.id})
            db.delete(legacy_admin)
            db.commit()
            print("  [-] Removed legacy admin@demo.gov.in account")

        # Explicit global assignment for Demo Officer (Phase 4 scope requirement)
        officer_user = db.query(User).filter(User.email == "officer@demo.gov.in").first()
        if officer_user:
            existing_assignment = (
                db.query(OfficerAssignment)
                .filter(OfficerAssignment.officer_id == officer_user.id)
                .first()
            )
            if not existing_assignment:
                global_assign = OfficerAssignment(
                    officer_id=officer_user.id,
                    state=None,
                    scheme_id=None,
                    is_active=True,
                )
                db.add(global_assign)
                db.commit()
                print(f"  [+] Assigned Global Desk Scope to: {officer_user.email}")

        # Explicit global assignment for Demo Committee Member (Phase 6 scope requirement)
        committee_user = db.query(User).filter(User.email == "committee@demo.gov.in").first()
        if committee_user:
            from app.models.committee_assignment import CommitteeAssignment
            existing_comm_assign = (
                db.query(CommitteeAssignment)
                .filter(CommitteeAssignment.user_id == committee_user.id)
                .first()
            )
            if not existing_comm_assign:
                global_comm_assign = CommitteeAssignment(
                    user_id=committee_user.id,
                    scheme_id=None,
                    role_in_committee="CHAIRPERSON",
                    is_active=True,
                )
                db.add(global_comm_assign)
                db.commit()
                print(f"  [+] Assigned Global Committee Scope to: {committee_user.email}")

        # Seed Demo Schemes & SchemeVersion records
        print("\n[2/2] Checking and seeding Demo Schemes & Scheme Versions...")
        for s_data in DEMO_SCHEMES:
            existing_scheme = (
                db.query(Scheme).filter(Scheme.scheme_code == s_data["scheme_code"]).first()
            )
            if existing_scheme:
                print(f"  -> Scheme '{s_data['scheme_code']}' already exists. Updating mirror fields.")
                existing_scheme.eligibility_rules = s_data["eligibility_rules"]
                existing_scheme.form_schema = s_data["form_schema"]
                existing_scheme.required_documents = s_data["required_documents"]
                existing_scheme.scoring_weights = s_data["scoring_weights"]
                db.add(existing_scheme)
                db.commit()
                scheme = existing_scheme
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

            # Ensure authoritative SchemeVersion row exists
            existing_version = (
                db.query(SchemeVersion)
                .filter(
                    SchemeVersion.scheme_code == s_data["scheme_code"],
                    SchemeVersion.scheme_version == s_data["scheme_version"],
                )
                .first()
            )
            if existing_version:
                print(f"  -> SchemeVersion '{s_data['scheme_code']} {s_data['scheme_version']}' already exists. Updating rules.")
                existing_version.eligibility_rules = s_data["eligibility_rules"]
                existing_version.form_schema = s_data["form_schema"]
                existing_version.required_documents = s_data["required_documents"]
                existing_version.scoring_weights = s_data["scoring_weights"]
                db.add(existing_version)
                db.commit()
            else:
                new_version = SchemeVersion(
                    scheme_id=scheme.id,
                    scheme_code=s_data["scheme_code"],
                    scheme_version=s_data["scheme_version"],
                    name=s_data["name"],
                    description=s_data["description"],
                    is_demo=s_data["is_demo"],
                    eligibility_rules=s_data["eligibility_rules"],
                    form_schema=s_data["form_schema"],
                    required_documents=s_data["required_documents"],
                    scoring_weights=s_data["scoring_weights"],
                    is_active=True,
                    is_locked=False,
                )
                db.add(new_version)
                db.commit()
                db.refresh(new_version)
                print(f"  [+] Created SchemeVersion: {new_version.scheme_code} v{new_version.scheme_version}")

        print("\n" + "=" * 70)
        print("SEEDING COMPLETED SUCCESSFULLY")
        print("Demo Credentials (Password for all: Demo@12345):")
        print("  - Applicant: applicant@demo.gov.in")
        print("  - Officer:   officer@demo.gov.in")
        print("  - Committee: committee@demo.gov.in")
        print("  - Admin:     loki@gmail.com")
        print("=" * 70)

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
