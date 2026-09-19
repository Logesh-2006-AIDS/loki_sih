import re
import uuid
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ExtractedField(BaseModel):
    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    raw_text: Optional[str] = None


class OCRExtractionResult(BaseModel):
    document_id: uuid.UUID
    document_type: str
    raw_text: str = ""
    extracted_fields: Dict[str, ExtractedField] = {}
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    is_scanned: bool = False
    error: Optional[str] = None


class BaseOCRService(ABC):
    """
    Architectural abstraction for OCR & document intelligence engines.
    Can be backed by LocalOCRService, Cloud Vision (Google Doc AI, AWS Textract),
    or TestOCRProvider without changing application code.
    """

    @abstractmethod
    def extract_document(
        self,
        document_id: uuid.UUID,
        file_path: Path,
        mime_type: str,
        document_type: str,
    ) -> OCRExtractionResult:
        """
        Extracts raw text and structured fields with confidence scores from the given document.
        """
        pass


class LocalOCRService(BaseOCRService):
    """
    Local OCR implementation supporting:
    1. High-confidence text extraction for digitally generated PDFs via pypdf.
    2. Image / Scanned OCR fallback using pytesseract/PIL when available.
    3. Safe degradation on unreadable files or missing OCR binaries.
    """

    def extract_document(
        self,
        document_id: uuid.UUID,
        file_path: Path,
        mime_type: str,
        document_type: str,
    ) -> OCRExtractionResult:
        if not file_path.exists():
            return OCRExtractionResult(
                document_id=document_id,
                document_type=document_type,
                raw_text="",
                extracted_fields={},
                overall_confidence=0.0,
                error=f"File not found: {file_path}",
            )

        raw_text = ""
        is_scanned = False
        error_msg = None

        try:
            if mime_type == "application/pdf" or file_path.suffix.lower() == ".pdf":
                raw_text, is_scanned = self._extract_pdf_text(file_path)
            elif mime_type.startswith("image/") or file_path.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                raw_text, error_msg = self._extract_image_text(file_path)
                is_scanned = True
            else:
                error_msg = f"Unsupported MIME type for OCR: {mime_type}"
        except Exception as e:
            logger.warning(f"Failed to extract raw text from document {document_id}: {e}")
            error_msg = f"Extraction failed: {str(e)}"

        if error_msg and not raw_text:
            return OCRExtractionResult(
                document_id=document_id,
                document_type=document_type,
                raw_text="",
                extracted_fields={},
                overall_confidence=0.0,
                is_scanned=is_scanned,
                error=error_msg,
            )

        # Parse structured fields from extracted text based on document type
        extracted_fields = self._parse_fields(raw_text, document_type)

        # Compute overall confidence
        if extracted_fields:
            overall_confidence = sum(f.confidence for f in extracted_fields.values()) / len(extracted_fields)
            overall_confidence = round(overall_confidence, 4)
        else:
            overall_confidence = 0.5 if raw_text else 0.0

        return OCRExtractionResult(
            document_id=document_id,
            document_type=document_type,
            raw_text=raw_text,
            extracted_fields=extracted_fields,
            overall_confidence=overall_confidence,
            is_scanned=is_scanned,
            error=error_msg,
        )

    def _extract_pdf_text(self, file_path: Path) -> tuple[str, bool]:
        """
        Extracts embedded text using pypdf.
        Returns (text, is_scanned).
        """
        try:
            import pypdf
            reader = pypdf.PdfReader(str(file_path))
            pages_text = []
            for page in reader.pages:
                t = page.extract_text() or ""
                if t.strip():
                    pages_text.append(t)
            full_text = "\n".join(pages_text).strip()
            if full_text:
                return full_text, False
            # If no selectable text, consider it a scanned PDF
            return "", True
        except Exception as e:
            logger.info(f"pypdf extraction error on {file_path}: {e}")
            return "", True

    def _extract_image_text(self, file_path: Path) -> tuple[str, Optional[str]]:
        """
        Extracts text from images using pytesseract if available.
        Degrades safely if pytesseract / tesseract binary is missing.
        """
        try:
            from PIL import Image
            import pytesseract

            img = Image.open(str(file_path))
            text = pytesseract.image_to_string(img)
            return text.strip(), None
        except ImportError:
            return "", "pytesseract not installed on system"
        except Exception as e:
            # Common case: TesseractNotFoundError when binary is absent
            return "", f"OCR engine unavailable or image unreadable: {type(e).__name__}"

    def _parse_fields(self, text: str, document_type: str) -> Dict[str, ExtractedField]:
        """
        Extracts structured fields using keyword anchor and pattern heuristics.
        Confidence is calculated based on anchor proximity, regex strength, and format validity.
        """
        if not text:
            return {}

        fields: Dict[str, ExtractedField] = {}
        upper_text = text.upper()
        clean_text = re.sub(r"\s+", " ", text).strip()

        # 1. Full Name extraction (common across almost all certificates)
        name_match = re.search(
            r"(?:this is to certify that|name\s*(?:of\s*applicant)?\s*[:\-]|candidate\s*name\s*[:\-]|certify that\s*(?:shri|smt|kumari|mr|ms)?)\s*([A-Za-z\s\.]{3,40})",
            clean_text,
            re.IGNORECASE,
        )
        if name_match:
            candidate_name = name_match.group(1).strip()
            # Clean trailing words like son/daughter of
            candidate_name = re.split(r"\b(s/o|d/o|w/o|son of|daughter of|resident of)\b", candidate_name, flags=re.IGNORECASE)[0].strip()
            if len(candidate_name) >= 3:
                fields["full_name"] = ExtractedField(
                    value=candidate_name,
                    confidence=0.88,
                    raw_text=name_match.group(0),
                )

        doc_type_upper = document_type.upper()

        # 2. Income Certificate
        if "INCOME" in doc_type_upper:
            # Match currency values: e.g. Rs. 2,50,000 or ₹ 250000 or 2.5 Lakh
            income_patterns = [
                r"(?:annual\s*family\s*income|annual\s*income|total\s*income|income\s*from\s*all\s*sources)\s*(?:is|amounting\s*to)?\s*[:\-]?\s*(?:rs\.?|₹|inr)?\s*([0-9,]+(?:\.[0-9]{2})?)",
                r"(?:rs\.?|₹|inr)\s*([0-9,]{4,10})",
                r"([0-9,]{4,10})\s*(?:rupees|only)",
                r"([0-9]+(?:\.[0-9]+)?)\s*(?:lakh|lac|lakhs)",
            ]
            for pat in income_patterns:
                m = re.search(pat, clean_text, re.IGNORECASE)
                if m:
                    val_str = m.group(1).replace(",", "")
                    if "lakh" in m.group(0).lower() or "lac" in m.group(0).lower():
                        try:
                            val_float = float(val_str) * 100000
                            fields["annual_family_income"] = ExtractedField(
                                value=str(int(val_float)),
                                confidence=0.92,
                                raw_text=m.group(0),
                            )
                            break
                        except ValueError:
                            pass
                    else:
                        try:
                            val_int = int(float(val_str))
                            # Realistic annual income ranges
                            if 10000 <= val_int <= 100000000:
                                fields["annual_family_income"] = ExtractedField(
                                    value=str(val_int),
                                    confidence=0.90,
                                    raw_text=m.group(0),
                                )
                                break
                        except ValueError:
                            pass

            # Certificate Number
            cert_m = re.search(r"(?:certificate\s*no\.?|cert\s*no\.?|application\s*no\.?)\s*[:\-]?\s*([A-Za-z0-9\/\-_]{5,25})", clean_text, re.IGNORECASE)
            if cert_m:
                fields["certificate_number"] = ExtractedField(
                    value=cert_m.group(1).strip(),
                    confidence=0.85,
                    raw_text=cert_m.group(0),
                )

        # 3. Caste / Community Certificate
        elif "CASTE" in doc_type_upper or "COMMUNITY" in doc_type_upper:
            # Check for ST community identifiers
            if re.search(r"\b(SCHEDULED\s*TRIBE|S\.T\.|ST\s*CATEGORY)\b", upper_text):
                fields["community"] = ExtractedField(
                    value="ST",
                    confidence=0.95,
                    raw_text="Scheduled Tribe (ST)",
                )
            elif re.search(r"\b(SCHEDULED\s*CASTE|S\.C\.|SC\s*CATEGORY)\b", upper_text):
                fields["community"] = ExtractedField(
                    value="SC",
                    confidence=0.95,
                    raw_text="Scheduled Caste (SC)",
                )
            elif re.search(r"\b(OTHER\s*BACKWARD\s*CLASS|OBC)\b", upper_text):
                fields["community"] = ExtractedField(
                    value="OBC",
                    confidence=0.95,
                    raw_text="Other Backward Class (OBC)",
                )

        # 4. Marksheet / Academic Records
        elif "MARKSHEET" in doc_type_upper or "DEGREE" in doc_type_upper:
            pct_m = re.search(r"(?:percentage|aggregate|marks\s*obtained|score|final\s*marks|percentage\s*of\s*marks)\s*[:\-]?\s*([0-9]{1,3}(?:\.[0-9]{1,2})?)\s*%", clean_text, re.IGNORECASE)
            if not pct_m:
                pct_m = re.search(r"\b([4-9][0-9]\.[0-9]{1,2})\s*%", clean_text)
            if pct_m:
                try:
                    pct_val = float(pct_m.group(1))
                    if 0.0 <= pct_val <= 100.0:
                        fields["percentage_marks"] = ExtractedField(
                            value=str(pct_val),
                            confidence=0.90,
                            raw_text=pct_m.group(0),
                        )
                except ValueError:
                    pass

        # 5. Passport / Identity Document
        elif "PASSPORT" in doc_type_upper or "IDENTITY" in doc_type_upper:
            # Date of Birth
            dob_m = re.search(r"(?:date\s*of\s*birth|dob|birth\s*date)\s*[:\-]?\s*([0-9]{1,2}[/\-\.][0-9]{1,2}[/\-\.][0-9]{2,4})", clean_text, re.IGNORECASE)
            if dob_m:
                fields["dob"] = ExtractedField(
                    value=dob_m.group(1).strip(),
                    confidence=0.88,
                    raw_text=dob_m.group(0),
                )

        # 6. Admission / University Letter
        elif "ADMISSION" in doc_type_upper or "OFFER" in doc_type_upper:
            uni_m = re.search(r"(?:university|institute|admitted\s*to|college)\s*[:\-]?\s*([A-Za-z\s]{5,50})", clean_text, re.IGNORECASE)
            if uni_m:
                fields["university_name"] = ExtractedField(
                    value=uni_m.group(1).strip(),
                    confidence=0.80,
                    raw_text=uni_m.group(0),
                )

        return fields
