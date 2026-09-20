import api from './api';
import {
  PublicDeficiencyListResponse,
  DeficiencyReplacementUploadResponse,
  ApplicationResubmitRequest,
  ApplicationResubmitResponse,
} from '../types/deficiency';

export const deficiencyService = {
  getDeficiencies: async (applicationId: string): Promise<PublicDeficiencyListResponse> => {
    const response = await api.get<PublicDeficiencyListResponse>(
      `/applications/${applicationId}/deficiencies`
    );
    return response.data;
  },

  uploadReplacementDocument: async (
    applicationId: string,
    deficiencyId: string,
    file: File,
    remarks?: string
  ): Promise<DeficiencyReplacementUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    if (remarks) {
      formData.append('applicant_remarks', remarks);
    }

    const response = await api.post<DeficiencyReplacementUploadResponse>(
      `/applications/${applicationId}/deficiencies/${deficiencyId}/resolve`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  resubmitApplication: async (
    applicationId: string,
    data: ApplicationResubmitRequest
  ): Promise<ApplicationResubmitResponse> => {
    const response = await api.post<ApplicationResubmitResponse>(
      `/applications/${applicationId}/resubmit`,
      data
    );
    return response.data;
  },

  notifyPending: async (applicationId: string): Promise<{ status: string; dispatched_count: number }> => {
    const response = await api.post<{ status: string; dispatched_count: number }>(
      `/applications/${applicationId}/deficiencies/notify-pending`
    );
    return response.data;
  },
};
