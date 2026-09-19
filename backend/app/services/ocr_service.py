from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional
import uuid
from pydantic import BaseModel


class OCRExtractionResult(BaseModel):
    document_id: uuid.UUID
    document_type: str
    raw_text: Optional[str] = None
    extracted_fields: Dict[str, Any] = {}
    confidence_score: float = 0.0
    status: str = "PENDING"


class BaseOCRService(ABC):
    """
    Architectural interface defining the contract for AI/OCR extraction
    services to be implemented in Phase 1+.
    """

    @abstractmethod
    def extract_document(
        self, document_id: uuid.UUID, file_path: Path, document_type: str
    ) -> OCRExtractionResult:
        """
        Extracts structured fields and raw text from the specified document.
        """
        pass

    @abstractmethod
    def verify_against_application(
        self,
        extraction: OCRExtractionResult,
        application_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Compares extracted document entities against applicant form data.
        """
        pass


class OCRService(BaseOCRService):
    """
    Phase 0 architectural interface stub.
    Actual OCR pipeline (PaddleOCR/Tesseract/Vision AI) is integrated in Phase 1.
    """

    def extract_document(
        self, document_id: uuid.UUID, file_path: Path, document_type: str
    ) -> OCRExtractionResult:
        raise NotImplementedError(
            "AI/OCR extraction service is scheduled for Phase 1 implementation."
        )

    def verify_against_application(
        self,
        extraction: OCRExtractionResult,
        application_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        raise NotImplementedError(
            "Document cross-verification engine is scheduled for Phase 1 implementation."
        )
