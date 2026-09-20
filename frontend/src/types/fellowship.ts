export interface FellowshipRecord {
  id: string;
  application_id: string;
  fellowship_number: string;
  sanction_order_number?: string | null;
  sanction_mode: string;
  sanction_date?: string | null;
  scheme_id: string;
  scheme_version_id: string;
  applicant_id: string;
  assigned_officer_id?: string | null;
  status: 'ACTIVE' | 'UNDER_RENEWAL' | 'SUSPENDED' | 'COMPLETED' | 'TERMINATED';
  current_year: number;
  tenure_years: number;
  start_date?: string | null;
  end_date?: string | null;
  institution_name?: string | null;
  department?: string | null;
  guide_name?: string | null;
  research_topic?: string | null;
  award_letter_url?: string | null;
  disbursement_status: string;
  created_at: string;
  updated_at: string;
}

export interface RenewalSubmission {
  id: string;
  fellowship_id: string;
  renewal_number: number;
  academic_year: number;
  status: 'DRAFT' | 'PENDING' | 'UNDER_REVIEW' | 'APPROVED' | 'REJECTED' | 'DEFICIENT';
  annual_progress_summary?: string | null;
  marks_percentage?: number | null;
  continuation_certificate_path?: string | null;
  marksheet_document_path?: string | null;
  reviewer_id?: string | null;
  reviewer_decision?: string | null;
  reviewer_remarks?: string | null;
  deficiency_id?: string | null;
  submitted_at: string;
  reviewed_at?: string | null;
}

export interface ProgressReport {
  id: string;
  fellowship_id: string;
  academic_year: number;
  report_period_start?: string | null;
  report_period_end?: string | null;
  file_path: string;
  description?: string | null;
  publications_count: number;
  presentations_count: number;
  patents_count: number;
  supervisor_remarks?: string | null;
  supervisor_approved: boolean;
  status: 'PENDING' | 'UNDER_REVIEW' | 'APPROVED' | 'REJECTED' | 'DEFICIENT';
  reviewer_id?: string | null;
  reviewer_decision?: string | null;
  reviewer_remarks?: string | null;
  deficiency_id?: string | null;
  submitted_at: string;
  reviewed_at?: string | null;
}

export interface DisbursementInstallment {
  id: string;
  fellowship_id: string;
  installment_number: number;
  academic_year: number;
  period_start: string;
  period_end: string;
  stipend_amount: number;
  contingency_amount: number;
  hra_amount: number;
  total_amount: number;
  payment_status: 'SCHEDULED' | 'PENDING_APPROVAL' | 'APPROVED_FOR_PAYMENT' | 'PROCESSING' | 'SUCCESS' | 'FAILED' | 'CANCELLED' | 'RETRY_EXHAUSTED';
  integration_mode: string;
  payment_request_id: string;
  pfms_reference_id?: string | null;
  bank_reference_utr?: string | null;
  account_number_masked: string;
  ifsc_code: string;
  retry_count: number;
  last_attempt_at?: string | null;
  processed_at?: string | null;
  failure_reason?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
}

export interface AwardAcceptancePayload {
  application_id: string;
  joining_date: string;
  institution_name: string;
  department?: string;
  guide_name?: string;
  research_topic?: string;
  bank_account_number: string;
  ifsc_code: string;
}

export interface RenewalSubmitPayload {
  academic_year: number;
  annual_progress_summary?: string;
  marks_percentage?: number;
  continuation_certificate_path?: string;
  marksheet_document_path?: string;
}

export interface ProgressReportSubmitPayload {
  academic_year: number;
  report_period_start?: string;
  report_period_end?: string;
  file_path: string;
  description?: string;
  publications_count?: number;
  presentations_count?: number;
  patents_count?: number;
  supervisor_remarks?: string;
  supervisor_approved?: boolean;
}
