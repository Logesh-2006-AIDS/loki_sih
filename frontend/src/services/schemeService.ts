import api from './api';
import {
  Scheme,
  SchemeDetail,
  SchemeVersion,
  EligibilityCheckResponse,
} from '../types/scheme';

export const schemeService = {
  async getSchemes(): Promise<Scheme[]> {
    const res = await api.get<Scheme[]>('/schemes/');
    return res.data;
  },

  async getScheme(id: string): Promise<SchemeDetail> {
    const res = await api.get<SchemeDetail>(`/schemes/${id}`);
    return res.data;
  },

  async getSchemeVersions(schemeId: string): Promise<SchemeVersion[]> {
    const res = await api.get<SchemeVersion[]>(`/schemes/${schemeId}/versions`);
    return res.data;
  },

  async getSchemeVersion(versionId: string): Promise<SchemeVersion> {
    const res = await api.get<SchemeVersion>(`/schemes/versions/${versionId}`);
    return res.data;
  },

  async checkEligibility(
    schemeId: string,
    answers: Record<string, any>,
    schemeVersionId?: string
  ): Promise<EligibilityCheckResponse> {
    const res = await api.post<EligibilityCheckResponse>(
      `/schemes/${schemeId}/check-eligibility`,
      {
        answers,
        scheme_version_id: schemeVersionId,
      }
    );
    return res.data;
  },

  async createSchemeVersion(
    schemeId: string,
    data: {
      scheme_version: string;
      name?: string;
      description?: string;
      is_demo?: boolean;
      eligibility_rules: Record<string, any>;
      form_schema?: Record<string, any>;
      required_documents?: Record<string, any>;
      scoring_weights?: Record<string, any>;
      is_active?: boolean;
    }
  ): Promise<SchemeVersion> {
    const res = await api.post<SchemeVersion>(
      `/schemes/${schemeId}/versions`,
      data
    );
    return res.data;
  },

  async updateSchemeVersion(
    versionId: string,
    data: {
      name?: string;
      description?: string;
      is_demo?: boolean;
      eligibility_rules?: Record<string, any>;
      form_schema?: Record<string, any>;
      required_documents?: Record<string, any>;
      scoring_weights?: Record<string, any>;
    }
  ): Promise<SchemeVersion> {
    const res = await api.put<SchemeVersion>(
      `/schemes/versions/${versionId}`,
      data
    );
    return res.data;
  },

  async lockSchemeVersion(versionId: string): Promise<SchemeVersion> {
    const res = await api.post<SchemeVersion>(
      `/schemes/versions/${versionId}/lock`
    );
    return res.data;
  },

  async activateSchemeVersion(versionId: string): Promise<SchemeVersion> {
    const res = await api.post<SchemeVersion>(
      `/schemes/versions/${versionId}/activate`
    );
    return res.data;
  },
};
