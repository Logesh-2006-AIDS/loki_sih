import React, { useState, useEffect } from 'react';
import {
  Calendar,
  BookOpen,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Eye,
  ShieldAlert,
} from 'lucide-react';
import api from '../../services/api';
import fellowshipService from '../../services/fellowshipService';
import { RenewalSubmission, ProgressReport } from '../../types/fellowship';

export const OfficerFellowshipWorkbench: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'renewals' | 'reports'>('renewals');
  const [renewals, setRenewals] = useState<RenewalSubmission[]>([]);
  const [reports, setReports] = useState<ProgressReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Review modal state
  const [selectedItem, setSelectedItem] = useState<{
    type: 'renewal' | 'report';
    id: string;
    academicYear: number;
    summary?: string | null;
  } | null>(null);
  const [decision, setDecision] = useState<'APPROVED' | 'DEFICIENT' | 'REJECTED'>('APPROVED');
  const [remarks, setRemarks] = useState('');
  const [deficiencyReason, setDeficiencyReason] = useState('DOCUMENT_ILLEGIBLE');
  const [deficiencyMessage, setDeficiencyMessage] = useState('');
  const [reviewing, setReviewing] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    loadQueue();
  }, []);

  const loadQueue = async () => {
    setLoading(true);
    setError(null);
    try {
      // In prototype mode, fetch all renewals and reports via direct query
      // or through fellowship sub-endpoints
      const res = await api.get('/applications', { params: { status: 'FELLOWSHIP_ACTIVE' } });
      const apps = res.data.items || res.data || [];

      const renAcc: RenewalSubmission[] = [];
      const repAcc: ProgressReport[] = [];

      for (const app of apps.slice(0, 10)) {
        try {
          const fel = await api.get(`/fellowships/${app.id}`).catch(() => null);
          if (fel && fel.data) {
            const [rens, reps] = await Promise.all([
              fellowshipService.listRenewals(fel.data.id).catch(() => []),
              fellowshipService.listProgressReports(fel.data.id).catch(() => []),
            ]);
            renAcc.push(...rens);
            repAcc.push(...reps);
          }
        } catch {
          // ignore individual item errors
        }
      }

      setRenewals(renAcc);
      setReports(repAcc);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load fellowship scrutiny queue.');
    } finally {
      setLoading(false);
    }
  };

  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedItem) return;
    setReviewing(true);
    setError(null);
    try {
      if (selectedItem.type === 'renewal') {
        await fellowshipService.reviewRenewal(
          selectedItem.id,
          decision,
          remarks,
          decision === 'DEFICIENT' ? deficiencyReason : undefined,
          decision === 'DEFICIENT' ? deficiencyMessage : undefined
        );
        setSuccessMessage(`Renewal review recorded successfully (${decision}).`);
      } else {
        await fellowshipService.reviewProgressReport(
          selectedItem.id,
          decision,
          remarks,
          decision === 'DEFICIENT' ? deficiencyReason : undefined,
          decision === 'DEFICIENT' ? deficiencyMessage : undefined
        );
        setSuccessMessage(`Progress report review recorded successfully (${decision}).`);
      }
      setSelectedItem(null);
      setRemarks('');
      setDeficiencyMessage('');
      await loadQueue();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to record review decision.');
    } finally {
      setReviewing(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Officer Fellowship Scrutiny Workbench</h1>
          <p className="text-sm text-slate-500">
            Review annual academic renewals and research milestones for awarded scholars.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
            Authorized Officer Role
          </span>
        </div>
      </div>

      {successMessage && (
        <div className="bg-emerald-50 border-l-4 border-emerald-500 p-4 rounded-r-lg text-sm text-emerald-800">
          {successMessage}
        </div>
      )}

      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-r-lg text-sm text-red-800">
          {error}
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="border-b border-slate-200">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab('renewals')}
            className={`py-3 px-1 inline-flex items-center gap-2 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'renewals'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <Calendar className="w-4 h-4" />
            Annual Academic Renewals ({renewals.length})
          </button>
          <button
            onClick={() => setActiveTab('reports')}
            className={`py-3 px-1 inline-flex items-center gap-2 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'reports'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <BookOpen className="w-4 h-4" />
            Periodic Progress Reports ({reports.length})
          </button>
        </nav>
      </div>

      {/* Tab 1: Renewals Table */}
      {activeTab === 'renewals' && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left font-semibold text-slate-700">Academic Year</th>
                <th className="px-6 py-3 text-left font-semibold text-slate-700">Performance Summary</th>
                <th className="px-6 py-3 text-left font-semibold text-slate-700">Marks %</th>
                <th className="px-6 py-3 text-left font-semibold text-slate-700">Status</th>
                <th className="px-6 py-3 text-right font-semibold text-slate-700">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {renewals.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-slate-500">
                    {loading ? 'Loading renewal submissions...' : 'No renewal submissions currently pending scrutiny.'}
                  </td>
                </tr>
              ) : (
                renewals.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50/50">
                    <td className="px-6 py-4 font-bold text-slate-900">
                      Year {r.academic_year} (Ren #{r.renewal_number})
                    </td>
                    <td className="px-6 py-4 text-slate-600 max-w-xs truncate">
                      {r.annual_progress_summary || 'N/A'}
                    </td>
                    <td className="px-6 py-4 font-mono font-semibold text-slate-700">
                      {r.marks_percentage ? `${r.marks_percentage}%` : 'N/A'}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          r.status === 'APPROVED'
                            ? 'bg-emerald-100 text-emerald-800'
                            : r.status === 'DEFICIENT'
                            ? 'bg-amber-100 text-amber-800'
                            : r.status === 'REJECTED'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-blue-100 text-blue-800'
                        }`}
                      >
                        {r.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() =>
                          setSelectedItem({
                            type: 'renewal',
                            id: r.id,
                            academicYear: r.academic_year,
                            summary: r.annual_progress_summary,
                          })
                        }
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-50 text-indigo-600 hover:bg-indigo-100 transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        Scrutinize
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab 2: Progress Reports Table */}
      {activeTab === 'reports' && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left font-semibold text-slate-700">Year</th>
                <th className="px-6 py-3 text-left font-semibold text-slate-700">Research Description</th>
                <th className="px-6 py-3 text-left font-semibold text-slate-700">Outputs</th>
                <th className="px-6 py-3 text-left font-semibold text-slate-700">Status</th>
                <th className="px-6 py-3 text-right font-semibold text-slate-700">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {reports.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-slate-500">
                    No progress reports currently pending scrutiny.
                  </td>
                </tr>
              ) : (
                reports.map((rep) => (
                  <tr key={rep.id} className="hover:bg-slate-50/50">
                    <td className="px-6 py-4 font-bold text-slate-900">Year {rep.academic_year}</td>
                    <td className="px-6 py-4 text-slate-600 max-w-xs truncate">
                      {rep.description || 'N/A'}
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-700 font-mono">
                      Pubs: {rep.publications_count} • Pres: {rep.presentations_count}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          rep.status === 'APPROVED'
                            ? 'bg-emerald-100 text-emerald-800'
                            : rep.status === 'DEFICIENT'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-blue-100 text-blue-800'
                        }`}
                      >
                        {rep.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() =>
                          setSelectedItem({
                            type: 'report',
                            id: rep.id,
                            academicYear: rep.academic_year,
                            summary: rep.description,
                          })
                        }
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-50 text-indigo-600 hover:bg-indigo-100 transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        Scrutinize
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Review Modal */}
      {selectedItem && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-6 space-y-5 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="font-bold text-slate-900 text-lg">
                Scrutinize {selectedItem.type === 'renewal' ? 'Annual Renewal' : 'Progress Report'} (Year{' '}
                {selectedItem.academicYear})
              </h3>
              <button
                onClick={() => setSelectedItem(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>
            </div>

            <div className="bg-slate-50 p-3 rounded-lg text-xs text-slate-600 space-y-1">
              <span className="font-bold text-slate-700 block">Submitted Content:</span>
              <p>{selectedItem.summary || 'No detailed text summary provided.'}</p>
            </div>

            <form onSubmit={handleReviewSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Scrutiny Decision
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setDecision('APPROVED')}
                    className={`py-2 px-3 rounded-lg text-xs font-bold border transition-colors flex items-center justify-center gap-1.5 ${
                      decision === 'APPROVED'
                        ? 'bg-emerald-500 text-white border-emerald-600'
                        : 'border-slate-300 text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    <CheckCircle className="w-3.5 h-3.5" />
                    Approve
                  </button>
                  <button
                    type="button"
                    onClick={() => setDecision('DEFICIENT')}
                    className={`py-2 px-3 rounded-lg text-xs font-bold border transition-colors flex items-center justify-center gap-1.5 ${
                      decision === 'DEFICIENT'
                        ? 'bg-amber-500 text-white border-amber-600'
                        : 'border-slate-300 text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    <AlertTriangle className="w-3.5 h-3.5" />
                    Deficient
                  </button>
                  <button
                    type="button"
                    onClick={() => setDecision('REJECTED')}
                    className={`py-2 px-3 rounded-lg text-xs font-bold border transition-colors flex items-center justify-center gap-1.5 ${
                      decision === 'REJECTED'
                        ? 'bg-red-500 text-white border-red-600'
                        : 'border-slate-300 text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    Reject
                  </button>
                </div>
              </div>

              {decision === 'DEFICIENT' && (
                <div className="bg-amber-50/70 p-4 rounded-xl border border-amber-200 space-y-3">
                  <div className="flex items-center gap-2 text-xs font-bold text-amber-800">
                    <ShieldAlert className="w-4 h-4 text-amber-600" />
                    Phase 5 Deficiency Registration
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-amber-900 mb-1">
                      Deficiency Code
                    </label>
                    <select
                      value={deficiencyReason}
                      onChange={(e) => setDeficiencyReason(e.target.value)}
                      className="w-full text-xs border border-amber-300 rounded-lg p-2 bg-white"
                    >
                      <option value="DOCUMENT_ILLEGIBLE">DOCUMENT_ILLEGIBLE</option>
                      <option value="MISSING_SIGNATURE">MISSING_SUPERVISOR_SIGNATURE</option>
                      <option value="INCORRECT_MARKSHEET">INCORRECT_OR_EXPIRED_MARKSHEET</option>
                      <option value="INCOMPLETE_RESEARCH_SUMMARY">INCOMPLETE_RESEARCH_SUMMARY</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-amber-900 mb-1">
                      Applicant Message / Replacement Instructions
                    </label>
                    <textarea
                      rows={2}
                      required
                      placeholder="Specify what needs to be corrected and re-uploaded..."
                      value={deficiencyMessage}
                      onChange={(e) => setDeficiencyMessage(e.target.value)}
                      className="w-full text-xs border border-amber-300 rounded-lg p-2 bg-white"
                    ></textarea>
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Official Remarks
                </label>
                <textarea
                  rows={3}
                  required
                  placeholder="Record formal appraisal notes..."
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5"
                ></textarea>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedItem(null)}
                  className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={reviewing}
                  className="px-4 py-2 rounded-lg text-xs font-bold bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  {reviewing ? 'Recording...' : 'Confirm Decision'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default OfficerFellowshipWorkbench;
