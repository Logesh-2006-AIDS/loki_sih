import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users,
  Award,
  Layers,
  CheckCircle2,
  Lock,
  Unlock,
  Plus,
  RefreshCw,
  Eye,
  BarChart3,
  AlertTriangle,
  FileText,
} from 'lucide-react';
import { committeeService } from '../../services/committeeService';
import { CommitteeScheme, CommitteeBatch } from '../../types/committee';

export const CommitteeDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [schemes, setSchemes] = useState<CommitteeScheme[]>([]);
  const [batches, setBatches] = useState<CommitteeBatch[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [selectedSchemeId, setSelectedSchemeId] = useState<string>('');

  // Create Batch Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [batchName, setBatchName] = useState('');
  const [modalSchemeId, setModalSchemeId] = useState('');
  const [verifiedApps, setVerifiedApps] = useState<any[]>([]);
  const [selectedAppIds, setSelectedAppIds] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const [fetchedSchemes, fetchedBatches] = await Promise.all([
        committeeService.getCommitteeSchemes(),
        committeeService.getBatches(selectedSchemeId || undefined),
      ]);
      setSchemes(fetchedSchemes);
      setBatches(fetchedBatches);
    } catch (err: any) {
      console.error('Failed to load committee dashboard', err);
      setErrorMsg(err.response?.data?.message || err.message || 'Failed to load committee dashboard data.');
    } finally {
      setIsLoading(false);
    }
  }, [selectedSchemeId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Aggregate Metrics
  const totalVerified = schemes.reduce((sum, s) => sum + s.verified_applications_count, 0);
  const totalFinalized = schemes.reduce((sum, s) => sum + s.finalized_count, 0);
  const totalBatches = batches.length;

  const handleOpenCreateModal = async () => {
    setIsModalOpen(true);
    if (schemes.length > 0) {
      const firstScheme = schemes[0];
      setModalSchemeId(firstScheme.scheme_id);
      setBatchName(`Cohort-${firstScheme.scheme_code}-${new Date().toLocaleDateString('en-GB').replace(/\//g, '')}`);
      // Load verified apps for this scheme
      try {
        const res = await fetch(`/api/v1/applications?scheme_id=${firstScheme.scheme_id}&status=VERIFIED`, {
          headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
        });
        if (res.ok) {
          const data = await res.json();
          const items = Array.isArray(data) ? data : data.items || [];
          setVerifiedApps(items);
          setSelectedAppIds(items.map((a: any) => a.id));
        }
      } catch (e) {
        console.error('Failed to load verified applications', e);
      }
    }
  };

  const handleModalSchemeChange = async (schemeId: string) => {
    setModalSchemeId(schemeId);
    const sch = schemes.find((s) => s.scheme_id === schemeId);
    if (sch) {
      setBatchName(`Cohort-${sch.scheme_code}-${new Date().toLocaleDateString('en-GB').replace(/\//g, '')}`);
    }
    try {
      const res = await fetch(`/api/v1/applications?scheme_id=${schemeId}&status=VERIFIED`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      if (res.ok) {
        const data = await res.json();
        const items = Array.isArray(data) ? data : data.items || [];
        setVerifiedApps(items);
        setSelectedAppIds(items.map((a: any) => a.id));
      }
    } catch (e) {
      console.error('Failed to load verified applications', e);
    }
  };

  const handleCreateBatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!batchName.trim() || !modalSchemeId || selectedAppIds.length === 0) {
      alert('Please provide a batch name, scheme, and select at least one verified candidate.');
      return;
    }
    const sch = schemes.find((s) => s.scheme_id === modalSchemeId);
    if (!sch || !sch.scheme_version_id) {
      alert('Selected scheme does not have an active scheme version.');
      return;
    }

    setIsSubmitting(true);
    try {
      await committeeService.createBatch({
        name: batchName.trim(),
        scheme_id: sch.scheme_id,
        scheme_version_id: sch.scheme_version_id,
        application_ids: selectedAppIds,
      });
      setIsModalOpen(false);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.message || 'Failed to create evaluation cohort batch');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 pb-20">
      {/* Top Banner / Disclaimer */}
      <div className="bg-gradient-to-r from-indigo-900 via-slate-900 to-indigo-950 text-white border-b border-indigo-800/40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-200 border border-indigo-400/30">
                  Phase 6 Scrutiny Engine
                </span>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-400/30">
                  Prototype Demo
                </span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
                Selection Committee Scrutiny & Merit Console
              </h1>
              <p className="mt-1 text-slate-300 text-sm max-w-3xl">
                Ministry of Tribal Affairs — Conduct peer-blind qualitative evaluations, enforce strict per-candidate quorum, dynamic tie-breaking, and finalize merit rankings.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={fetchData}
                disabled={isLoading}
                className="inline-flex items-center gap-2 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium rounded-lg border border-slate-700 transition"
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
              <button
                onClick={handleOpenCreateModal}
                className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg shadow-sm transition"
              >
                <Plus className="w-4 h-4" />
                New Evaluation Cohort
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 -mt-6">
        {/* Metrics Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200/80 p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Assigned Schemes</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{schemes.length}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <Layers className="w-6 h-6" />
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-slate-200/80 p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Verified Pool</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{totalVerified}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Users className="w-6 h-6" />
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-slate-200/80 p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Cohorts</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{totalBatches}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <FileText className="w-6 h-6" />
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-slate-200/80 p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Finalized Selections</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{totalFinalized}</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <Award className="w-6 h-6" />
            </div>
          </div>
        </div>

        {errorMsg && (
          <div className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Assigned Schemes Workload Overview */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200/80 overflow-hidden mb-8">
          <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Assigned Schemes & Scrutiny Workloads</h2>
              <p className="text-xs text-slate-500 mt-0.5">Schemes where your profile has active committee jurisdiction</p>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-left font-semibold text-slate-700">Scheme</th>
                  <th className="px-6 py-3 text-left font-semibold text-slate-700">Version</th>
                  <th className="px-6 py-3 text-center font-semibold text-slate-700">Quorum Rule</th>
                  <th className="px-6 py-3 text-center font-semibold text-slate-700">Verified Pool</th>
                  <th className="px-6 py-3 text-center font-semibold text-slate-700">Ranked</th>
                  <th className="px-6 py-3 text-center font-semibold text-slate-700">Finalized</th>
                  <th className="px-6 py-3 text-right font-semibold text-slate-700">Cohorts</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {schemes.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-8 text-center text-slate-400">
                      No active committee scheme assignments found.
                    </td>
                  </tr>
                ) : (
                  schemes.map((s) => (
                    <tr key={s.scheme_id} className="hover:bg-slate-50/80 transition">
                      <td className="px-6 py-4">
                        <div className="font-semibold text-slate-900">{s.scheme_code}</div>
                        <div className="text-xs text-slate-500">{s.scheme_name}</div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-800">
                          v{s.scheme_version}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <span className="font-medium text-slate-800">{s.required_quorum} reviews / app</span>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          {s.verified_applications_count}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                          {s.merit_ranked_count}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">
                          {s.finalized_count}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right font-medium text-slate-700">
                        {s.batches_count} batches
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Evaluation Cohort Batches */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200/80 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Evaluation Cohort Batches</h2>
              <p className="text-xs text-slate-500 mt-0.5">Immutable candidate batches for committee scrutiny and ranking</p>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={selectedSchemeId}
                onChange={(e) => setSelectedSchemeId(e.target.value)}
                className="text-xs border border-slate-300 rounded-lg px-3 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">All Schemes</option>
                {schemes.map((s) => (
                  <option key={s.scheme_id} value={s.scheme_id}>
                    {s.scheme_code}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-left font-semibold text-slate-700">Cohort Name</th>
                  <th className="px-6 py-3 text-center font-semibold text-slate-700">Candidates</th>
                  <th className="px-6 py-3 text-center font-semibold text-slate-700">Reviews Done</th>
                  <th className="px-6 py-3 text-center font-semibold text-slate-700">Evaluation State</th>
                  <th className="px-6 py-3 text-center font-semibold text-slate-700">Created Date</th>
                  <th className="px-6 py-3 text-right font-semibold text-slate-700">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {batches.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-slate-400">
                      <Layers className="w-8 h-8 mx-auto text-slate-300 mb-2" />
                      No candidate cohorts created yet. Click "New Evaluation Cohort" to begin.
                    </td>
                  </tr>
                ) : (
                  batches.map((b) => (
                    <tr key={b.id} className="hover:bg-slate-50/80 transition">
                      <td className="px-6 py-4">
                        <div className="font-semibold text-slate-900">{b.name}</div>
                        <div className="text-xs text-slate-400 font-mono">{b.id.slice(0, 8)}...</div>
                      </td>
                      <td className="px-6 py-4 text-center font-medium text-slate-800">
                        {b.application_count}
                      </td>
                      <td className="px-6 py-4 text-center">
                        <span className="font-medium text-slate-700">{b.reviews_completed_count}</span>
                      </td>
                      <td className="px-6 py-4 text-center">
                        {b.status === 'FINALIZED' ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <CheckCircle2 className="w-3 h-3" /> Finalized
                          </span>
                        ) : b.is_locked ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                            <Lock className="w-3 h-3" /> Locked for Ranking
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                            <Unlock className="w-3 h-3" /> Open for Scrutiny
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-center text-xs text-slate-500">
                        {new Date(b.created_at).toLocaleDateString('en-GB')}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="inline-flex items-center gap-2">
                          <button
                            onClick={() => navigate(`/committee/batches/${b.id}/queue`)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            Scrutiny Queue
                          </button>
                          <button
                            onClick={() => navigate(`/committee/batches/${b.id}/ranking`)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition"
                          >
                            <BarChart3 className="w-3.5 h-3.5" />
                            Ranking Console
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Modal: Create Candidate Cohort Batch */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full p-6 border border-slate-200 max-h-[90vh] flex flex-col">
            <h3 className="text-lg font-bold text-slate-900">Create Candidate Cohort Batch</h3>
            <p className="text-xs text-slate-500 mt-1 mb-4">
              Cohorts bind verified candidates to an evaluation cycle. Membership becomes permanently immutable once reviews begin.
            </p>

            <form onSubmit={handleCreateBatch} className="space-y-4 flex-1 overflow-y-auto pr-1">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Select Scheme</label>
                <select
                  value={modalSchemeId}
                  onChange={(e) => handleModalSchemeChange(e.target.value)}
                  className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 bg-white text-slate-800 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  required
                >
                  {schemes.map((s) => (
                    <option key={s.scheme_id} value={s.scheme_id}>
                      {s.scheme_code} - {s.scheme_name} (v{s.scheme_version})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Cohort Batch Name</label>
                <input
                  type="text"
                  value={batchName}
                  onChange={(e) => setBatchName(e.target.value)}
                  placeholder="e.g. Cohort-NFST-2026-Batch1"
                  className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  required
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-xs font-semibold text-slate-700">
                    Verified Candidates ({selectedAppIds.length} of {verifiedApps.length} selected)
                  </label>
                  <button
                    type="button"
                    onClick={() =>
                      setSelectedAppIds(
                        selectedAppIds.length === verifiedApps.length
                          ? []
                          : verifiedApps.map((a: any) => a.id)
                      )
                    }
                    className="text-xs text-indigo-600 font-semibold hover:underline"
                  >
                    {selectedAppIds.length === verifiedApps.length ? 'Deselect All' : 'Select All'}
                  </button>
                </div>

                <div className="border border-slate-200 rounded-lg max-h-48 overflow-y-auto divide-y divide-slate-100 p-2">
                  {verifiedApps.length === 0 ? (
                    <p className="text-xs text-slate-400 py-4 text-center">
                      No verified candidates available for this scheme.
                    </p>
                  ) : (
                    verifiedApps.map((app: any) => (
                      <label
                        key={app.id}
                        className="flex items-center gap-3 p-2 hover:bg-slate-50 rounded cursor-pointer text-xs"
                      >
                        <input
                          type="checkbox"
                          checked={selectedAppIds.includes(app.id)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedAppIds([...selectedAppIds, app.id]);
                            } else {
                              setSelectedAppIds(selectedAppIds.filter((id) => id !== app.id));
                            }
                          }}
                          className="rounded text-indigo-600 focus:ring-indigo-500"
                        />
                        <div className="flex-1">
                          <span className="font-semibold text-slate-900">{app.reference_id}</span>
                          <span className="text-slate-500 ml-2">
                            {app.form_data?.personal?.full_name || 'Applicant'}
                          </span>
                        </div>
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          VERIFIED
                        </span>
                      </label>
                    ))
                  )}
                </div>
              </div>

              <div className="pt-4 border-t border-slate-200 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-sm text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || selectedAppIds.length === 0}
                  className="px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition disabled:opacity-50"
                >
                  {isSubmitting ? 'Creating Cohort...' : 'Create Cohort'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default CommitteeDashboard;
