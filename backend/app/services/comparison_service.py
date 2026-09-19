import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from app.services.ocr_service import ExtractedField


class DocumentComparisonService:
    """
    Schema-driven normalization and comparison engine.
    Cross-references extracted document values against applicant form data.
    """

    @staticmethod
    def normalize_name(name: Optional[str]) -> str:
        if not name:
            return ""
        text = str(name).lower().strip()
        # Remove common Indian titles/salutations
        salutations = [
            r"\bshri\b",
            r"\bsmt\b",
            r"\bkumari\b",
            r"\bkm\b",
            r"\bmr\b",
            r"\bmrs\b",
            r"\bms\b",
            r"\bdr\b",
            r"\bprof\b",
        ]
        for sal in salutations:
            text = re.sub(sal, "", text, flags=re.IGNORECASE)
        # Remove dots (e.g. Ph.D. -> phd, S. -> s) without introducing spaces
        text = text.replace(".", "")
        # Remove other punctuation
        text = re.sub(r"[^\w\s]", " ", text)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def normalize_currency(val: Any) -> Optional[float]:
        if val is None:
            return None
        text = str(val).lower().strip()
        # Handle lakh representations (e.g. 2.5 lakh, 6 lac)
        lakh_m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:lakh|lac|lakhs)", text)
        if lakh_m:
            try:
                return float(lakh_m.group(1)) * 100000.0
            except ValueError:
                pass

        # Strip currency symbols and formatting without destroying decimal point
        clean = re.sub(r"[₹/]", "", text)
        clean = re.sub(r"\b(rs\.?|inr)\b", "", clean, flags=re.IGNORECASE)
        clean = clean.replace(",", "").strip()
        try:
            return float(clean)
        except ValueError:
            # Try finding first numeric group
            num_m = re.search(r"([0-9]+(?:\.[0-9]+)?)", clean)
            if num_m:
                try:
                    return float(num_m.group(1))
                except ValueError:
                    pass
            return None


    @staticmethod
    def normalize_date(val: Any) -> Optional[str]:
        if not val:
            return None
        text = str(val).strip()
        # Try various formats
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d.%m.%Y",
            "%d/%m/%y",
            "%d-%m-%y",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(text, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    @staticmethod
    def normalize_percentage(val: Any) -> Optional[float]:
        if val is None:
            return None
        clean = str(val).replace("%", "").strip()
        try:
            return float(clean)
        except ValueError:
            return None

    @staticmethod
    def normalize_text(val: Any) -> str:
        if val is None:
            return ""
        text = str(val).lower().strip()
        text = re.sub(r"[^\w\s]", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def compare_document_fields(
        self,
        application_form_data: Dict[str, Any],
        extracted_fields: Dict[str, ExtractedField],
        verification_fields: List[Dict[str, Any]],
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]], bool]:
        """
        Compares extracted fields with application form data based on configured verification fields.

        Returns:
            - comparison_results: Dict mapping field names to match details
            - flags: List of flags (discrepancies, missing fields, or low confidence)
            - is_verified: True if all required verification fields match with high confidence and zero flags
        """
        comparison_results: Dict[str, Any] = {}
        flags: List[Dict[str, Any]] = []

        if not verification_fields:
            # Default fallback: if no verification_fields configured, return neutral state
            return comparison_results, flags, True

        has_mismatch = False
        all_required_matched = True

        for rule in verification_fields:
            doc_field = rule.get("document_field")
            app_field = rule.get("application_field") or doc_field
            comp_type = rule.get("comparison", "text").lower()
            label = rule.get("label", doc_field)
            is_required = rule.get("required", True)

            app_val = application_form_data.get(app_field)
            extracted_obj = extracted_fields.get(doc_field)

            # 1. Check if extracted field exists
            if not extracted_obj or extracted_obj.value is None or str(extracted_obj.value).strip() == "":
                if is_required:
                    all_required_matched = False
                    flags.append({
                        "field": doc_field,
                        "label": label,
                        "application_value": str(app_val) if app_val is not None else None,
                        "document_value": None,
                        "reason": f"Required verification field '{label}' could not be identified in the document",
                        "severity": "MEDIUM",
                    })
                    comparison_results[doc_field] = {
                        "status": "UNCLEAR",
                        "label": label,
                        "application_value": app_val,
                        "document_value": None,
                        "confidence": 0.0,
                    }
                continue

            doc_val = extracted_obj.value
            confidence = extracted_obj.confidence

            # 2. Perform comparison based on type
            match_status = "MATCH"
            reason = None

            if comp_type == "currency":
                norm_app = self.normalize_currency(app_val)
                norm_doc = self.normalize_currency(doc_val)
                if norm_app is not None and norm_doc is not None:
                    if abs(norm_app - norm_doc) < 1.0:
                        match_status = "MATCH"
                    else:
                        match_status = "MISMATCH"
                        reason = f"Annual income on document (₹{norm_doc:,.0f}) does not match application value (₹{norm_app:,.0f})"
                else:
                    match_status = "UNCLEAR"
                    reason = f"Could not parse numeric income amount from document ('{doc_val}')"

            elif comp_type == "name":
                norm_app = self.normalize_name(app_val)
                norm_doc = self.normalize_name(doc_val)
                if norm_app and norm_doc:
                    # Token subset matching for Indian names (e.g. Ramesh Meena in Ramesh Chandra Meena)
                    app_tokens = set(norm_app.split())
                    doc_tokens = set(norm_doc.split())
                    if norm_app == norm_doc or norm_app in norm_doc or norm_doc in norm_app or (len(app_tokens & doc_tokens) >= 2):
                        match_status = "MATCH"
                    else:
                        match_status = "MISMATCH"
                        reason = f"Name on document ('{doc_val}') does not match applicant name ('{app_val}')"
                else:
                    match_status = "UNCLEAR"
                    reason = "Name could not be normalized for comparison"

            elif comp_type == "date":
                norm_app = self.normalize_date(app_val)
                norm_doc = self.normalize_date(doc_val)
                if norm_app and norm_doc:
                    if norm_app == norm_doc:
                        match_status = "MATCH"
                    else:
                        match_status = "MISMATCH"
                        reason = f"Date on document ('{doc_val}') does not match application date ('{app_val}')"
                else:
                    match_status = "UNCLEAR"
                    reason = "Date could not be normalized for comparison"

            elif comp_type == "percentage":
                norm_app = self.normalize_percentage(app_val)
                norm_doc = self.normalize_percentage(doc_val)
                if norm_app is not None and norm_doc is not None:
                    if abs(norm_app - norm_doc) <= 0.5:
                        match_status = "MATCH"
                    else:
                        match_status = "MISMATCH"
                        reason = f"Marks percentage on document ({norm_doc}%) does not match application ({norm_app}%)"
                else:
                    match_status = "UNCLEAR"
                    reason = "Percentage marks could not be parsed from document"

            else:  # General text comparison
                norm_app = self.normalize_text(app_val)
                norm_doc = self.normalize_text(doc_val)
                if norm_app and norm_doc:
                    if norm_app == norm_doc or norm_app in norm_doc or norm_doc in norm_app:
                        match_status = "MATCH"
                    else:
                        match_status = "MISMATCH"
                        reason = f"{label} on document ('{doc_val}') does not match application ('{app_val}')"
                else:
                    match_status = "UNCLEAR"
                    reason = f"{label} could not be compared"

            # 3. Handle low confidence
            if match_status == "MATCH" and confidence < 0.70:
                match_status = "UNCLEAR"
                reason = f"Low extraction confidence ({int(confidence * 100)}%) on {label}"

            # 4. Record comparison result and flags
            comparison_results[doc_field] = {
                "status": match_status,
                "label": label,
                "application_value": app_val,
                "document_value": doc_val,
                "confidence": round(confidence, 4),
                "reason": reason,
            }

            if match_status == "MISMATCH":
                has_mismatch = True
                flags.append({
                    "field": doc_field,
                    "label": label,
                    "application_value": str(app_val),
                    "document_value": str(doc_val),
                    "reason": reason,
                    "severity": "HIGH",
                })
            elif match_status == "UNCLEAR":
                flags.append({
                    "field": doc_field,
                    "label": label,
                    "application_value": str(app_val) if app_val is not None else None,
                    "document_value": str(doc_val),
                    "reason": reason,
                    "severity": "MEDIUM",
                })

        is_verified = (
            not has_mismatch
            and all_required_matched
            and len(flags) == 0
            and len(comparison_results) > 0
        )


        return comparison_results, flags, is_verified
