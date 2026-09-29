import api from './api';
import { StaffRequestResponse, StaffRequestStats } from '../types/userApproval';

export const userApprovalService = {
  async getStats(): Promise<StaffRequestStats> {
    const res = await api.get<StaffRequestStats>('/admin/user-approvals/stats');
    return res.data;
  },

  async listRequests(status?: string, role?: string, search?: string): Promise<StaffRequestResponse[]> {
    const params: Record<string, any> = {};
    if (status && status !== 'ALL') params.status = status;
    if (role && role !== 'ALL') params.role = role;
    if (search && search.trim()) params.search = search.trim();

    const res = await api.get<StaffRequestResponse[]>('/admin/user-approvals/', { params });
    return res.data;
  },

  async getRequest(id: string): Promise<StaffRequestResponse> {
    const res = await api.get<StaffRequestResponse>(`/admin/user-approvals/${id}`);
    return res.data;
  },

  async approveRequest(id: string): Promise<StaffRequestResponse> {
    const res = await api.post<StaffRequestResponse>(`/admin/user-approvals/${id}/approve`);
    return res.data;
  },

  async rejectRequest(id: string, reason: string): Promise<StaffRequestResponse> {
    const res = await api.post<StaffRequestResponse>(`/admin/user-approvals/${id}/reject`, { reason });
    return res.data;
  },
};
