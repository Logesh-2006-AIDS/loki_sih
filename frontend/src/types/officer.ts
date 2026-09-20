export interface OfficerQueueItem {
  id: string;
  reference_id: string;
  scheme_id: string;
  scheme_code: string;
  scheme_name: string;
  applicant_name: string;
  state?: string | null;
  status: string;
  submitted_at?: string | null;
  total_documents: number;
  ai_flagged_count: number;
  ai_status: string;
  overall_confidence?: number | null;
}

export interface OfficerQueueCounts {
  pending_review: number;
  verified: number;
  deficient: number;
  rejected: number;
  all: number;
}

export interface OfficerQueueResponse {
  total: number;
  skip: number;
  limit: number;
  counts: OfficerQueueCounts;
  items: OfficerQueueItem[];
}

export interface OfficerStatsResponse {
  pending_review_count: number;
  verified_count: number;
  deficient_count: number;
  rejected_count: number;
  total_assigned_count: number;
}

export interface OfficerDocumentScrutinyItem {
  id: string;
  document_type: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
  status: string;
  uploaded_at: string;

  // Phase 3 AI / OCR Verification Evidence
  ocr_text?: string | null;
  extracted_fields: Record<string, any>;
  field_confidences: Record<string, number>;
  comparison_results: Record<string, any>;
  overall_confidence?: number | null;
  flags: Array<{
    field: string;
    label?: string;
    application_value?: string | null;
    document_value?: string | null;
    reason?: string;
    severity?: string;
  }>;

  // Phase 4 Human Scrutiny Metadata
  officer_decision?: 'VERIFIED' | 'RESUBMISSION_REQUIRED' | 'REJECTED' | null;
  officer_remarks?: string | null;
  ai_override: boolean;
  override_reason?: string | null;
  verified_by?: string | null;
  verified_by_name?: string | null;
  verified_at?: string | null;

  // Phase 5 Lineage & History
  version?: number;
  is_current?: boolean;
  parent_document_id?: string | null;
  history?: Array<{
    id: string;
    version: number;
    original_filename: string;
    mime_type: string;
    file_size: number;
    status: string;
    uploaded_at: string;
    officer_decision?: string | null;
    officer_remarks?: string | null;
    ocr_text?: string | null;
    flags?: any[];
  }>;
}

export interface OfficerApplicationScrutinyResponse {
  id: string;
  reference_id: string;
  status: string;
  submitted_at?: string | null;
  resubmission_count?: number;
  resubmitted_at?: string | null;
  deficiencies_history?: Array<{
    id: string;
    document_id?: string | null;
    reason: string;
    applicant_message: string;
    status: string;
    cycle: number;
    created_at: string;
    replacement_uploaded_at?: string | null;
    resolved_at?: string | null;
    applicant_remarks?: string | null;
  }>;

  applicant_id: string;
  applicant_name: string;
  applicant_email: string;
  applicant_phone?: string | null;

  scheme_id: string;
  scheme_code: string;
  scheme_name: string;
  scheme_version?: string | null;
  eligibility_rules?: Record<string, any> | null;
  form_schema?: Record<string, any> | null;
  required_documents_config?: Array<{
    code: string;
    type?: string;
    name: string;
    label?: string;
    required: boolean;
    allowed_extensions?: string[];
    max_size_mb?: number;
  }> | null;

  form_data: Record<string, any>;
  documents: OfficerDocumentScrutinyItem[];

  scrutiny_remarks?: string | null;
  scrutiny_officer_id?: string | null;
  scrutiny_officer_name?: string | null;
  scrutiny_completed_at?: string | null;
}

export interface OfficerDocumentDecisionRequest {
  decision: 'VERIFIED' | 'RESUBMISSION_REQUIRED' | 'REJECTED';
  remarks?: string;
  ai_override?: boolean;
  override_reason?: string;
}

export interface DeficiencyItemCreate {
  document_id?: string;
  reason: string;
  applicant_message: string;
}

export interface OfficerApplicationDecisionRequest {
  decision: 'VERIFIED' | 'DEFICIENT' | 'REJECTED';
  remarks: string;
  deficiencies?: DeficiencyItemCreate[];
}
