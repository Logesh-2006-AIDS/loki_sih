import api from './api';
import { Application, DocumentItem } from '../types/application';

export const applicationService = {
  async getApplications(): Promise<Application[]> {
    const res = await api.get<Application[]>('/applications');
    return res.data;
  },

  async getApplication(id: string): Promise<Application> {
    const res = await api.get<Application>(`/applications/${id}`);
    return res.data;
  },

  async createDraft(schemeId: string, formData: Record<string, any> = {}): Promise<Application> {
    const res = await api.post<Application>('/applications', {
      scheme_id: schemeId,
      form_data: formData,
    });
    return res.data;
  },

  async updateDraft(id: string, formData: Record<string, any>): Promise<Application> {
    const res = await api.put<Application>(`/applications/${id}`, {
      form_data: formData,
    });
    return res.data;
  },

  async submitApplication(id: string): Promise<Application> {
    const res = await api.post<Application>(`/applications/${id}/submit`);
    return res.data;
  },

  async uploadDocument(
    applicationId: string,
    documentType: string,
    file: File
  ): Promise<DocumentItem> {
    const formData = new FormData();
    formData.append('document_type', documentType);
    formData.append('file', file);

    const res = await api.post<DocumentItem>(
      `/applications/${applicationId}/documents`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return res.data;
  },

  async listDocuments(applicationId: string): Promise<DocumentItem[]> {
    const res = await api.get<DocumentItem[]>(`/applications/${applicationId}/documents`);
    return res.data;
  },

  async deleteDocument(documentId: string): Promise<void> {
    await api.delete(`/documents/${documentId}`);
  },

  async downloadDocument(documentId: string, originalFilename = 'document.pdf'): Promise<void> {
    const res = await api.get(`/documents/${documentId}/download`, {
      responseType: 'blob',
    });
    const blobUrl = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement('a');
    link.href = blobUrl;
    link.setAttribute('download', originalFilename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(blobUrl);
  },
};
