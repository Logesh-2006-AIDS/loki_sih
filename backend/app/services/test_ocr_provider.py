import uuid
from pathlib import Path
from typing import Any, Dict, Optional
from app.services.ocr_service import (
    BaseOCRService,
    ExtractedField,
    OCRExtractionResult,
    LocalOCRService,
)


class TestOCRProvider(BaseOCRService):
    """
    Deterministic OCR provider for unit tests and CI.
    Allows injecting exact extraction results, simulated field values,
    mismatches, low confidence scores, or OCR failures.
    """
    __test__ = False

    def __init__(self, fallback_to_local: bool = True):

        self.fallback_to_local = fallback_to_local
        self._mock_results: Dict[uuid.UUID, OCRExtractionResult] = {}
        self._mock_by_type: Dict[str, Dict[str, Any]] = {}
        self._simulated_error: Optional[str] = None
        self._local_ocr = LocalOCRService() if fallback_to_local else None

    def set_mock_result(self, document_id: uuid.UUID, result: OCRExtractionResult):
        self._mock_results[document_id] = result

    def set_mock_type_fields(self, document_type: str, fields: Dict[str, Any]):
        """
        Configure default field values for a document type.
        fields format: { "field_name": (value, confidence) } or { "field_name": value }
        """
        self._mock_by_type[document_type.upper()] = fields

    def simulate_failure(self, error_message: str):
        self._simulated_error = error_message

    def clear_mocks(self):
        self._mock_results.clear()
        self._mock_by_type.clear()
        self._simulated_error = None

    def extract_document(
        self,
        document_id: uuid.UUID,
        file_path: Path,
        mime_type: str,
        document_type: str,
    ) -> OCRExtractionResult:
        if self._simulated_error:
            return OCRExtractionResult(
                document_id=document_id,
                document_type=document_type,
                raw_text="",
                extracted_fields={},
                overall_confidence=0.0,
                error=self._simulated_error,
            )

        # 1. Check if an explicit mock result was registered for this document ID
        if document_id in self._mock_results:
            return self._mock_results[document_id]

        # 2. Check if mock fields were registered for this document type
        doc_type_upper = document_type.upper()
        if doc_type_upper in self._mock_by_type:
            raw_fields = self._mock_by_type[doc_type_upper]
            extracted_fields: Dict[str, ExtractedField] = {}
            for k, v in raw_fields.items():
                if isinstance(v, tuple) and len(v) == 2:
                    val, conf = v
                else:
                    val, conf = v, 0.95
                extracted_fields[k] = ExtractedField(value=val, confidence=float(conf))

            overall_conf = (
                sum(f.confidence for f in extracted_fields.values()) / len(extracted_fields)
                if extracted_fields
                else 0.9
            )
            return OCRExtractionResult(
                document_id=document_id,
                document_type=document_type,
                raw_text="[Simulated OCR Text from TestOCRProvider]",
                extracted_fields=extracted_fields,
                overall_confidence=round(overall_conf, 4),
            )

        # 3. Fallback to LocalOCRService if enabled and file exists
        if self.fallback_to_local and self._local_ocr and file_path.exists():
            return self._local_ocr.extract_document(
                document_id=document_id,
                file_path=file_path,
                mime_type=mime_type,
                document_type=document_type,
            )

        # 4. Default empty result
        return OCRExtractionResult(
            document_id=document_id,
            document_type=document_type,
            raw_text="",
            extracted_fields={},
            overall_confidence=0.0,
            error="No mock configured and local file unavailable",
        )
