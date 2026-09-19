from abc import ABC, abstractmethod
from typing import Any, Dict, List
import uuid
from pydantic import BaseModel


class MeritCalculationResult(BaseModel):
    application_id: uuid.UUID
    total_score: float
    score_breakdown: Dict[str, float] = {}
    rank: int = 0


class BaseMeritService(ABC):
    """
    Architectural interface defining the contract for merit score calculation
    and candidate ranking algorithms.
    """

    @abstractmethod
    def calculate_score(
        self,
        application_id: uuid.UUID,
        scoring_weights: Dict[str, Any],
        application_data: Dict[str, Any],
    ) -> MeritCalculationResult:
        """
        Calculates merit score according to scheme weights and verified application data.
        """
        pass

    @abstractmethod
    def rank_candidates(
        self, scheme_id: uuid.UUID, scored_applications: List[MeritCalculationResult]
    ) -> List[MeritCalculationResult]:
        """
        Ranks scored candidates considering tie-breaking rules and reservation categories.
        """
        pass


class MeritService(BaseMeritService):
    """
    Phase 0 architectural interface stub.
    Actual merit scoring and automated ranking engines will be implemented in subsequent phases.
    """

    def calculate_score(
        self,
        application_id: uuid.UUID,
        scoring_weights: Dict[str, Any],
        application_data: Dict[str, Any],
    ) -> MeritCalculationResult:
        raise NotImplementedError(
            "Merit scoring algorithm is scheduled for subsequent phase implementation."
        )

    def rank_candidates(
        self, scheme_id: uuid.UUID, scored_applications: List[MeritCalculationResult]
    ) -> List[MeritCalculationResult]:
        raise NotImplementedError(
            "Candidate ranking engine is scheduled for subsequent phase implementation."
        )
