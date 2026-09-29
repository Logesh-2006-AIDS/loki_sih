export type StaffRequestStatus = 'PENDING' | 'APPROVED' | 'REJECTED';

export interface StaffRequestResponse {
  id: string;
  user_id: string;
  user_name: string;
  user_email: string;
  user_phone?: string | null;
  requested_role: 'OFFICER' | 'COMMITTEE';
  employee_id: string;
  department: string;
  designation: string;
  jurisdiction: string;
  status: StaffRequestStatus;
  rejection_reason?: string | null;
  submitted_at: string;
  reviewed_at?: string | null;
  reviewed_by?: string | null;
  reviewer_name?: string | null;
}

export interface StaffRequestStats {
  pending_count: number;
  active_officers: number;
  active_committee: number;
  rejected_count: number;
  total_requests: number;
}
