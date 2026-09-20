export interface PublicDeficiencyItem {
  id: string;
  application_id: string;
  cycle: number;
  document_id: string | null;
  document_type: string;
  document_name: string;
  reason: string;
  applicant_message: string;
  applicant_remarks: string | null;
  status: 'OPEN' | 'REPLACEMENT_UPLOADED' | 'UNDER_REVIEW' | 'RESOLVED' | 'FAILED';
  created_at: string;
  replacement_document_id: string | null;
  replacement_uploaded_at: string | null;
  resolved_at: string | null;
}

export interface PublicDeficiencyListResponse {
  application_id: string;
  application_status: string;
  total: number;
  open_count: number;
  replacement_uploaded_count: number;
  under_review_count: number;
  resolved_count: number;
  can_resubmit: boolean;
  items: PublicDeficiencyItem[];
}

export interface DeficiencyReplacementUploadResponse {
  deficiency_id: string;
  status: string;
  document_id: string;
  version: number;
  original_filename: string;
  applicant_remarks: string | null;
  uploaded_at: string;
  message: string;
}

export interface ApplicationResubmitRequest {
  declaration_confirmed: boolean;
  remarks?: string;
}

export interface ApplicationResubmitResponse {
  application_id: string;
  reference_id: string;
  status: string;
  resubmission_count: number;
  resubmitted_at: string;
  message: string;
}
