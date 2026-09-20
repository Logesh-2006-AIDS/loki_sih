from typing import Dict, Set
from app.core.enums import ApplicationStatus, DocumentStatus


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
        ApplicationStatus.SHORTLISTED,
        ApplicationStatus.MERIT_RANKED,
        ApplicationStatus.REJECTED,
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
