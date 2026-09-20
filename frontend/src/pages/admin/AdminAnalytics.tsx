import React, { useState, useEffect } from 'react';
import {
  Activity,
  AlertCircle,
  Award,
  BarChart3,
  Clock,
  Download,
  FileSpreadsheet,
  Filter,
  Layers,
  RefreshCw,
  Shield,
  ShieldCheck,
  TrendingUp,
  UserCheck,
  Users,
} from 'lucide-react';
import {
  SystemOverviewMetrics,
  ApplicationFunnelResponse,
  VelocityTrendsResponse,
  SchemeBreakdownsResponse,
  OfficerThroughputResponse,
  VerificationDecisionMetrics,
  AuditLogReportResponse,
} from '../../types/analytics';
import { analyticsService } from '../../services/analyticsService';
import { schemeService } from '../../services/schemeService';
import { Scheme } from '../../types/scheme';

export const AdminAnalytics: React.FC = () => {
  const [schemes, setSchemes] = useState<Scheme[]>([]);
  const [selectedSchemeId, setSelectedSchemeId] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Analytical Data States
  const [overview, setOverview] = useState<SystemOverviewMetrics | null>(null);
  const [funnel, setFunnel] = useState<ApplicationFunnelResponse | null>(null);
  const [trends, setTrends] = useState<VelocityTrendsResponse | null>(null);
  const [schemeBreakdowns, setSchemeBreakdowns] = useState<SchemeBreakdownsResponse | null>(null);
  const [officerThroughput, setOfficerThroughput] = useState<OfficerThroughputResponse | null>(null);
  const [decisionMetrics, setDecisionMetrics] = useState<VerificationDecisionMetrics | null>(null);

  // Audit Logs Explorer States
  const [auditLogs, setAuditLogs] = useState<AuditLogReportResponse | null>(null);
  const [auditActionFilter, setAuditActionFilter] = useState<string>('');
  const [auditEntityFilter, setAuditEntityFilter] = useState<string>('');
  const [auditPage, setAuditPage] = useState<number>(1);
  const [exportingApps, setExportingApps] = useState<boolean>(false);
  const [exportingAudit, setExportingAudit] = useState<boolean>(false);

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [selectedSchemeId]);

  useEffect(() => {
    loadAuditLogs();
  }, [auditPage, auditActionFilter, auditEntityFilter]);

  const loadInitialData = async () => {
    try {
      const schemeList = await schemeService.getSchemes();
      setSchemes(schemeList);
    } catch (err: any) {
      console.error('Failed to fetch schemes list', err);
    }
  };

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = selectedSchemeId ? { scheme_id: selectedSchemeId } : undefined;

      const [overviewData, funnelData, trendsData, schemesData, officersData, decisionsData] =
        await Promise.all([
          analyticsService.getSystemOverview(params),
          analyticsService.getApplicationFunnel(selectedSchemeId || undefined),
          analyticsService.getVelocityTrends(params),
          analyticsService.getSchemeBreakdowns(selectedSchemeId || undefined),
          analyticsService.getOfficerThroughput(),
          analyticsService.getDecisionMetrics(params),
        ]);

      setOverview(overviewData);
      setFunnel(funnelData);
      setTrends(trendsData);
      setSchemeBreakdowns(schemesData);
      setOfficerThroughput(officersData);
      setDecisionMetrics(decisionsData);
    } catch (err: any) {
      console.error('Failed to load dashboard analytics', err);
      setError(err?.response?.data?.detail || 'Failed to load executive analytics.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const loadAuditLogs = async () => {
    try {
      const auditData = await analyticsService.getAuditLogs({
        action: auditActionFilter || undefined,
        entity_type: auditEntityFilter || undefined,
        page: auditPage,
        limit: 25,
      });
      setAuditLogs(auditData);
    } catch (err: any) {
      console.error('Failed to load audit logs', err);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadDashboardData();
    loadAuditLogs();
  };

  const handleExportApplications = async () => {
    try {
      setExportingApps(true);
      await analyticsService.downloadApplicationsCsv({
        scheme_id: selectedSchemeId || undefined,
        limit: 10000,
      });
    } catch (err: any) {
      alert('Failed to export applications: ' + (err?.response?.data?.detail || err.message));
    } finally {
      setExportingApps(false);
    }
  };

  const handleExportAuditLogs = async () => {
    try {
      setExportingAudit(true);
      await analyticsService.downloadAuditLogsCsv({
        action: auditActionFilter || undefined,
        entity_type: auditEntityFilter || undefined,
        limit: 10000,
      });
    } catch (err: any) {
      alert('Failed to export audit logs: ' + (err?.response?.data?.detail || err.message));
    } finally {
      setExportingAudit(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 pb-16">
      {/* Official Header */}
      <div className="bg-slate-900 text-white border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-amber-400 font-semibold mb-1">
                <span>Ministry of Tribal Affairs</span>
                <span>•</span>
                <span>Government of India</span>
              </div>
              <h1 className="text-2xl font-bold flex items-center gap-3">
                <BarChart3 className="w-7 h-7 text-indigo-400" />
                Executive Analytics & Pipeline Monitoring Desk
              </h1>
              <p className="text-sm text-slate-400 mt-1">
                Real-time operational observability, version-bound quota monitoring, and verifiable audit trails.
              </p>
            </div>

            <div className="flex items-center gap-3 flex-wrap">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-amber-500/10 text-amber-300 border border-amber-500/20 text-xs font-medium rounded-full">
                <AlertCircle className="w-3.5 h-3.5" />
                DEMO / EVALUATION SYSTEM
              </span>

              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium rounded-lg border border-slate-700 transition"
              >
                <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Container */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6">
        {/* Controls & Filter Bar */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-2 text-sm text-slate-600 font-medium">
              <Filter className="w-4 h-4 text-slate-400" />
              <span>Scope Filter:</span>
            </div>
            <select
              value={selectedSchemeId}
              onChange={(e) => setSelectedSchemeId(e.target.value)}
              className="bg-slate-50 border border-slate-300 text-slate-800 text-sm rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            >
              <option value="">All Ministry Schemes (Platform-Wide)</option>
              {schemes.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.scheme_code} — {s.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={handleExportApplications}
              disabled={exportingApps}
              className="inline-flex items-center gap-2 px-3.5 py-2 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 text-sm font-medium rounded-lg transition"
            >
              <FileSpreadsheet className="w-4 h-4 text-indigo-600" />
              {exportingApps ? 'Exporting...' : 'Export Applications CSV'}
            </button>
            <button
              onClick={handleExportAuditLogs}
              disabled={exportingAudit}
              className="inline-flex items-center gap-2 px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 text-sm font-medium rounded-lg transition"
            >
              <Download className="w-4 h-4 text-slate-600" />
              {exportingAudit ? 'Exporting...' : 'Export Audit CSV'}
            </button>
          </div>
        </div>

        {loading && (
          <div className="mb-6 p-4 bg-indigo-50 border border-indigo-200 text-indigo-700 rounded-xl flex items-center gap-3">
            <RefreshCw className="w-5 h-5 animate-spin flex-shrink-0" />
            <p className="text-sm font-medium">Loading executive analytics and pipeline metrics...</p>
          </div>
        )}

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl flex items-center gap-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <p className="text-sm font-medium">{error}</p>
          </div>
        )}

        {/* 1. Top KPI Cards */}
        {overview && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Total Applications
                </span>
                <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
                  <Layers className="w-5 h-5" />
                </div>
              </div>
              <div className="mt-3">
                <span className="text-3xl font-bold text-slate-900">{overview.total_applications}</span>
                <span className="ml-2 text-xs text-slate-500">cumulative intake</span>
              </div>
              <div className="mt-2 text-xs text-slate-500 flex items-center justify-between">
                <span>Verified Pool:</span>
                <span className="font-semibold text-slate-800">{overview.total_verified_pool}</span>
              </div>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Quota Slots & Utilization
                </span>
                <div className="p-2 bg-emerald-50 text-emerald-600 rounded-lg">
                  <Award className="w-5 h-5" />
                </div>
              </div>
              <div className="mt-3">
                <span className="text-3xl font-bold text-slate-900">{overview.active_schemes_total_quota_slots}</span>
                <span className="ml-2 text-xs font-medium text-emerald-600">
                  {overview.active_schemes_quota_utilization_rate}% utilized
                </span>
              </div>
              <div className="mt-2 text-xs text-slate-500 flex items-center justify-between">
                <span>Selected Candidates:</span>
                <span className="font-semibold text-emerald-700">{overview.total_selected}</span>
              </div>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Selection Outcomes
                </span>
                <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
                  <UserCheck className="w-5 h-5" />
                </div>
              </div>
              <div className="mt-3 flex items-baseline gap-2">
                <span className="text-3xl font-bold text-slate-900">{overview.total_selected}</span>
                <span className="text-xs text-slate-500">selected</span>
                <span className="text-sm font-semibold text-amber-600 ml-1">/ {overview.total_waitlisted} WL</span>
              </div>
              <div className="mt-2 text-xs text-slate-500 flex items-center justify-between">
                <span>Batches Finalized:</span>
                <span className="font-semibold text-slate-800">
                  {overview.finalized_evaluation_batches} of {overview.total_evaluation_batches}
                </span>
              </div>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Deficiency Cycles
                </span>
                <div className="p-2 bg-amber-50 text-amber-600 rounded-lg">
                  <Clock className="w-5 h-5" />
                </div>
              </div>
              <div className="mt-3">
                <span className="text-3xl font-bold text-slate-900">{overview.resolved_deficiencies_count}</span>
                <span className="ml-2 text-xs text-emerald-600 font-medium">resolved</span>
              </div>
              <div className="mt-2 text-xs text-slate-500 flex items-center justify-between">
                <span>Active Deficiencies:</span>
                <span className="font-semibold text-amber-700">{overview.active_deficiencies_count} open</span>
              </div>
            </div>
          </div>
        )}

        {/* 2. Current-State Distribution Bar */}
        {overview && (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 mb-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
                <Activity className="w-4 h-4 text-indigo-600" />
                Pipeline Current-State Distribution (Mutually Exclusive Ground Truth)
              </h2>
              <span className="text-xs text-slate-500 font-mono">
                Total: {overview.total_applications} Applications (100%)
              </span>
            </div>

            <div className="w-full bg-slate-100 rounded-lg h-5 flex overflow-hidden border border-slate-200">
              {Object.entries(overview.current_state_distribution).map(([stateKey, count]) => {
                if (count === 0) return null;
                const pct = (count / (overview.total_applications || 1)) * 100;
                let bg = 'bg-slate-400';
                if (stateKey === 'SUBMITTED') bg = 'bg-blue-500';
                if (stateKey === 'UNDER_AI_VERIFICATION') bg = 'bg-cyan-500';
                if (stateKey === 'UNDER_MANUAL_REVIEW') bg = 'bg-indigo-500';
                if (stateKey === 'DEFICIENT') bg = 'bg-amber-500';
                if (stateKey === 'RESUBMITTED') bg = 'bg-orange-500';
                if (stateKey === 'VERIFIED') bg = 'bg-emerald-500';
                if (stateKey === 'MERIT_RANKED') bg = 'bg-purple-500';
                if (stateKey === 'SELECTED') bg = 'bg-green-600';
                if (stateKey === 'WAITLISTED') bg = 'bg-yellow-500';
                if (stateKey === 'REJECTED') bg = 'bg-rose-500';

                return (
                  <div
                    key={stateKey}
                    style={{ width: `${pct}%` }}
                    className={`${bg} h-full transition-all duration-300 relative group cursor-pointer`}
                    title={`${stateKey}: ${count} (${pct.toFixed(1)}%)`}
                  />
                );
              })}
            </div>

            <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 text-xs">
              {Object.entries(overview.current_state_distribution).map(([stateKey, count]) => (
                <div key={stateKey} className="p-2 bg-slate-50 border border-slate-200 rounded flex flex-col">
                  <span className="text-slate-500 truncate" title={stateKey}>
                    {stateKey}
                  </span>
                  <span className="font-bold text-slate-800 text-sm mt-0.5">{count}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 3. Cumulative Lifecycle Milestone Funnel */}
        {funnel && (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 mb-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-emerald-600" />
                  Cumulative Lifecycle Milestone Funnel
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Sequential progression derived from audit logs and historical evaluation artifacts.
                </p>
              </div>
              <span className="text-xs bg-emerald-50 text-emerald-700 px-2.5 py-1 rounded-full font-medium">
                Monotonic Invariant Preserved
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
              {funnel.milestones.map((m, idx) => (
                <div
                  key={m.milestone_key}
                  className="bg-slate-50 border border-slate-200 rounded-lg p-4 flex flex-col justify-between relative"
                >
                  <div>
                    <div className="flex items-center justify-between text-xs text-slate-500 font-semibold mb-1">
                      <span>Step {idx + 1}</span>
                      <span>{m.conversion_from_start_rate}% of init</span>
                    </div>
                    <div className="text-sm font-bold text-slate-800">{m.milestone_label}</div>
                  </div>

                  <div className="mt-4">
                    <div className="text-2xl font-extrabold text-indigo-900">{m.count}</div>
                    <div className="text-xs text-slate-500 mt-1">
                      {idx === 0 ? 'Base intake pool' : `${m.conversion_from_previous_rate}% from prior step`}
                    </div>
                  </div>

                  <div className="w-full bg-slate-200 rounded-full h-1.5 mt-3 overflow-hidden">
                    <div
                      className="bg-indigo-600 h-full rounded-full"
                      style={{ width: `${m.conversion_from_start_rate}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 4. Intake, Verification & Selection Velocity Timeline */}
        {trends && trends.data_points.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 mb-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-blue-600" />
                  Intake, Verification & Selection Velocity Timeline
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Daily throughput velocity tracking intake submissions, scrutiny completions, and selections.
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600">
                <thead className="bg-slate-50 uppercase font-semibold text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="px-3 py-2.5">Date</th>
                    <th className="px-3 py-2.5">Applications Submitted</th>
                    <th className="px-3 py-2.5">Officer Verifications</th>
                    <th className="px-3 py-2.5">Selections Finalized</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {trends.data_points.map((pt) => (
                    <tr key={pt.date} className="hover:bg-slate-50/80">
                      <td className="px-3 py-2 font-mono text-slate-700">{pt.date}</td>
                      <td className="px-3 py-2 font-semibold text-blue-600">{pt.submissions_count}</td>
                      <td className="px-3 py-2 font-semibold text-indigo-600">{pt.verifications_count}</td>
                      <td className="px-3 py-2 font-semibold text-emerald-600">{pt.selections_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 5. Scheme & Version-Bound Performance Matrix */}
        {schemeBreakdowns && (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 mb-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
                  <Award className="w-4 h-4 text-amber-600" />
                  Scheme & Version-Bound Quota Performance
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Authoritative quotas bound to active SchemeVersion.scoring_weights configurations.
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-600">
                <thead className="bg-slate-50 text-xs uppercase font-semibold text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">Scheme Code</th>
                    <th className="px-4 py-3">Version</th>
                    <th className="px-4 py-3">Quota Slots</th>
                    <th className="px-4 py-3">Total Intake</th>
                    <th className="px-4 py-3">Verified Pool</th>
                    <th className="px-4 py-3">Selected</th>
                    <th className="px-4 py-3">Waitlisted</th>
                    <th className="px-4 py-3">Exhaustion Rate</th>
                    <th className="px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {schemeBreakdowns.schemes.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="px-4 py-6 text-center text-slate-400">
                        No active schemes available.
                      </td>
                    </tr>
                  ) : (
                    schemeBreakdowns.schemes.map((item) => (
                      <tr key={`${item.scheme_id}_${item.scheme_version_id}`} className="hover:bg-slate-50/80">
                        <td className="px-4 py-3 font-semibold text-slate-900">{item.scheme_code}</td>
                        <td className="px-4 py-3 font-mono text-xs">{item.scheme_version || '1.0'}</td>
                        <td className="px-4 py-3 font-semibold text-indigo-700">{item.quota_slots}</td>
                        <td className="px-4 py-3">{item.total_applications}</td>
                        <td className="px-4 py-3 font-medium text-emerald-600">{item.verified_count}</td>
                        <td className="px-4 py-3 font-bold text-slate-900">{item.selected_count}</td>
                        <td className="px-4 py-3 text-amber-600">{item.waitlisted_count}</td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-xs">{item.quota_exhaustion_rate}%</span>
                            <div className="w-16 bg-slate-200 rounded-full h-1.5 overflow-hidden">
                              <div
                                className={`h-full rounded-full ${
                                  item.quota_exhaustion_rate >= 100
                                    ? 'bg-red-500'
                                    : item.quota_exhaustion_rate >= 75
                                    ? 'bg-amber-500'
                                    : 'bg-emerald-500'
                                }`}
                                style={{ width: `${Math.min(item.quota_exhaustion_rate, 100)}%` }}
                              />
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`px-2 py-0.5 text-xs font-semibold rounded-full ${
                              item.is_active
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                : 'bg-slate-100 text-slate-600'
                            }`}
                          >
                            {item.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 6. Two-Column Analytics: Decision Integrity & Staff Throughput */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Decision Integrity */}
          {decisionMetrics && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-indigo-600" />
                    AI-Human Verification Integrity & Agreement
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Evaluated against completed officer scrutiny decisions in document_verifications.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="p-4 bg-emerald-50/50 border border-emerald-100 rounded-lg">
                  <span className="text-xs uppercase tracking-wider font-semibold text-emerald-700">
                    AI-Human Agreement Rate
                  </span>
                  <div className="text-3xl font-extrabold text-emerald-900 mt-1">
                    {decisionMetrics.ai_human_agreement_rate}%
                  </div>
                  <span className="text-xs text-emerald-700 mt-1 block">
                    {decisionMetrics.ai_human_agreements} of {decisionMetrics.total_documents_evaluated} verified docs
                  </span>
                </div>

                <div className="p-4 bg-indigo-50/50 border border-indigo-100 rounded-lg">
                  <span className="text-xs uppercase tracking-wider font-semibold text-indigo-700">
                    Human Override Rate
                  </span>
                  <div className="text-3xl font-extrabold text-indigo-900 mt-1">
                    {decisionMetrics.human_override_rate}%
                  </div>
                  <span className="text-xs text-indigo-700 mt-1 block">
                    {decisionMetrics.human_overrides} officer overrides recorded
                  </span>
                </div>
              </div>

              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                <span className="text-xs font-semibold text-slate-700 block mb-2">Override Breakdown</span>
                <div className="space-y-1 text-xs text-slate-600">
                  <div className="flex justify-between">
                    <span>AI Flagged → Human Officer Approved (False Positives cleared):</span>
                    <span className="font-semibold text-slate-900">
                      {decisionMetrics.override_breakdown['AI_FLAGGED_HUMAN_VERIFIED'] || 0}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>AI Verified → Human Officer Rejected (Ineligibility caught):</span>
                    <span className="font-semibold text-slate-900">
                      {decisionMetrics.override_breakdown['AI_VERIFIED_HUMAN_REJECTED'] || 0}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Staff Throughput */}
          {officerThroughput && (
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
                    <Users className="w-4 h-4 text-blue-600" />
                    Officer Verification Velocity & Throughput
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Individual throughput metrics (Admin only). Applicant PII is strictly excluded.
                  </p>
                </div>
              </div>

              <div className="overflow-y-auto max-h-72">
                <table className="w-full text-left text-sm text-slate-600">
                  <thead className="bg-slate-50 text-xs uppercase font-semibold text-slate-500 border-b border-slate-200 sticky top-0">
                    <tr>
                      <th className="px-3 py-2">Officer Name</th>
                      <th className="px-3 py-2">Scrutinized</th>
                      <th className="px-3 py-2">Verified</th>
                      <th className="px-3 py-2">Overrides</th>
                      <th className="px-3 py-2">Avg Duration</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {officerThroughput.officers.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-3 py-4 text-center text-slate-400 text-xs">
                          No active officer records found.
                        </td>
                      </tr>
                    ) : (
                      officerThroughput.officers.map((off) => (
                        <tr key={off.officer_id} className="hover:bg-slate-50/80">
                          <td className="px-3 py-2 font-medium text-slate-900">{off.officer_name}</td>
                          <td className="px-3 py-2">{off.assigned_applications_count}</td>
                          <td className="px-3 py-2 font-semibold text-emerald-600">{off.verified_count}</td>
                          <td className="px-3 py-2 text-indigo-600">{off.human_overrides_count}</td>
                          <td className="px-3 py-2 text-xs font-mono">
                            {off.avg_verification_duration_hours}h
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* 7. Searchable System Audit Trail Explorer */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
            <div>
              <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
                <Shield className="w-4 h-4 text-slate-700" />
                Platform Audit Trail Explorer
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Verifiable event log across all transactional pipelines. Passwords and credentials scrubbed.
              </p>
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              <input
                type="text"
                placeholder="Filter action (e.g. OFFICER_)"
                value={auditActionFilter}
                onChange={(e) => {
                  setAuditActionFilter(e.target.value);
                  setAuditPage(1);
                }}
                className="bg-slate-50 border border-slate-300 text-slate-800 text-xs rounded-lg px-2.5 py-1.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
              <select
                value={auditEntityFilter}
                onChange={(e) => {
                  setAuditEntityFilter(e.target.value);
                  setAuditPage(1);
                }}
                className="bg-slate-50 border border-slate-300 text-slate-800 text-xs rounded-lg px-2.5 py-1.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              >
                <option value="">All Entities</option>
                <option value="APPLICATION">APPLICATION</option>
                <option value="DOCUMENT">DOCUMENT</option>
                <option value="DEFICIENCY">DEFICIENCY</option>
                <option value="COMMITTEE">COMMITTEE</option>
                <option value="SCHEME">SCHEME</option>
                <option value="USER">USER</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 uppercase font-semibold text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-3 py-2.5">Timestamp</th>
                  <th className="px-3 py-2.5">Actor</th>
                  <th className="px-3 py-2.5">Entity</th>
                  <th className="px-3 py-2.5">Action</th>
                  <th className="px-3 py-2.5">Transition</th>
                  <th className="px-3 py-2.5">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {!auditLogs || auditLogs.logs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-3 py-6 text-center text-slate-400">
                      No audit log entries matching filters.
                    </td>
                  </tr>
                ) : (
                  auditLogs.logs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-50/80">
                      <td className="px-3 py-2 text-slate-500 font-mono whitespace-nowrap">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td className="px-3 py-2 font-medium text-slate-900">{log.actor_name || 'SYSTEM'}</td>
                      <td className="px-3 py-2">
                        <span className="px-1.5 py-0.5 bg-slate-100 text-slate-700 rounded font-mono">
                          {log.entity_type}
                        </span>
                      </td>
                      <td className="px-3 py-2 font-semibold text-slate-800">{log.action}</td>
                      <td className="px-3 py-2 font-mono text-xs">
                        {log.previous_status || log.new_status ? (
                          <span>
                            {log.previous_status || '—'} →{' '}
                            <span className="font-bold text-slate-900">{log.new_status || '—'}</span>
                          </span>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td className="px-3 py-2 max-w-xs truncate text-slate-500" title={JSON.stringify(log.details)}>
                        {JSON.stringify(log.details)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {auditLogs && auditLogs.total_count > 0 && (
            <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-100 text-xs text-slate-500">
              <div>
                Showing {(auditPage - 1) * auditLogs.limit + 1} to{' '}
                {Math.min(auditPage * auditLogs.limit, auditLogs.total_count)} of {auditLogs.total_count} events
              </div>
              <div className="flex items-center gap-2">
                <button
                  disabled={auditPage <= 1}
                  onClick={() => setAuditPage((p) => Math.max(p - 1, 1))}
                  className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 rounded"
                >
                  Previous
                </button>
                <span className="font-semibold text-slate-800">Page {auditPage}</span>
                <button
                  disabled={auditPage * auditLogs.limit >= auditLogs.total_count}
                  onClick={() => setAuditPage((p) => p + 1)}
                  className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 rounded"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminAnalytics;
