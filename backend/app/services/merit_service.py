import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel

from app.core.exceptions import ValidationException
from app.models.application import Application
from app.models.committee_review import CommitteeReview


class MeritCalculationResult(BaseModel):
    application_id: uuid.UUID
    total_score: float
    score_breakdown: Dict[str, Any] = {}
    rank: int = 0
    tie_break_level: Optional[str] = None


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
        pass

    @abstractmethod
    def rank_candidates(
        self, scheme_id: uuid.UUID, scored_applications: List[MeritCalculationResult]
    ) -> List[MeritCalculationResult]:
        pass


def _extract_nested_field(data: Dict[str, Any], path: str) -> Any:
    """Extracts value from a nested dict using dot-notation path."""
    parts = path.split(".")
    curr = data
    for p in parts:
        if not isinstance(curr, dict):
            return None
        curr = curr.get(p)
        if curr is None:
            return None
    return curr


class GenericMeritCalculator:
    """
    Generic, declarative merit calculation engine.
    Driven 100% by the scoring configuration in the scheme version's frozen rules snapshot.
    Performs purely deterministic algebraic reductions without scheme-specific branching.
    """

    @staticmethod
    def calculate_application_score(
        app: Application,
        scoring_rules: Dict[str, Any],
        reviews: List[CommitteeReview],
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculates the merit score and detailed auditable breakdown for a single application.
        """
        form_data = app.form_data or {}
        scoring_components = scoring_rules.get("scoring_components", [])

        # Backward compatibility fallback if scoring_weights dict is provided instead of components
        if not scoring_components and "weights" in scoring_rules:
            # Synthetic standard components
            weights = scoring_rules.get("weights", {})
            scoring_components = [
                {
                    "code": k,
                    "label": k.replace("_", " ").title(),
                    "weight": float(v),
                    "source_type": "COMMITTEE_EVALUATION" if "proposal" in k or "sop" in k or "interview" in k else "APPLICATION_FORM_FIELD",
                    "field_path": "academic.percentage_marks" if "academic" in k else "research.nirf_rank" if "nirf" in k else "research.qs_rank" if "qs" in k else k,
                    "evaluation_type": "PERCENTAGE_NORMALIZED",
                    "max_raw": 100.0,
                }
                for k, v in weights.items()
            ]

        if not scoring_components:
            raise ValidationException("Scoring configuration contains no scoring components")

        component_breakdowns: Dict[str, Any] = {}
        total_score = 0.0

        for comp in scoring_components:
            code = comp.get("code")
            label = comp.get("label", code)
            weight = float(comp.get("weight", 0.0))
            source_type = comp.get("source_type", "APPLICATION_FORM_FIELD")
            max_raw = float(comp.get("max_raw", 100.0))

            if source_type == "APPLICATION_FORM_FIELD":
                field_path = comp.get("field_path", "")
                raw_val = _extract_nested_field(form_data, field_path)
                evaluation_type = comp.get("evaluation_type", "PERCENTAGE_NORMALIZED")

                if evaluation_type == "TIER_BRACKETS":
                    brackets = comp.get("brackets", [])
                    default_pct = float(comp.get("default_percentage_of_weight", 50.0))
                    try:
                        rank_val = int(raw_val) if raw_val is not None else 99999
                    except (ValueError, TypeError):
                        rank_val = 99999

                    matched_bracket = None
                    pct_of_weight = default_pct
                    for b in brackets:
                        if rank_val <= int(b.get("max_rank", 0)):
                            pct_of_weight = float(b.get("percentage_of_weight", 100.0))
                            matched_bracket = b.get("label", f"Rank <= {b.get('max_rank')}")
                            break

                    weighted_score = round((pct_of_weight / 100.0) * weight, 4)
                    component_breakdowns[code] = {
                        "label": label,
                        "raw_value": raw_val,
                        "matched_tier": matched_bracket or "Default / Unranked",
                        "weight": weight,
                        "weighted_score": weighted_score,
                        "source_type": source_type,
                        "field_path": field_path,
                    }
                else:  # PERCENTAGE_NORMALIZED
                    try:
                        num_val = float(raw_val) if raw_val is not None else 0.0
                    except (ValueError, TypeError):
                        num_val = 0.0

                    normalized_ratio = min(max(num_val / max_raw, 0.0), 1.0)
                    weighted_score = round(normalized_ratio * weight, 4)
                    component_breakdowns[code] = {
                        "label": label,
                        "raw_value": num_val,
                        "max_raw": max_raw,
                        "weight": weight,
                        "weighted_score": weighted_score,
                        "source_type": source_type,
                        "field_path": field_path,
                    }

                total_score += weighted_score

            elif source_type == "COMMITTEE_EVALUATION":
                # Gather scores given by reviewers for this component
                valid_scores = []
                for r in reviews:
                    if r.scores and code in r.scores:
                        try:
                            valid_scores.append(float(r.scores[code]))
                        except (ValueError, TypeError):
                            pass

                if valid_scores:
                    consensus_raw = sum(valid_scores) / len(valid_scores)
                else:
                    consensus_raw = 0.0

                normalized_ratio = min(max(consensus_raw / max_raw, 0.0), 1.0)
                weighted_score = round(normalized_ratio * weight, 4)
                total_score += weighted_score

                component_breakdowns[code] = {
                    "label": label,
                    "consensus_raw": round(consensus_raw, 2),
                    "reviewers_count": len(valid_scores),
                    "scores_received": valid_scores,
                    "max_raw": max_raw,
                    "weight": weight,
                    "weighted_score": weighted_score,
                    "source_type": source_type,
                }

        final_total = round(total_score, 4)
        breakdown_payload = {
            "total_score": final_total,
            "max_possible_score": float(scoring_rules.get("total_max_score", 100.0)),
            "calculation_timestamp": datetime.now(timezone.utc).isoformat(),
            "formula_version": "1.0",
            "components": component_breakdowns,
        }
        return final_total, breakdown_payload


class MeritService(BaseMeritService):
    """
    Phase 6 Production implementation of the MeritService contract.
    Wraps GenericMeritCalculator to provide deterministic, auditable merit scoring.
    """

    def calculate_score(
        self,
        application_id: uuid.UUID,
        scoring_weights: Dict[str, Any],
        application_data: Dict[str, Any],
    ) -> MeritCalculationResult:
        # Construct synthetic app instance for standalone calculation
        from app.models.application import Application
        dummy_app = Application(
            id=application_id,
            form_data=application_data,
        )
        total_score, breakdown = GenericMeritCalculator.calculate_application_score(
            app=dummy_app,
            scoring_rules={"scoring_components": scoring_weights.get("scoring_components", [])},
            reviews=[],
        )
        return MeritCalculationResult(
            application_id=application_id,
            total_score=total_score,
            score_breakdown=breakdown,
        )

    def rank_candidates(
        self, scheme_id: uuid.UUID, scored_applications: List[MeritCalculationResult]
    ) -> List[MeritCalculationResult]:
        # Basic descending rank by total score
        sorted_apps = sorted(scored_applications, key=lambda a: a.total_score, reverse=True)
        for idx, item in enumerate(sorted_apps, 1):
            item.rank = idx
        return sorted_apps
