# AI & OCR Service Interface (Phase 0 Architectural Foundation)

This package defines the formal architectural contracts, data types, and interfaces for the AI, OCR, and Document Verification pipelines of the **Ministry of Tribal Affairs Scholarship & Fellowship Management System**.

## Scope & Strategy

In **Phase 0**, this directory establishes the decoupled integration contract:
- **No Mock / Fake Logic**: Instead of placeholder or stubbed simulated responses, strict abstract base classes (`BaseDocumentExtractor`, `BaseDocumentVerifier`, `BaseEligibilityEvaluator`) and Pydantic validation models define the input/output protocol.
- **Phase 1+ Implementation**: The concrete implementation will leverage OCR engines (PaddleOCR, Tesseract, or Vision Transformers) to extract text, bounding boxes, and metadata from tribal certificates, marksheets, and passport records.
- **Decoupled Architecture**: The backend interacts with these components via standard Python interfaces or gRPC/REST microservice endpoints, enabling independent scaling and model updates without touching core transactional logic.

## Key Contracts (`interface.py`)

1. **`ExtractionResult`**: Captures raw text, localized bounding boxes, identified key-value pairs, language, and confidence metrics.
2. **`DocumentVerificationReport`**: Details matched fields, field mismatches, tamper detection scores, and recommended verification status (`VERIFIED`, `FLAGGED`, `RESUBMISSION_REQUIRED`).
3. **`EligibilityEvaluationReport`**: Parameterized outcome evaluating scheme-specific criteria (income, ST caste validation, educational scores, age ceilings) against verified application data.
