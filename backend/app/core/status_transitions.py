from typing import Dict, Set
from app.core.enums import ApplicationStatus, DocumentStatus, FellowshipStatus, DisbursementStatus


LEGAL_APPLICATION_TRANSITIONS: Dict[ApplicationStatus, Set[ApplicationStatus]] = {
    ApplicationStatus.DRAFT: {
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.UNDER_AI_VERIFICATION,
    },
    ApplicationStatus.SUBMITTED: {
        ApplicationStatus.UNDER_AI_VERIFICATION,
        ApplicationStatus.UNDER_MANUAL_REVIEW,
        ApplicationStatus.DEFICIENT,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.UNDER_AI_VERIFICATION: {
        ApplicationStatus.UNDER_MANUAL_REVIEW,
        ApplicationStatus.DEFICIENT,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.DEFICIENT: {
        ApplicationStatus.RESUBMITTED,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.RESUBMITTED: {
        ApplicationStatus.UNDER_AI_VERIFICATION,
        ApplicationStatus.UNDER_MANUAL_REVIEW,
        ApplicationStatus.DEFICIENT,
    },
    ApplicationStatus.UNDER_MANUAL_REVIEW: {
        ApplicationStatus.VERIFIED,
        ApplicationStatus.DEFICIENT,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.VERIFIED: {
        ApplicationStatus.MERIT_RANKED,
    },
    ApplicationStatus.SHORTLISTED: {
        ApplicationStatus.MERIT_RANKED,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.MERIT_RANKED: {
        ApplicationStatus.SELECTED,
        ApplicationStatus.WAITLISTED,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.SELECTED: {
        ApplicationStatus.FELLOWSHIP_ACTIVE,
    },
    ApplicationStatus.WAITLISTED: {
        ApplicationStatus.SELECTED,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.REJECTED: set(),
    ApplicationStatus.FELLOWSHIP_ACTIVE: set(),
}

LEGAL_DOCUMENT_TRANSITIONS: Dict[DocumentStatus, Set[DocumentStatus]] = {
    DocumentStatus.PENDING: {
        DocumentStatus.UPLOADED,
        DocumentStatus.PROCESSING,
        DocumentStatus.VERIFIED,
        DocumentStatus.FLAGGED,
        DocumentStatus.REJECTED,
    },
    DocumentStatus.UPLOADED: {
        DocumentStatus.PENDING,
        DocumentStatus.PROCESSING,
        DocumentStatus.VERIFIED,
        DocumentStatus.FLAGGED,
        DocumentStatus.REJECTED,
        DocumentStatus.RESUBMISSION_REQUIRED,
    },
    DocumentStatus.PROCESSING: {
        DocumentStatus.VERIFIED,
        DocumentStatus.FLAGGED,
        DocumentStatus.REJECTED,
        DocumentStatus.RESUBMISSION_REQUIRED,
    },
    DocumentStatus.FLAGGED: {
        DocumentStatus.VERIFIED,
        DocumentStatus.REJECTED,
        DocumentStatus.RESUBMISSION_REQUIRED,
    },
    DocumentStatus.RESUBMISSION_REQUIRED: {
        DocumentStatus.PENDING,
        DocumentStatus.PROCESSING,
        DocumentStatus.VERIFIED,
        DocumentStatus.REJECTED,
    },
    DocumentStatus.VERIFIED: {
        DocumentStatus.FLAGGED,
        DocumentStatus.RESUBMISSION_REQUIRED,
        DocumentStatus.REJECTED,
    },
    DocumentStatus.REJECTED: {
        DocumentStatus.VERIFIED,
        DocumentStatus.RESUBMISSION_REQUIRED,
    },
}


def can_transition_application(
    current: ApplicationStatus, next_status: ApplicationStatus
) -> bool:
    if current == next_status:
        return True
    return next_status in LEGAL_APPLICATION_TRANSITIONS.get(current, set())


def can_transition_document(
    current: DocumentStatus, next_status: DocumentStatus
) -> bool:
    if current == next_status:
        return True
    return next_status in LEGAL_DOCUMENT_TRANSITIONS.get(current, set())


LEGAL_FELLOWSHIP_TRANSITIONS: Dict[FellowshipStatus, Set[FellowshipStatus]] = {
    FellowshipStatus.ACTIVE: {
        FellowshipStatus.UNDER_RENEWAL,
        FellowshipStatus.SUSPENDED,
        FellowshipStatus.COMPLETED,
        FellowshipStatus.TERMINATED,
    },
    FellowshipStatus.UNDER_RENEWAL: {
        FellowshipStatus.ACTIVE,       # Renewal approved -> current_year advances
        FellowshipStatus.SUSPENDED,    # Suspended due to deficiency timeout/failure
        FellowshipStatus.TERMINATED,   # Forfeited or disqualified
    },
    FellowshipStatus.SUSPENDED: {
        FellowshipStatus.ACTIVE,       # Reinstated strictly by ADMIN
        FellowshipStatus.TERMINATED,   # Permanent revocation
    },
    FellowshipStatus.COMPLETED: set(), # Terminal
    FellowshipStatus.TERMINATED: set(),# Terminal
}


def can_transition_fellowship(
    current: FellowshipStatus, next_status: FellowshipStatus
) -> bool:
    if current == next_status:
        return True
    return next_status in LEGAL_FELLOWSHIP_TRANSITIONS.get(current, set())


LEGAL_DISBURSEMENT_TRANSITIONS: Dict[DisbursementStatus, Set[DisbursementStatus]] = {
    DisbursementStatus.SCHEDULED: {
        DisbursementStatus.PENDING_APPROVAL,
        DisbursementStatus.APPROVED_FOR_PAYMENT,
        DisbursementStatus.CANCELLED,
    },
    DisbursementStatus.PENDING_APPROVAL: {
        DisbursementStatus.APPROVED_FOR_PAYMENT,
        DisbursementStatus.CANCELLED,
    },
    DisbursementStatus.APPROVED_FOR_PAYMENT: {
        DisbursementStatus.PROCESSING,
        DisbursementStatus.CANCELLED,
    },
    DisbursementStatus.PROCESSING: {
        DisbursementStatus.SUCCESS,
        DisbursementStatus.FAILED,
    },
    DisbursementStatus.FAILED: {
        DisbursementStatus.PROCESSING,       # Retry dispatch (retry_count < 3)
        DisbursementStatus.RETRY_EXHAUSTED,  # When retry limit (3/3) reached
    },
    DisbursementStatus.SUCCESS: set(),         # Terminal ledger entry
    DisbursementStatus.CANCELLED: set(),       # Terminal
    DisbursementStatus.RETRY_EXHAUSTED: set(), # Terminal administrative lock
}


def can_transition_disbursement(
    current: DisbursementStatus, next_status: DisbursementStatus
) -> bool:
    if current == next_status:
        return True
    return next_status in LEGAL_DISBURSEMENT_TRANSITIONS.get(current, set())
