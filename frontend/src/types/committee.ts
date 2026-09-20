export interface CommitteeScheme {
  scheme_id: string;
  scheme_code: string;
  scheme_name: string;
  scheme_version_id: string | null;
  scheme_version: string;
  is_demo: boolean;
  required_quorum: number;
  verified_applications_count: number;
  merit_ranked_count: number;
  finalized_count: number;
  batches_count: number;
}

export interface CommitteeBatch {
  id: string;
  name: string;
  scheme_id: string;
  scheme_version_id: string;
  status: string;
  is_locked: boolean;
  locked_at?: string | null;
  locked_by?: string | null;
  application_count: number;
  reviews_completed_count: number;
  created_at: string;
}

export interface CommitteeBatchCreatePayload {
  name: string;
  scheme_id: string;
  scheme_version_id: string;
  application_ids: string[];
}

export interface CommitteeReviewResponse {
  id: string;
  application_id: string;
  committee_member_id: string;
  committee_member_name?: string | null;
  batch_id: string;
  scores: Record<string, number>;
  remarks?: string | null;
  recommendation: 'RECOMMEND' | 'WAITLIST' | 'REJECT' | 'NEEDS_DISCUSSION';
  is_locked: boolean;
  created_at: string;
  updated_at: string;
}

export interface CommitteeDossier {
  application_id: string;
  reference_id: string;
  batch_id: string;
  scheme_id: string;
  scheme_name: string;
  scheme_version_id: string;
  scheme_version: string;
  applicant_name: string;
  category?: string | null;
  state?: string | null;
  academic_summary: Record<string, any>;
  proposal_summary: Record<string, any>;
  verified_documents: Array<{
    document_type: string;
    original_filename: string;
    status: string;
  }>;
  my_review?: CommitteeReviewResponse | null;
  is_batch_locked: boolean;
  required_quorum: number;
  completed_reviews_count: number;
}

export interface CommitteeReviewPayload {
  scores: Record<string, number>;
  remarks?: string;
  recommendation: 'RECOMMEND' | 'WAITLIST' | 'REJECT' | 'NEEDS_DISCUSSION';
}

export interface MeritCalculationResponse {
  batch_id: string;
  scheme_id: string;
  scheme_version_id: string;
  scored_count: number;
  status: string;
  calculation_timestamp: string;
  boundary_tie_flag: boolean;
  tied_candidate_ids: string[];
}

export interface MeritRankItem {
  application_id: string;
  reference_id: string;
  applicant_name: string;
  total_score: number;
  rank: number;
  tie_break_level?: string | null;
  status: string;
  score_breakdown: Record<string, any>;
}

export interface TieResolutionPayload {
  preferred_candidate_id: string;
  secondary_candidate_id: string;
  statutory_justification: string;
  authority_order_reference: string;
}

export interface BatchFinalizePayload {
  committee_minutes: string;
  meeting_date: string;
  resolution_reference: string;
}

export interface SelectionResultItem {
  id: string;
  application_id: string;
  result: 'SELECTED' | 'WAITLISTED' | 'REJECTED';
  rank?: number | null;
  quota_category: string;
  reason?: string | null;
  committee_minutes?: string | null;
  authority_reference?: string | null;
  selection_round: number;
  is_override: boolean;
  override_reason?: string | null;
  override_by?: string | null;
  finalized_by?: string | null;
  finalized_at?: string | null;
  created_at: string;
}

export interface SelectionOverridePayload {
  application_id: string;
  target_status: 'SELECTED' | 'REJECTED';
  override_reason: string;
  authority_reference: string;
  selection_round?: number;
}

export interface ApplicantSelectionResult {
  application_reference_id: string;
  result: string;
  rank?: number | null;
  selection_round: number;
  finalized_at?: string | null;
}
