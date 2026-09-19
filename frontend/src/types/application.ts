export type ApplicationStatus =
  | 'DRAFT'
  | 'SUBMITTED'
  | 'UNDER_AI_VERIFICATION'
  | 'DEFICIENT'
  | 'RESUBMITTED'
  | 'UNDER_MANUAL_REVIEW'
  | 'VERIFIED'
  | 'SHORTLISTED'
  | 'MERIT_RANKED'
  | 'SELECTED'
  | 'WAITLISTED'
  | 'REJECTED'
  | 'FELLOWSHIP_ACTIVE';

export type DocumentStatus =
  | 'PENDING'
  | 'UPLOADED'
  | 'PROCESSING'
  | 'VERIFIED'
  | 'FLAGGED'
  | 'REJECTED'
  | 'RESUBMISSION_REQUIRED';

export interface FormOption {
  label: string;
  value: string;
}

export interface FormField {
  name: string;
  label: string;
  type:
    | 'text'
    | 'number'
    | 'date'
    | 'email'
    | 'phone'
    | 'select'
    | 'radio'
    | 'checkbox'
    | 'textarea';
  required?: boolean;
  placeholder?: string;
  help_text?: string;
  options?: FormOption[];
  min?: number;
  max?: number;
}

export interface FormSection {
  id: string;
  title: string;
  description?: string;
  fields: FormField[];
}

export interface FormSchema {
  disclaimer?: string;
  sections: FormSection[];
}

export interface RequiredDocumentConfig {
  code: string;
  type?: string;
  name: string;
  label?: string;
  required: boolean;
  allowed_extensions?: string[];
  max_size_mb?: number;
  allow_multiple?: boolean;
}

export interface RequiredDocumentsSchema {
  disclaimer?: string;
  documents: RequiredDocumentConfig[];
}

export interface DocumentItem {
  id: string;
  application_id: string;
  document_type: string;
  original_filename: string;
  storage_path?: string;
  mime_type: string;
  file_size: number;
  status: DocumentStatus;
  uploaded_at: string;
  updated_at: string;
}

export interface Application {
  id: string;
  reference_id: string;
  applicant_id: string;
  scheme_id: string;
  scheme_version_id?: string | null;
  status: ApplicationStatus;
  form_data: Record<string, any>;
  frozen_rules_snapshot?: Record<string, any> | null;
  merit_score?: number | null;
  submitted_at?: string | null;
  created_at: string;
  updated_at: string;
}
