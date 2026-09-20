import api from './api';
import {
  FellowshipRecord,
  RenewalSubmission,
  ProgressReport,
  DisbursementInstallment,
  AwardAcceptancePayload,
  RenewalSubmitPayload,
  ProgressReportSubmitPayload,
} from '../types/fellowship';

export const fellowshipService = {
  // Scholar acceptance
  acceptAward: async (payload: AwardAcceptancePayload) => {
    const res = await api.post('/fellowships/accept-award', payload);
    return res.data;
  },

  // Admin/Officer activation
  activateFellowship: async (applicationId: string, tenureYears: number = 5) => {
    const res = await api.post('/fellowships/activate', {
      application_id: applicationId,
      tenure_years: tenureYears,
    });
    return res.data as FellowshipRecord;
  },

  // Scholar queries
  getMyFellowship: async () => {
    const res = await api.get('/fellowships/my');
    return res.data as FellowshipRecord;
  },

  getFellowshipById: async (id: string) => {
    const res = await api.get(`/fellowships/${id}`);
    return res.data as FellowshipRecord;
  },

  // Renewals
  submitRenewal: async (fellowshipId: string, payload: RenewalSubmitPayload) => {
    const res = await api.post(`/fellowships/${fellowshipId}/renewals`, payload);
    return res.data as RenewalSubmission;
  },

  listRenewals: async (fellowshipId: string) => {
    const res = await api.get(`/fellowships/${fellowshipId}/renewals`);
    return res.data as RenewalSubmission[];
  },

  reviewRenewal: async (
    renewalId: string,
    decision: 'APPROVED' | 'REJECTED' | 'DEFICIENT',
    remarks?: string,
    deficiencyReason?: string,
    deficiencyMessage?: string
  ) => {
    const res = await api.post(`/fellowships/renewals/${renewalId}/review`, {
      decision,
      remarks,
      deficiency_reason: deficiencyReason,
      deficiency_message: deficiencyMessage,
    });
    return res.data as RenewalSubmission;
  },

  // Progress Reports
  submitProgressReport: async (fellowshipId: string, payload: ProgressReportSubmitPayload) => {
    const res = await api.post(`/fellowships/${fellowshipId}/progress-reports`, payload);
    return res.data as ProgressReport;
  },

  listProgressReports: async (fellowshipId: string) => {
    const res = await api.get(`/fellowships/${fellowshipId}/progress-reports`);
    return res.data as ProgressReport[];
  },

  reviewProgressReport: async (
    reportId: string,
    decision: 'APPROVED' | 'REJECTED' | 'DEFICIENT',
    remarks?: string,
    deficiencyReason?: string,
    deficiencyMessage?: string
  ) => {
    const res = await api.post(`/fellowships/progress-reports/${reportId}/review`, {
      decision,
      remarks,
      deficiency_reason: deficiencyReason,
      deficiency_message: deficiencyMessage,
    });
    return res.data as ProgressReport;
  },

  getDisbursements: async (fellowshipId: string) => {
    const res = await api.get(`/fellowships/${fellowshipId}/disbursements`);
    return res.data as DisbursementInstallment[];
  },

  listAllDisbursements: async (status?: string) => {
    const res = await api.get('/disbursements', { params: status ? { status } : {} });
    return res.data as DisbursementInstallment[];
  },

  approveDisbursement: async (installmentId: string, remarks?: string) => {
    const res = await api.post(`/disbursements/${installmentId}/approve`, { remarks });
    return res.data as DisbursementInstallment;
  },

  executeDisbursement: async (installmentId: string, testAccountOverride?: string) => {
    const res = await api.post(`/disbursements/${installmentId}/execute`, {
      test_account_override: testAccountOverride,
    });
    return res.data;
  },

  retryDisbursement: async (installmentId: string, testAccountOverride?: string) => {
    const res = await api.post(`/disbursements/${installmentId}/retry`, {
      test_account_override: testAccountOverride,
    });
    return res.data;
  },

  // Status updates
  updateFellowshipStatus: async (
    fellowshipId: string,
    status: string,
    reason: string,
    statutoryOrderNumber?: string
  ) => {
    const res = await api.patch(`/fellowships/${fellowshipId}/status`, {
      status,
      reason,
      statutory_order_number: statutoryOrderNumber,
    });
    return res.data as FellowshipRecord;
  },
};

export default fellowshipService;
