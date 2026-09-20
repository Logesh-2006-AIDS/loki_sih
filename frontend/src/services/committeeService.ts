import api from './api';
import {
  CommitteeScheme,
  CommitteeBatch,
  CommitteeBatchCreatePayload,
  CommitteeDossier,
  CommitteeReviewResponse,
  CommitteeReviewPayload,
  MeritCalculationResponse,
  MeritRankItem,
  TieResolutionPayload,
  BatchFinalizePayload,
  SelectionResultItem,
  SelectionOverridePayload,
  ApplicantSelectionResult,
} from '../types/committee';

export const committeeService = {
  // 1. Schemes with workload counters
  async getCommitteeSchemes(): Promise<CommitteeScheme[]> {
    const response = await api.get<CommitteeScheme[]>('/committee/schemes');
    return response.data;
  },

  // 2. Evaluation Batches
  async getBatches(schemeId?: string): Promise<CommitteeBatch[]> {
    const response = await api.get<CommitteeBatch[]>('/committee/batches', {
      params: schemeId ? { scheme_id: schemeId } : undefined,
    });
    return response.data;
  },

  async getBatchDetails(batchId: string): Promise<CommitteeBatch> {
    const response = await api.get<CommitteeBatch>(`/committee/batches/${batchId}`);
    return response.data;
  },

  async createBatch(payload: CommitteeBatchCreatePayload): Promise<CommitteeBatch> {
    const response = await api.post<CommitteeBatch>('/committee/batches', payload);
    return response.data;
  },

  async addApplicationToBatch(batchId: string, applicationId: string): Promise<CommitteeBatch> {
    const response = await api.post<CommitteeBatch>(`/committee/batches/${batchId}/applications`, {
      application_id: applicationId,
    });
    return response.data;
  },

  // 3. Blind Candidate Dossiers
  async getBatchApplications(batchId: string): Promise<CommitteeDossier[]> {
    const response = await api.get<CommitteeDossier[]>(`/committee/batches/${batchId}/applications`);
    return response.data;
  },

  // 4. Submit Member Review
  async submitReview(
    applicationId: string,
    batchId: string,
    payload: CommitteeReviewPayload
  ): Promise<CommitteeReviewResponse> {
    const response = await api.post<CommitteeReviewResponse>(
      `/committee/applications/${applicationId}/review`,
      payload,
      { params: { batch_id: batchId } }
    );
    return response.data;
  },

  async getApplicationReviews(applicationId: string, batchId: string): Promise<CommitteeReviewResponse[]> {
    const response = await api.get<CommitteeReviewResponse[]>(
      `/committee/applications/${applicationId}/reviews`,
      { params: { batch_id: batchId } }
    );
    return response.data;
  },

  // 5. Lock Batch Evaluations
  async lockBatchEvaluations(batchId: string): Promise<CommitteeBatch> {
    const response = await api.post<CommitteeBatch>(`/committee/batches/${batchId}/lock-evaluations`);
    return response.data;
  },

  // 6. Calculate Merit & Dynamic Ranking
  async calculateBatchMerit(batchId: string): Promise<MeritCalculationResponse> {
    const response = await api.post<MeritCalculationResponse>(`/merit/batches/${batchId}/calculate`);
    return response.data;
  },

  async getBatchRanking(batchId: string): Promise<MeritRankItem[]> {
    const response = await api.get<MeritRankItem[]>(`/merit/batches/${batchId}/ranking`);
    return response.data;
  },

  // 7. Resolve Boundary Tie
  async resolveBoundaryTie(
    batchId: string,
    payload: TieResolutionPayload
  ): Promise<{ batch_id: string; status: string }> {
    const response = await api.post(`/committee/batches/${batchId}/resolve-tie`, payload);
    return response.data;
  },

  // 8. Finalize Batch Selection
  async finalizeBatch(
    batchId: string,
    payload: BatchFinalizePayload
  ): Promise<{
    batch_id: string;
    status: string;
    selected_count: number;
    waitlisted_count: number;
    rejected_count: number;
    finalized_at: string;
  }> {
    const response = await api.post(`/committee/batches/${batchId}/finalize`, payload);
    return response.data;
  },

  async getBatchResults(batchId: string): Promise<SelectionResultItem[]> {
    const response = await api.get<SelectionResultItem[]>(`/committee/batches/${batchId}/results`);
    return response.data;
  },

  // 9. Administrative Selection Override (Admin Only)
  async selectionOverride(payload: SelectionOverridePayload): Promise<SelectionResultItem> {
    const response = await api.post<SelectionResultItem>('/committee/admin/selection-override', payload);
    return response.data;
  },

  // 10. Sanitized Applicant Result Query
  async getApplicantResult(applicationId: string): Promise<ApplicantSelectionResult> {
    const response = await api.get<ApplicantSelectionResult>(`/applications/${applicationId}/result`);
    return response.data;
  },
};

export default committeeService;
