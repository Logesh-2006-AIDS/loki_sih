import api from './api';
import {
  SystemOverviewMetrics,
  ApplicationFunnelResponse,
  VelocityTrendsResponse,
  SchemeBreakdownsResponse,
  OfficerThroughputResponse,
  VerificationDecisionMetrics,
  AuditLogReportResponse,
} from '../types/analytics';

export const analyticsService = {
  async getSystemOverview(params?: {
    scheme_id?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<SystemOverviewMetrics> {
    const res = await api.get<SystemOverviewMetrics>('/analytics/overview', { params });
    return res.data;
  },

  async getApplicationFunnel(scheme_id?: string): Promise<ApplicationFunnelResponse> {
    const res = await api.get<ApplicationFunnelResponse>('/analytics/funnel', {
      params: scheme_id ? { scheme_id } : {},
    });
    return res.data;
  },

  async getVelocityTrends(params?: {
    scheme_id?: string;
    start_date?: string;
    end_date?: string;
    granularity?: string;
  }): Promise<VelocityTrendsResponse> {
    const res = await api.get<VelocityTrendsResponse>('/analytics/trends', { params });
    return res.data;
  },

  async getSchemeBreakdowns(scheme_id?: string): Promise<SchemeBreakdownsResponse> {
    const res = await api.get<SchemeBreakdownsResponse>('/analytics/schemes', {
      params: scheme_id ? { scheme_id } : {},
    });
    return res.data;
  },

  async getOfficerThroughput(params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<OfficerThroughputResponse> {
    const res = await api.get<OfficerThroughputResponse>('/analytics/officers', { params });
    return res.data;
  },

  async getDecisionMetrics(params?: {
    scheme_id?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<VerificationDecisionMetrics> {
    const res = await api.get<VerificationDecisionMetrics>('/analytics/decisions', { params });
    return res.data;
  },

  async getAuditLogs(params?: {
    action?: string;
    entity_type?: string;
    actor_id?: string;
    application_id?: string;
    start_date?: string;
    end_date?: string;
    page?: number;
    limit?: number;
  }): Promise<AuditLogReportResponse> {
    const res = await api.get<AuditLogReportResponse>('/analytics/audit-logs', { params });
    return res.data;
  },

  async downloadApplicationsCsv(params?: {
    scheme_id?: string;
    status?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
  }): Promise<void> {
    const res = await api.get('/analytics/export/applications', {
      params,
      responseType: 'blob',
    });
    const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `mta_applications_export_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  async downloadAuditLogsCsv(params?: {
    action?: string;
    entity_type?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
  }): Promise<void> {
    const res = await api.get('/analytics/export/audit-logs', {
      params,
      responseType: 'blob',
    });
    const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `mta_audit_logs_export_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
};

export default analyticsService;
