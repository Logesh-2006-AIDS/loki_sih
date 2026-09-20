import api from './api';
import {
  OfficerQueueResponse,
  OfficerStatsResponse,
  OfficerApplicationScrutinyResponse,
  OfficerDocumentScrutinyItem,
  OfficerDocumentDecisionRequest,
  OfficerApplicationDecisionRequest,
} from '../types/officer';

export const officerService = {
  async getQueue(params: {
    status_filter?: string;
    scheme_id?: string;
    state?: string;
    search?: string;
    has_ai_flags?: boolean;
    skip?: number;
    limit?: number;
  } = {}): Promise<OfficerQueueResponse> {
    const res = await api.get<OfficerQueueResponse>('/officer/queue', { params });
    return res.data;
  },

  async getStats(): Promise<OfficerStatsResponse> {
    const res = await api.get<OfficerStatsResponse>('/officer/stats');
    return res.data;
  },

  async getScrutiny(applicationId: string): Promise<OfficerApplicationScrutinyResponse> {
    const res = await api.get<OfficerApplicationScrutinyResponse>(`/officer/applications/${applicationId}/scrutiny`);
    return res.data;
  },

  async recordDocumentDecision(
    documentId: string,
    data: OfficerDocumentDecisionRequest
  ): Promise<OfficerDocumentScrutinyItem> {
    const res = await api.post<OfficerDocumentScrutinyItem>(`/officer/documents/${documentId}/decision`, data);
    return res.data;
  },

  async recordApplicationDecision(
    applicationId: string,
    data: OfficerApplicationDecisionRequest
  ): Promise<any> {
    const res = await api.post(`/officer/applications/${applicationId}/decision`, data);
    return res.data;
  },

  async downloadDocument(documentId: string, filename = 'document.pdf'): Promise<void> {
    const res = await api.get(`/documents/${documentId}/download`, {
      responseType: 'blob',
    });
    const blobUrl = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement('a');
    link.href = blobUrl;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(blobUrl);
  },

  async getDocumentPreviewUrl(documentId: string): Promise<string> {
    const res = await api.get(`/documents/${documentId}/download`, {
      responseType: 'blob',
    });
    const contentType = typeof res.headers['content-type'] === 'string' ? res.headers['content-type'] : 'application/pdf';
    return window.URL.createObjectURL(new Blob([res.data], { type: contentType }));
  },
};
