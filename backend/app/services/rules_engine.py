import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RuleCheckDetail(BaseModel):
    rule: str
    label: str
    operator: str
    expected: Any
    actual: Any
    passed: bool
    message: str


class EligibilityEvaluationResult(BaseModel):
    eligible: bool
    summary_message: str
    disclaimer: str = (
        "Self-check is indicative only. Final eligibility is subject to "
        "document verification and official scrutiny."
    )
    is_demo: bool = True
    checks: List[RuleCheckDetail] = Field(default_factory=list)


class RulesEngine:
    """
    Deterministic, configuration-driven eligibility evaluation engine.
    Supports operators:
      - equals (eq, ==)
      - not_equals (ne, !=)
      - greater_than (gt, >)
      - greater_than_or_equal (gte, >=)
      - less_than (lt, <)
      - less_than_or_equal (lte, <=)
      - in (contains, is_in)
      - required (exists)

    Strictly deterministic: Zero LLM, zero OCR, zero AI decision-making.
    """

    SUPPORTED_OPERATORS = {
        "equals", "eq", "==",
        "not_equals", "ne", "!=",
        "greater_than", "gt", ">",
        "greater_than_or_equal", "gte", ">=",
        "less_than", "lt", "<",
        "less_than_or_equal", "lte", "<=",
        "in", "contains", "is_in",
        "required", "exists",
    }

    @classmethod
    def evaluate(
        cls,
        eligibility_rules: Dict[str, Any],
        applicant_answers: Dict[str, Any],
        is_demo: bool = True,
    ) -> EligibilityEvaluationResult:
        """
        Evaluates applicant inputs against configured scheme rules.
        Does not mutate or persist any application data.
        """
        normalized_rules = cls._normalize_rules(eligibility_rules)
        checks: List[RuleCheckDetail] = []
        all_passed = True

        for rule in normalized_rules:
            check = cls._evaluate_single_rule(rule, applicant_answers)
            checks.append(check)
            if not check.passed:
                all_passed = False

        if all_passed and checks:
            summary = "Based on the information provided, you appear to meet the configured criteria."
        elif not checks:
            summary = "No eligibility rules configured for this scheme version."
        else:
            summary = "Based on the information provided, you may not meet one or more configured criteria."

        return EligibilityEvaluationResult(
            eligible=all_passed if checks else True,
            summary_message=summary,
            disclaimer=(
                "Self-check is indicative only. Final eligibility is subject to "
                "document verification and official scrutiny."
            ),
            is_demo=is_demo,
            checks=checks,
        )

    @classmethod
    def _normalize_rules(cls, rules_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Converts either explicit 'rules' list or legacy key-value dictionary into
        a standardized list of rule specifications.
        """
        if not rules_config:
            return []

        # If explicit rules list exists, validate and return
        if "rules" in rules_config and isinstance(rules_config["rules"], list):
            valid_rules = []
            for r in rules_config["rules"]:
                if isinstance(r, dict) and "field" in r and "operator" in r:
                    valid_rules.append(r)
                else:
                    # Malformed rule handled safely
                    valid_rules.append({
                        "field": str(r.get("field", "unknown")) if isinstance(r, dict) else "unknown",
                        "operator": "invalid",
                        "value": None,
                        "label": "Invalid Rule Definition",
                        "fail_message": "Rule configuration is invalid or unsupported.",
                    })
            return valid_rules

        # Otherwise synthesize from known legacy key-value dictionary
        synthesized: List[Dict[str, Any]] = []
        for key, val in rules_config.items():
            if key in {"disclaimer", "rules", "notes", "description"}:
                continue

            if key in {"community", "category", "caste"}:
                synthesized.append({
                    "field": key,
                    "operator": "equals",
                    "value": str(val),
                    "label": "Community / Category",
                    "pass_message": f"Community criterion satisfied ({val}).",
                    "fail_message": f"Must belong to {val} community.",
                })
            elif "min_" in key or "minimum_" in key or "marks" in key or "percentage" in key:
                label = key.replace("_", " ").title()
                synthesized.append({
                    "field": key,
                    "operator": "greater_than_or_equal",
                    "value": float(val) if isinstance(val, (int, float, str)) and str(val).replace(".", "", 1).isdigit() else val,
                    "label": label,
                    "pass_message": f"{label} requirement satisfied (>= {val}).",
                    "fail_message": f"{label} must be at least {val}.",
                })
            elif "max_" in key or "ceiling" in key or "income" in key or "age" in key:
                label = key.replace("_", " ").title()
                synthesized.append({
                    "field": key,
                    "operator": "less_than_or_equal",
                    "value": float(val) if isinstance(val, (int, float, str)) and str(val).replace(".", "", 1).isdigit() else val,
                    "label": label,
                    "pass_message": f"{label} requirement satisfied (<= {val}).",
                    "fail_message": f"{label} must not exceed {val}.",
                })
            elif isinstance(val, list):
                label = key.replace("_", " ").title()
                synthesized.append({
                    "field": key,
                    "operator": "in",
                    "value": val,
                    "label": label,
                    "pass_message": f"{label} is an eligible option.",
                    "fail_message": f"{label} must be one of: {', '.join(str(v) for v in val)}.",
                })
            elif isinstance(val, bool):
                label = key.replace("_", " ").title()
                synthesized.append({
                    "field": key,
                    "operator": "equals",
                    "value": val,
                    "label": label,
                    "pass_message": f"{label} requirement met.",
                    "fail_message": f"{label} requirement must be {val}.",
                })
            else:
                label = key.replace("_", " ").title()
                synthesized.append({
                    "field": key,
                    "operator": "equals",
                    "value": val,
                    "label": label,
                    "pass_message": f"{label} requirement satisfied.",
                    "fail_message": f"{label} does not match required condition.",
                })

        return synthesized

    @classmethod
    def _evaluate_single_rule(
        cls, rule: Dict[str, Any], answers: Dict[str, Any]
    ) -> RuleCheckDetail:
        field = rule.get("field", "")
        raw_op = str(rule.get("operator", "")).lower().strip()
        expected = rule.get("value")
        label = rule.get("label") or field.replace("_", " ").title()

        # Retrieve actual answer with fallback key matching
        actual = answers.get(field)
        if actual is None:
            # Fallback for common aliases (e.g. community <-> category)
            aliases = {
                "community": ["category", "caste", "caste_tribe_name"],
                "category": ["community", "caste"],
                "min_qualifying_percentage": ["percentage", "qualifying_percentage", "marks", "percentage_cgpa"],
                "max_annual_family_income": ["annual_income", "family_income", "income"],
                "course_type": ["valid_course_types", "course", "degree_level"],
                "valid_course_types": ["course_type", "course"],
                "max_age": ["age"],
            }
            for alias in aliases.get(field, []):
                if alias in answers:
                    actual = answers[alias]
                    break

        # Check operator validity
        if raw_op not in cls.SUPPORTED_OPERATORS:
            return RuleCheckDetail(
                rule=field,
                label=label,
                operator=raw_op,
                expected=expected,
                actual=actual,
                passed=False,
                message=rule.get("fail_message") or f"Unsupported or invalid rule operator '{raw_op}'.",
            )

        # 1. required operator
        if raw_op in {"required", "exists"}:
            passed = actual is not None and str(actual).strip() != ""
            msg = (
                rule.get("pass_message") or f"{label} provided."
                if passed
                else rule.get("fail_message") or f"{label} is required but missing."
            )
            return RuleCheckDetail(
                rule=field, label=label, operator="required",
                expected="Present", actual="Present" if passed else "Missing",
                passed=passed, message=msg,
            )

        # If actual value is missing for other operators
        if actual is None or str(actual).strip() == "":
            return RuleCheckDetail(
                rule=field, label=label, operator=raw_op,
                expected=expected, actual=None, passed=False,
                message=rule.get("fail_message") or f"{label} was not provided.",
            )

        # 2. equals / not_equals
        if raw_op in {"equals", "eq", "=="}:
            passed = cls._check_equality(actual, expected)
            msg = (
                rule.get("pass_message") or f"{label} requirement satisfied ({expected})."
                if passed
                else rule.get("fail_message") or f"{label} '{actual}' does not match required value '{expected}'."
            )
            return RuleCheckDetail(
                rule=field, label=label, operator="equals",
                expected=expected, actual=actual, passed=passed, message=msg,
            )

        if raw_op in {"not_equals", "ne", "!="}:
            passed = not cls._check_equality(actual, expected)
            msg = (
                rule.get("pass_message") or f"{label} requirement satisfied."
                if passed
                else rule.get("fail_message") or f"{label} must not be '{expected}'."
            )
            return RuleCheckDetail(
                rule=field, label=label, operator="not_equals",
                expected=f"!= {expected}", actual=actual, passed=passed, message=msg,
            )

        # 3. Numeric comparisons (gt, gte, lt, lte)
        if raw_op in {
            "greater_than", "gt", ">",
            "greater_than_or_equal", "gte", ">=",
            "less_than", "lt", "<",
            "less_than_or_equal", "lte", "<=",
        }:
            num_actual = cls._to_float(actual)
            num_expected = cls._to_float(expected)

            if num_actual is None or num_expected is None:
                return RuleCheckDetail(
                    rule=field, label=label, operator=raw_op,
                    expected=expected, actual=actual, passed=False,
                    message=f"Invalid numeric comparison for {label}: provided '{actual}' vs target '{expected}'.",
                )

            if raw_op in {"greater_than", "gt", ">"}:
                passed = num_actual > num_expected
                msg = (
                    rule.get("pass_message") or f"{label} ({actual}) is greater than required {expected}."
                    if passed
                    else rule.get("fail_message") or f"{label} ({actual}) must be greater than {expected}."
                )
                return RuleCheckDetail(
                    rule=field, label=label, operator="greater_than",
                    expected=f"> {expected}", actual=actual, passed=passed, message=msg,
                )

            if raw_op in {"greater_than_or_equal", "gte", ">="}:
                passed = num_actual >= num_expected
                msg = (
                    rule.get("pass_message") or f"{label} ({actual}) meets minimum requirement of {expected}."
                    if passed
                    else rule.get("fail_message") or f"{label} ({actual}) is below required minimum of {expected}."
                )
                return RuleCheckDetail(
                    rule=field, label=label, operator="greater_than_or_equal",
                    expected=f">= {expected}", actual=actual, passed=passed, message=msg,
                )

            if raw_op in {"less_than", "lt", "<"}:
                passed = num_actual < num_expected
                msg = (
                    rule.get("pass_message") or f"{label} ({actual}) is below ceiling of {expected}."
                    if passed
                    else rule.get("fail_message") or f"{label} ({actual}) must be less than {expected}."
                )
                return RuleCheckDetail(
                    rule=field, label=label, operator="less_than",
                    expected=f"< {expected}", actual=actual, passed=passed, message=msg,
                )

            if raw_op in {"less_than_or_equal", "lte", "<="}:
                passed = num_actual <= num_expected
                msg = (
                    rule.get("pass_message") or f"{label} ({actual}) is within the allowable limit of {expected}."
                    if passed
                    else rule.get("fail_message") or f"{label} ({actual}) exceeds allowable ceiling of {expected}."
                )
                return RuleCheckDetail(
                    rule=field, label=label, operator="less_than_or_equal",
                    expected=f"<= {expected}", actual=actual, passed=passed, message=msg,
                )

        # 4. in / contains
        if raw_op in {"in", "contains", "is_in"}:
            passed = False
            expected_list = expected if isinstance(expected, list) else [expected]
            for item in expected_list:
                if cls._check_equality(actual, item):
                    passed = True
                    break
            msg = (
                rule.get("pass_message") or f"{label} ({actual}) is an eligible option."
                if passed
                else rule.get("fail_message") or f"{label} '{actual}' is not among eligible options: {', '.join(str(i) for i in expected_list)}."
            )
            return RuleCheckDetail(
                rule=field, label=label, operator="in",
                expected=expected_list, actual=actual, passed=passed, message=msg,
            )

        return RuleCheckDetail(
            rule=field, label=label, operator=raw_op,
            expected=expected, actual=actual, passed=False,
            message="Unrecognized rule check.",
        )

    @staticmethod
    def _check_equality(val1: Any, val2: Any) -> bool:
        if val1 == val2:
            return True
        if isinstance(val1, str) and isinstance(val2, str):
            return val1.strip().lower() == val2.strip().lower()
        if isinstance(val1, bool) or isinstance(val2, bool):
            return bool(val1) is bool(val2)
        try:
            return float(val1) == float(val2)
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _to_float(val: Any) -> Optional[float]:
        try:
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, str):
                # Clean currency symbols or commas if present (e.g. ₹6,00,000 -> 600000)
                cleaned = re.sub(r"[^\d.]", "", val)
                return float(cleaned) if cleaned else None
            return None
        except (ValueError, TypeError):
            return None
