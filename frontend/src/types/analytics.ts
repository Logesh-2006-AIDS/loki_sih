export interface SystemOverviewMetrics {
  total_applications: number;
  current_state_distribution: Record<string, number>;
  active_schemes_count: number;
  active_schemes_total_quota_slots: number;
  active_schemes_quota_utilization_rate: number;
  total_verified_pool: number;
  active_deficiencies_count: number;
  resolved_deficiencies_count: number;
  total_evaluation_batches: number;
  finalized_evaluation_batches: number;
  total_selected: number;
  total_waitlisted: number;
  total_rejected: number;
  total_officers: number;
  total_committee_members: number;
}

export interface ApplicationMilestone {
  milestone_key: string;
  milestone_label: string;
  count: number;
  conversion_from_start_rate: number;
  conversion_from_previous_rate: number;
}

export interface ApplicationFunnelResponse {
  total_initiated: number;
  milestones: ApplicationMilestone[];
}

export interface TimeSeriesPoint {
  date: string;
  submissions_count: number;
  verifications_count: number;
  selections_count: number;
}

export interface VelocityTrendsResponse {
  start_date: string;
  end_date: string;
  granularity: string;
  data_points: TimeSeriesPoint[];
}

export interface SchemePerformanceSummary {
  scheme_id: string;
  scheme_code: string;
  scheme_name: string;
  scheme_version_id?: string;
  scheme_version?: string;
  is_active: boolean;
  quota_slots: number;
  total_applications: number;
  verified_count: number;
  selected_count: number;
  waitlisted_count: number;
  rejected_count: number;
  quota_exhaustion_rate: number;
}

export interface SchemeBreakdownsResponse {
  schemes: SchemePerformanceSummary[];
}

export interface OfficerThroughputItem {
  officer_id: string;
  officer_name: string;
  assigned_applications_count: number;
  verified_count: number;
  deficiencies_flagged_count: number;
  human_overrides_count: number;
  avg_verification_duration_hours: number;
}

export interface OfficerThroughputResponse {
  officers: OfficerThroughputItem[];
}

export interface VerificationDecisionMetrics {
  total_documents_evaluated: number;
  ai_human_agreements: number;
  human_overrides: number;
  ai_human_agreement_rate: number;
  human_override_rate: number;
  override_breakdown: Record<string, number>;
}

export interface AuditLogReportItem {
  id: string;
  created_at: string;
  actor_id?: string;
  actor_name?: string;
  entity_type: string;
  entity_id: string;
  action: string;
  previous_status?: string;
  new_status?: string;
  details: Record<string, any>;
}

export interface AuditLogReportResponse {
  total_count: number;
  page: number;
  limit: number;
  logs: AuditLogReportItem[];
}
