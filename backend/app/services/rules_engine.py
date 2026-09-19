from abc import ABC, abstractmethod
from typing import Any, Dict, List
from pydantic import BaseModel


class RuleEvaluationResult(BaseModel):
    is_eligible: bool
    passed_rules: List[str] = []
    failed_rules: List[str] = []
    deficiencies: List[Dict[str, Any]] = []
    notes: Dict[str, Any] = {}


class BaseRulesEngine(ABC):
    """
    Architectural interface defining the contract for scheme eligibility rules evaluation.
    """

    @abstractmethod
    def evaluate_eligibility(
        self,
        scheme_rules: Dict[str, Any],
        application_data: Dict[str, Any],
        verified_documents: List[Dict[str, Any]],
    ) -> RuleEvaluationResult:
        """
        Evaluates dynamic scheme eligibility rules (income ceiling, community/caste validation,
        age limit, educational qualifications) against applicant data.
        """
        pass


class RulesEngine(BaseRulesEngine):
    """
    Phase 0 architectural interface stub.
    Complex rule evaluation engines will be implemented in subsequent phases.
    """

    def evaluate_eligibility(
        self,
        scheme_rules: Dict[str, Any],
        application_data: Dict[str, Any],
        verified_documents: List[Dict[str, Any]],
    ) -> RuleEvaluationResult:
        raise NotImplementedError(
            "Dynamic scheme eligibility rules engine is scheduled for subsequent phase implementation."
        )
