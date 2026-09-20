import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  ArrowRight,
  Plus,
  RefreshCw,
  Award,
  Bot,
  UserCheck,
  AlertTriangle,
  CheckCircle2,
  Clock,
  XCircle,
  X,
  ShieldCheck,
  FileCheck,
} from 'lucide-react';
import { Application } from '../../types/application';
import { Scheme } from '../../types/scheme';
import { applicationService } from '../../services/applicationService';
import { schemeService } from '../../services/schemeService';
import { authService } from '../../services/authService';
import { committeeService } from '../../services/committeeService';
import { ApplicantSelectionResult } from '../../types/committee';
import { DeficiencyBanner } from '../../components/deficiency/DeficiencyBanner';

export const ApplicantDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [applications, setApplications] = useState<Application[]>([]);
  const [schemesMap, setSchemesMap] = useState<Record<string, Scheme>>({});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'ALL' | 'DRAFT' | 'SUBMITTED'>('ALL');
  const [activeResult, setActiveResult] = useState<{
    applicationId: string;
    schemeTitle: string;
    result: ApplicantSelectionResult;
  } | null>(null);
  const [resultLoadingId, setResultLoadingId] = useState<string | null>(null);
  const currentUser = authService.getCurrentUser();

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [apps, schemes] = await Promise.all([
        applicationService.getApplications(),
        schemeService.getSchemes(),
      ]);

      setApplications(apps);
      const sMap: Record<string, Scheme> = {};
      schemes.forEach((s) => {
        sMap[s.id] = s;
      });
      setSchemesMap(sMap);
    } catch (err) {
      console.error('Failed to load applicant dashboard', err);
    } finally {
      setLoading(false);
    }
  };

  const handleViewResult = async (appId: string, schemeTitle: string) => {
    try {
      setResultLoadingId(appId);
      const res = await committeeService.getApplicantResult(appId);
      setActiveResult({ applicationId: appId, schemeTitle, result: res });
    } catch (err: any) {
      console.error('Failed to load selection result', err);
      alert(err.response?.data?.error || 'Official result not yet published for this application.');
    } finally {
      setResultLoadingId(null);
    }
  };

  const drafts = applications.filter((a) => a.status === 'DRAFT');
  const submitted = applications.filter((a) => a.status !== 'DRAFT');
  const deficientApps = applications.filter((a) => a.status === 'DEFICIENT');

  const filteredApps = applications.filter((a) => {
    if (filter === 'DRAFT') return a.status === 'DRAFT';
    if (filter === 'SUBMITTED') return a.status !== 'DRAFT';
    return true;
  });

  const getStatusBadge = (status: string) => {
    if (status === 'DRAFT') {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">
          INCOMPLETE DRAFT
        </span>
      );
    }
    if (status === 'DEFICIENT') {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300 flex items-center gap-1">
          <AlertTriangle className="w-3 h-3 text-amber-600" />
          DEFICIENCIES FLAGGED
        </span>
      );
    }
    if (status === 'RESUBMITTED') {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-teal-100 text-teal-900 border border-teal-300 flex items-center gap-1">
          <RefreshCw className="w-3 h-3 text-teal-600" />
          RESUBMITTED
        </span>
      );
    }
    if (status === 'UNDER_AI_VERIFICATION') {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-800 border border-blue-200 flex items-center gap-1">
          <Bot className="w-3 h-3 text-blue-600" />
          UNDER AI VERIFICATION
        </span>
      );
    }
    if (status === 'UNDER_MANUAL_REVIEW') {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-200 flex items-center gap-1">
          <UserCheck className="w-3 h-3 text-purple-600" />
          UNDER MANUAL REVIEW
        </span>
      );
    }
    if (status === 'VERIFIED') {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-teal-100 text-teal-800 border border-teal-200 flex items-center gap-1">
          <FileCheck className="w-3 h-3 text-teal-600" />
          VERIFIED
        </span>
      );
    }
    if (status === 'MERIT_RANKED') {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-indigo-100 text-indigo-800 border border-indigo-200 flex items-center gap-1">
          <Award className="w-3 h-3 text-indigo-600" />
          MERIT RANKED
        </span>
      );
    }
    if (status === 'SELECTED') {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-900 border border-emerald-300 flex items-center gap-1">
          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
          OFFICIALLY SELECTED
        </span>
      );
    }
    if (status === 'WAITLISTED') {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300 flex items-center gap-1">
          <Clock className="w-3 h-3 text-amber-600" />
          PROVISIONALLY WAITLISTED
        </span>
      );
    }
    if (status === 'REJECTED') {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-300 flex items-center gap-1">
          <XCircle className="w-3 h-3 text-slate-500" />
          NOT SELECTED
        </span>
      );
    }
    return (
      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-800 border border-slate-200">
        {status.replace(/_/g, ' ')}
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Dashboard Banner */}
        <div className="bg-slate-900 text-white p-6 sm:p-8 rounded-2xl shadow-sm border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <span className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-teal-500/20 text-teal-300 border border-teal-500/40 uppercase tracking-wider">
              Applicant Portal
            </span>
            <h1 className="text-xl sm:text-2xl font-extrabold tracking-tight mt-2">
              {currentUser?.full_name ? `${currentUser.full_name}'s Applications` : 'My Scholarship Applications'}
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 mt-1">
              Track your application dossiers, complete saved drafts, and view verification progress.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={loadDashboardData}
              className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-semibold transition-colors flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <Link
              to="/"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-teal-700 hover:bg-teal-800 text-white text-xs font-bold transition-all shadow-sm"
            >
              <Plus className="w-4 h-4" />
              Apply for Scheme
            </Link>
          </div>
        </div>

        {/* Active Deficiencies Alert Banner (Phase 5) */}
        {deficientApps.length > 0 && (
          <DeficiencyBanner
            applicationId={deficientApps[0].id}
            referenceId={deficientApps[0].reference_id}
            deficiencyCount={deficientApps.length}
          />
        )}

        {/* Metric Summary Cards */}
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white p-4 sm:p-5 rounded-xl border border-slate-200 shadow-sm">
            <span className="text-[11px] font-semibold text-slate-500 block">
              Total Dossiers
            </span>
            <span className="text-xl sm:text-2xl font-black text-slate-900 mt-1 block">
              {applications.length}
            </span>
          </div>

          <div className="bg-white p-4 sm:p-5 rounded-xl border border-slate-200 shadow-sm">
            <span className="text-[11px] font-semibold text-amber-700 block">
              Incomplete Drafts
            </span>
            <span className="text-xl sm:text-2xl font-black text-amber-900 mt-1 block">
              {drafts.length}
            </span>
          </div>

          <div className="bg-white p-4 sm:p-5 rounded-xl border border-slate-200 shadow-sm">
            <span className="text-[11px] font-semibold text-blue-700 block">
              Submitted / Under Review
            </span>
            <span className="text-xl sm:text-2xl font-black text-blue-900 mt-1 block">
              {submitted.length}
            </span>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
          <button
            onClick={() => setFilter('ALL')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              filter === 'ALL'
                ? 'bg-slate-900 text-white shadow-sm'
                : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
            }`}
          >
            All Applications ({applications.length})
          </button>
          <button
            onClick={() => setFilter('DRAFT')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              filter === 'DRAFT'
                ? 'bg-slate-900 text-white shadow-sm'
                : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
            }`}
          >
            Saved Drafts ({drafts.length})
          </button>
          <button
            onClick={() => setFilter('SUBMITTED')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              filter === 'SUBMITTED'
                ? 'bg-slate-900 text-white shadow-sm'
                : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
            }`}
          >
            Submitted ({submitted.length})
          </button>
        </div>

        {/* Application Cards List */}
        {loading ? (
          <div className="p-12 text-center bg-white rounded-2xl border border-slate-200">
            <div className="inline-block w-7 h-7 border-3 border-teal-600 border-t-transparent rounded-full animate-spin"></div>
            <p className="mt-3 text-xs text-slate-500">Loading your applications...</p>
          </div>
        ) : filteredApps.length === 0 ? (
          <div className="p-12 text-center bg-white rounded-2xl border border-slate-200 space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-teal-50 text-teal-700 flex items-center justify-center mx-auto font-bold">
              <Award className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-slate-900">
              No applications found in this category
            </h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              You haven't started any applications matching this filter. Explore available MoTA fellowship programs to begin.
            </p>
            <Link
              to="/"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-teal-700 hover:bg-teal-800 text-white text-xs font-bold transition-all shadow-sm mt-2"
            >
              <Plus className="w-4 h-4" />
              Explore Schemes
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredApps.map((app) => {
              const scheme = schemesMap[app.scheme_id];
              const schemeTitle = scheme?.name || 'MoTA Fellowship Program';
              const schemeCode = scheme?.scheme_code || 'MTA';
              const isDraft = app.status === 'DRAFT';

              const updatedDate = new Date(app.updated_at).toLocaleDateString('en-IN', {
                day: '2-digit',
                month: 'short',
                year: 'numeric',
              });

              return (
                <div
                  key={app.id}
                  className="bg-white p-5 sm:p-6 rounded-2xl border border-slate-200 shadow-sm hover:border-teal-300 transition-all space-y-4"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-900 text-white">
                          {schemeCode}
                        </span>
                        {getStatusBadge(app.status)}
                        <span className="text-[11px] font-mono text-slate-400">
                          {app.reference_id}
                        </span>
                      </div>
                      <h3 className="text-base font-bold text-slate-900 mt-1.5">
                        {schemeTitle}
                      </h3>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Last modified: {updatedDate}
                      </p>
                    </div>

                    <div className="shrink-0 flex items-center gap-2 flex-wrap">
                      {['SELECTED', 'WAITLISTED', 'REJECTED'].includes(app.status) && (
                        <button
                          type="button"
                          onClick={() => handleViewResult(app.id, schemeTitle)}
                          disabled={resultLoadingId === app.id}
                          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-bold transition-all shadow-sm bg-purple-700 hover:bg-purple-800 text-white"
                        >
                          {resultLoadingId === app.id ? (
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Award className="w-3.5 h-3.5" />
                          )}
                          <span>Official Result</span>
                        </button>
                      )}
                      {app.status === 'DEFICIENT' && (
                        <button
                          type="button"
                          onClick={() => navigate(`/applications/${app.id}/deficiencies`)}
                          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold transition-all shadow-sm bg-amber-600 hover:bg-amber-700 text-white"
                        >
                          <AlertTriangle className="w-3.5 h-3.5" />
                          <span>Resolve Deficiencies</span>
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => navigate(`/applications/${app.id}`)}
                        className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all shadow-sm ${
                          isDraft
                            ? 'bg-amber-600 hover:bg-amber-700 text-white'
                            : app.status === 'DEFICIENT'
                            ? 'bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300'
                            : 'bg-teal-700 hover:bg-teal-800 text-white'
                        }`}
                      >
                        <span>{isDraft ? 'Continue Application' : 'View & Track Status'}</span>
                        <ArrowRight className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Sanitized Official Selection Result Modal */}
        {activeResult && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-5 animate-in fade-in zoom-in duration-150">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-purple-100 text-purple-700 flex items-center justify-center font-bold">
                    <Award className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">
                      Official Selection Notification
                    </h3>
                    <p className="text-[11px] text-slate-500 font-mono">
                      Ref: {activeResult.result.application_reference_id}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setActiveResult(null)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Status Showcase Card */}
              <div
                className={`p-5 rounded-xl border text-center space-y-2 ${
                  activeResult.result.result === 'SELECTED'
                    ? 'bg-emerald-50/80 border-emerald-200 text-emerald-950'
                    : activeResult.result.result === 'WAITLISTED'
                    ? 'bg-amber-50/80 border-amber-200 text-amber-950'
                    : 'bg-slate-50 border-slate-200 text-slate-900'
                }`}
              >
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-full mx-auto shadow-sm">
                  {activeResult.result.result === 'SELECTED' && (
                    <CheckCircle2 className="w-10 h-10 text-emerald-600" />
                  )}
                  {activeResult.result.result === 'WAITLISTED' && (
                    <Clock className="w-10 h-10 text-amber-600" />
                  )}
                  {activeResult.result.result === 'REJECTED' && (
                    <XCircle className="w-10 h-10 text-slate-500" />
                  )}
                </div>

                <div className="text-lg font-black tracking-tight">
                  {activeResult.result.result === 'SELECTED' && 'PROVISIONALLY SELECTED FOR AWARD'}
                  {activeResult.result.result === 'WAITLISTED' && 'PLACED ON OFFICIAL WAITLIST'}
                  {activeResult.result.result === 'REJECTED' && 'NOT SELECTED IN CURRENT ROUND'}
                </div>

                <p className="text-xs max-w-sm mx-auto text-slate-600">
                  {activeResult.schemeTitle}
                </p>
              </div>

              {/* Merit and Cohort Details */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <span className="text-[11px] font-semibold text-slate-500 block">
                    Final Merit Rank
                  </span>
                  <span className="text-lg font-bold text-slate-900 mt-0.5 block">
                    {activeResult.result.rank ? `#${activeResult.result.rank}` : 'Unranked'}
                  </span>
                </div>
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <span className="text-[11px] font-semibold text-slate-500 block">
                    Selection Round
                  </span>
                  <span className="text-lg font-bold text-slate-900 mt-0.5 block">
                    Round {activeResult.result.selection_round}
                  </span>
                </div>
              </div>

              {/* Statutory Notice */}
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-[11px] text-slate-600 space-y-1.5">
                <div className="flex items-center gap-1.5 font-bold text-slate-800">
                  <ShieldCheck className="w-3.5 h-3.5 text-teal-600" />
                  Statutory Evaluation Notification
                </div>
                <p className="leading-relaxed">
                  Decisions have been recorded pursuant to evaluation guidelines approved by the Ministry of Tribal Affairs.
                  {activeResult.result.finalized_at && (
                    <span className="block mt-1 text-slate-500 font-mono text-[10px]">
                      Batch Finalized: {new Date(activeResult.result.finalized_at).toLocaleString('en-IN')}
                    </span>
                  )}
                </p>
                <p className="text-[10px] text-slate-500 italic mt-1">
                  * Note: Internal committee reviewer scorecards and peer remarks remain confidential under standard evaluation protocols.
                </p>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setActiveResult(null)}
                  className="px-4 py-2 rounded-lg bg-slate-900 text-white text-xs font-bold hover:bg-slate-800 transition-colors shadow-sm"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
