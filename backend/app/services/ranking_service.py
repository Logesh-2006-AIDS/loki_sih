import uuid
from datetime import datetime, date
from functools import cmp_to_key
from typing import Any, Dict, List, Optional, Tuple

from app.core.exceptions import BoundaryTieConflictException, ValidationException
from app.models.application import Application
from app.models.merit_score import MeritScore


def _parse_dob(val: Any) -> date:
    """Parses a date string or object into date for seniority comparison."""
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(val.strip(), fmt).date()
            except ValueError:
                pass
    return date.max  # Younger fallback if invalid/missing


class DynamicRankingEngine:
    """
    Evaluates candidate rankings and resolves ties dynamically according to the
    ordered tie-breaking criteria configured in the scheme version's snapshot.
    Enforces strict boundary-tie guarding to prevent arbitrary quota allocation.
    """

    CRITERIA_COMPARATORS = {
        "ACADEMIC_PERCENTAGE": lambda app: float(
            (app.form_data or {}).get("academic", {}).get("percentage_marks")
            or (app.form_data or {}).get("percentage_marks")
            or 0.0
        ),
        "AGE_SENIORITY": lambda app: _parse_dob(
            (app.form_data or {}).get("personal", {}).get("dob")
            or (app.form_data or {}).get("dob")
        ),
        "FAMILY_INCOME": lambda app: float(
            (app.form_data or {}).get("financial", {}).get("annual_family_income")
            or (app.form_data or {}).get("annual_family_income")
            or 99999999.0
        ),
        "SUBMISSION_TIMESTAMP": lambda app: app.submitted_at or datetime.max,
    }

    @classmethod
    def compare_candidates(
        cls,
        cand_a: Tuple[Application, MeritScore],
        cand_b: Tuple[Application, MeritScore],
        tie_breaking_order: List[str],
    ) -> Tuple[int, str]:
        """
        Compares two candidates:
        Returns:
          - negative if cand_a ranks higher (better) than cand_b
          - positive if cand_b ranks higher (better) than cand_a
          - 0 if genuinely co-ranked tied
          - string indicating which tier broke the tie
        """
        app_a, score_a = cand_a
        app_b, score_b = cand_b

        # 1. Primary Sort: Total Merit Score (DESC)
        diff = score_b.total_score - score_a.total_score
        if abs(diff) > 0.0001:
            return (-1 if diff < 0 else 1), "DIRECT_SCORE"

        # Check if tie was resolved by chairperson
        if score_a.tie_break_level == "CHAIRPERSON_RESOLUTION" and score_b.tie_break_level == "CHAIRPERSON_RESOLUTION":
            if score_a.rank and score_b.rank and score_a.rank != score_b.rank:
                return (-1 if score_a.rank < score_b.rank else 1), "CHAIRPERSON_RESOLUTION"


        # 2. Iterate through configured tie-breaking criteria
        for criterion in tie_breaking_order:
            crit_upper = criterion.strip().upper()
            if crit_upper in cls.CRITERIA_COMPARATORS:
                extractor = cls.CRITERIA_COMPARATORS[crit_upper]
                val_a = extractor(app_a)
                val_b = extractor(app_b)

                if crit_upper == "ACADEMIC_PERCENTAGE":
                    # Higher is better
                    if abs(val_a - val_b) > 0.001:
                        return (-1 if val_a > val_b else 1), f"TIER_{crit_upper}"
                elif crit_upper == "AGE_SENIORITY":
                    # Older is better (earlier date wins)
                    if val_a != val_b:
                        return (-1 if val_a < val_b else 1), f"TIER_{crit_upper}"
                elif crit_upper == "FAMILY_INCOME":
                    # Lower income is prioritized (lower wins)
                    if abs(val_a - val_b) > 1.0:
                        return (-1 if val_a < val_b else 1), f"TIER_{crit_upper}"
                elif crit_upper == "SUBMISSION_TIMESTAMP":
                    # Earlier submission timestamp wins
                    if val_a != val_b:
                        return (-1 if val_a < val_b else 1), f"TIER_{crit_upper}"

        # Genuinely co-ranked tied after exhausting all criteria
        return 0, "CO_RANKED_TIED"

    @classmethod
    def rank_batch_candidates(
        cls,
        candidates: List[Tuple[Application, MeritScore]],
        tie_breaking_order: List[str],
        quota_config: Dict[str, Any],
    ) -> Tuple[List[Tuple[Application, MeritScore, int, str]], bool, List[uuid.UUID]]:
        """
        Sorts, assigns sequential integer ranks, and checks boundary-tie guards.
        Returns:
          - Ranked list: [(Application, MeritScore, rank, tie_break_level)]
          - boundary_tie_flag: bool (True if an unresolved tie crosses a quota boundary)
          - tied_boundary_candidate_ids: List of UUIDs involved in boundary tie
        """
        if not candidates:
            return [], False, []

        default_tie_order = [
            "ACADEMIC_PERCENTAGE",
            "AGE_SENIORITY",
            "FAMILY_INCOME",
            "SUBMISSION_TIMESTAMP",
        ]
        order_to_use = tie_breaking_order or default_tie_order

        # Build custom sorting comparator
        def _comparator(a: Tuple[Application, MeritScore], b: Tuple[Application, MeritScore]) -> int:
            cmp_res, _ = cls.compare_candidates(a, b, order_to_use)
            return cmp_res

        sorted_candidates = sorted(candidates, key=cmp_to_key(_comparator))

        # Assign ranks and determine exact tie_break_level for each
        ranked_list = []
        n = len(sorted_candidates)
        total_slots = int(quota_config.get("total_slots", 10))
        waitlist_slots = int(quota_config.get("waitlist_slots", 3))

        boundary_tie_flag = False
        tied_candidate_ids: List[uuid.UUID] = []

        current_rank = 1
        for i in range(n):
            curr_app, curr_score = sorted_candidates[i]
            tie_level = "DIRECT_SCORE"

            if i > 0:
                prev_app, prev_score = sorted_candidates[i - 1]
                cmp_val, tier_reason = cls.compare_candidates(
                    (curr_app, curr_score), (prev_app, prev_score), order_to_use
                )
                if cmp_val == 0:
                    # Genuinely tied with previous candidate
                    tie_level = "CO_RANKED_TIED"
                    # Share rank with previous candidate or sequential?
                    # In official merit indexing, candidates retain shared rank
                else:
                    tie_level = tier_reason

            ranked_list.append((curr_app, curr_score, i + 1, tie_level))

        # Check selection boundary tie:
        # Boundary 1: Rank total_slots vs total_slots + 1
        # Boundary 2: Rank total_slots + waitlist_slots vs total_slots + waitlist_slots + 1
        boundaries_to_check = [total_slots, total_slots + waitlist_slots]

        for b_rank in boundaries_to_check:
            if 0 < b_rank < n:
                app_at_cutoff, score_at_cutoff, _, _ = ranked_list[b_rank - 1]
                app_beyond_cutoff, score_beyond_cutoff, _, _ = ranked_list[b_rank]

                cmp_res, _ = cls.compare_candidates(
                    (app_at_cutoff, score_at_cutoff),
                    (app_beyond_cutoff, score_beyond_cutoff),
                    order_to_use,
                )
                if cmp_res == 0:
                    boundary_tie_flag = True
                    tied_candidate_ids.extend([app_at_cutoff.id, app_beyond_cutoff.id])

        return ranked_list, boundary_tie_flag, list(set(tied_candidate_ids))

    @classmethod
    def allocate_quota_outcomes(
        cls,
        ranked_list: List[Tuple[Application, MeritScore, int, str]],
        quota_config: Dict[str, Any],
        has_boundary_tie: bool,
    ) -> List[Tuple[Application, MeritScore, int, str, str]]:
        """
        Partitions ranked candidates into SELECTED, WAITLISTED, and REJECTED.
        If an unresolved boundary tie exists, halts and raises BoundaryTieConflictException.
        """
        if has_boundary_tie:
            raise BoundaryTieConflictException(
                "Cannot automatically allocate quota: An unresolved exact tie crosses a selection or waitlist boundary. "
                "The Committee Chairperson must resolve this tie before finalization."
            )

        total_slots = int(quota_config.get("total_slots", 10))
        waitlist_slots = int(quota_config.get("waitlist_slots", 3))

        outcomes = []
        for app, score, rank, tie_level in ranked_list:
            if rank <= total_slots:
                outcome = "SELECTED"
            elif rank <= (total_slots + waitlist_slots):
                outcome = "WAITLISTED"
            else:
                outcome = "REJECTED"
            outcomes.append((app, score, rank, tie_level, outcome))

        return outcomes
