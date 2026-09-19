"""
AI Service Architectural Contracts & Interfaces
Ministry of Tribal Affairs - Scholarship & Fellowship Management System

Phase 0 Architectural Foundation for Phase 1+ AI/OCR integration.
Defines formal Abstract Base Classes (ABC) and Pydantic models for:
  - Document OCR & Text Extraction
  - Entity & Field Identification
  - Tampering & Authenticity Verification
  - Cross-Verification with Application Form Data
  - Automated Scheme Rules Evaluation
"""

import uuid
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    CASTE_CERTIFICATE = "CASTE_CERTIFICATE"
    INCOME_CERTIFICATE = "INCOME_CERTIFICATE"
    DEGREE_CERTIFICATE = "DEGREE_CERTIFICATE"
    PG_MARKSHEET = "PG_MARKSHEET"
    ADMISSION_LETTER = "ADMISSION_LETTER"
    PASSPORT = "PASSPORT"
    AADHAAR_CARD = "AADHAAR_CARD"
    OTHER = "OTHER"


class BoundingBox(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class ExtractedField(BaseModel):
    field_name: str
    field_value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    bounding_box: Optional[BoundingBox] = None


class ExtractionResult(BaseModel):
    document_id: uuid.UUID
    document_type: DocumentType
    raw_text: str
    fields: Dict[str, ExtractedField]
    overall_confidence: float = Field(ge=0.0, le=1.0)
    detected_language: str = "en"
    page_count: int = 1


class DocumentIntegrityCheck(BaseModel):
    is_tampered: bool
    tamper_score: float = Field(ge=0.0, le=1.0)
    detected_anomalies: List[str] = []
    qr_barcode_verified: Optional[bool] = None


class VerificationMismatch(BaseModel):
    field_name: str
    form_value: Any
    extracted_value: Any
    severity: str  # "CRITICAL", "WARNING", "INFO"
    notes: Optional[str] = None


class DocumentVerificationReport(BaseModel):
    document_id: uuid.UUID
    application_id: uuid.UUID
    is_verified: bool
    confidence: float
    matched_fields: List[str]
    mismatched_fields: List[VerificationMismatch]
    integrity: DocumentIntegrityCheck
    recommended_status: str  # "VERIFIED", "FLAGGED", "RESUBMISSION_REQUIRED"


class RuleEvaluationOutcome(BaseModel):
    rule_name: str
    is_satisfied: bool
    expected_criteria: Any
    actual_value: Any
    failure_reason: Optional[str] = None


class EligibilityEvaluationReport(BaseModel):
    application_id: uuid.UUID
    scheme_code: str
    is_eligible: bool
    outcomes: List[RuleEvaluationOutcome]
    deficiency_flags: List[str] = []
    merit_input_attributes: Dict[str, Any] = {}


# =====================================================================
# Abstract Base Classes (Contracts to be implemented in Phase 1+)
# =====================================================================


class BaseDocumentExtractor(ABC):
    """
    Contract for extracting unstructured text and key-value entities
    from official certificates and government documents.
    """

    @abstractmethod
    def extract(
        self,
        document_id: uuid.UUID,
        file_path: Path,
        expected_type: DocumentType,
    ) -> ExtractionResult:
        """
        Executes OCR engine (e.g. PaddleOCR / Tesseract / Vision model)
        and extracts key-value entities corresponding to the document schema.
        """
        pass


class BaseDocumentVerifier(ABC):
    """
    Contract for cross-verifying extracted document entities against
    the submitted application form and assessing document tampering.
    """

    @abstractmethod
    def verify(
        self,
        application_id: uuid.UUID,
        form_data: Dict[str, Any],
        extraction: ExtractionResult,
    ) -> DocumentVerificationReport:
        """
        Validates whether extracted entities match applicant-provided details
        and checks document visual integrity.
        """
        pass


class BaseEligibilityEvaluator(ABC):
    """
    Contract for evaluating scheme eligibility rules against verified
    candidate data.
    """

    @abstractmethod
    def evaluate(
        self,
        application_id: uuid.UUID,
        scheme_rules: Dict[str, Any],
        form_data: Dict[str, Any],
        verification_reports: List[DocumentVerificationReport],
    ) -> EligibilityEvaluationReport:
        """
        Applies parameterized rule criteria (e.g. ST community status,
        income ceiling, qualifying score thresholds, age limits).
        """
        pass
