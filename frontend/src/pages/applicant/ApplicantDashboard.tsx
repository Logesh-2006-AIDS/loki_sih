import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  ArrowRight,
  Plus,
  RefreshCw,
  Award,
  Bot,
  UserCheck,
} from 'lucide-react';
import { Application } from '../../types/application';
import { Scheme } from '../../types/scheme';
import { applicationService } from '../../services/applicationService';
import { schemeService } from '../../services/schemeService';
import { authService } from '../../services/authService';

export const ApplicantDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [applications, setApplications] = useState<Application[]>([]);
  const [schemesMap, setSchemesMap] = useState<Record<string, Scheme>>({});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'ALL' | 'DRAFT' | 'SUBMITTED'>('ALL');
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

  const drafts = applications.filter((a) => a.status === 'DRAFT');
  const submitted = applications.filter((a) => a.status !== 'DRAFT');

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

                    <div className="shrink-0">
                      <button
                        type="button"
                        onClick={() => navigate(`/applications/${app.id}`)}
                        className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all shadow-sm ${
                          isDraft
                            ? 'bg-amber-600 hover:bg-amber-700 text-white'
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
      </div>
    </div>
  );
};
