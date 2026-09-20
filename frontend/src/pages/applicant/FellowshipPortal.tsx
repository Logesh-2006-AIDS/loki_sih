import React, { useState, useEffect } from 'react';
import {
  Calendar,
  FileText,
  DollarSign,
  AlertCircle,
  CheckCircle2,
  Send,
  ShieldCheck,
  BookOpen,
} from 'lucide-react';
import fellowshipService from '../../services/fellowshipService';
import {
  FellowshipRecord,
  RenewalSubmission,
  ProgressReport,
  DisbursementInstallment,
} from '../../types/fellowship';

export const FellowshipPortal: React.FC = () => {
  const [fellowship, setFellowship] = useState<FellowshipRecord | null>(null);
  const [renewals, setRenewals] = useState<RenewalSubmission[]>([]);
  const [progressReports, setProgressReports] = useState<ProgressReport[]>([]);
  const [disbursements, setDisbursements] = useState<DisbursementInstallment[]>([]);
  const [activeTab, setActiveTab] = useState<'disbursements' | 'renewals' | 'reports'>('disbursements');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Renewal form state
  const [renewalSummary, setRenewalSummary] = useState('');
  const [marksPercentage, setMarksPercentage] = useState('');
  const [submittingRenewal, setSubmittingRenewal] = useState(false);

  // Progress report form state
  const [reportDescription, setReportDescription] = useState('');
  const [publicationsCount, setPublicationsCount] = useState(0);
  const [presentationsCount, setPresentationsCount] = useState(0);
  const [patentsCount, setPatentsCount] = useState(0);
  const [submittingReport, setSubmittingReport] = useState(false);

  useEffect(() => {
    loadFellowshipData();
  }, []);

  const loadFellowshipData = async () => {
    setLoading(true);
    setError(null);
    try {
      const fel = await fellowshipService.getMyFellowship();
      setFellowship(fel);

      const [renList, repList, disbList] = await Promise.all([
        fellowshipService.listRenewals(fel.id),
        fellowshipService.listProgressReports(fel.id),
        fellowshipService.getDisbursements(fel.id),
      ]);
      setRenewals(renList);
      setProgressReports(repList);
      setDisbursements(disbList);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load fellowship details.');
    } finally {
      setLoading(false);
    }
  };

  const handleRenewalSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fellowship) return;
    setSubmittingRenewal(true);
    setActionMessage(null);
    try {
      const nextYear = fellowship.current_year + 1;
      await fellowshipService.submitRenewal(fellowship.id, {
        academic_year: nextYear,
        annual_progress_summary: renewalSummary,
        marks_percentage: marksPercentage ? parseFloat(marksPercentage) : undefined,
        continuation_certificate_path: `/documents/continuation_year_${nextYear}.pdf`,
      });
      setActionMessage(`Academic renewal for Year ${nextYear} submitted successfully!`);
      setRenewalSummary('');
      setMarksPercentage('');
      await loadFellowshipData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit renewal.');
    } finally {
      setSubmittingRenewal(false);
    }
  };

  const handleReportSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fellowship) return;
    setSubmittingReport(true);
    setActionMessage(null);
    try {
      await fellowshipService.submitProgressReport(fellowship.id, {
        academic_year: fellowship.current_year,
        file_path: `/reports/progress_year_${fellowship.current_year}_q.pdf`,
        description: reportDescription,
        publications_count: publicationsCount,
        presentations_count: presentationsCount,
        patents_count: patentsCount,
        supervisor_approved: true,
      });
      setActionMessage('Research progress report submitted successfully!');
      setReportDescription('');
      setPublicationsCount(0);
      setPresentationsCount(0);
      setPatentsCount(0);
      await loadFellowshipData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit progress report.');
    } finally {
      setSubmittingReport(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error || !fellowship) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-amber-50 border-l-4 border-amber-500 p-6 rounded-r-lg">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-6 h-6 text-amber-600" />
            <h3 className="text-lg font-semibold text-amber-800">Fellowship Portal Notice</h3>
          </div>
          <p className="mt-2 text-amber-700">{error || 'No active fellowship record found.'}</p>
        </div>
      </div>
    );
  }

  const tenurePercent = Math.min(100, Math.round((fellowship.current_year / fellowship.tenure_years) * 100));

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header & National Identity Card */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 rounded-2xl shadow-xl p-6 sm:p-8 text-white relative overflow-hidden border border-slate-800">
        <div className="absolute top-0 right-0 -mt-8 -mr-8 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-3">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />
                {fellowship.status}
              </span>
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                {fellowship.sanction_mode}
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
              National Fellowship Scholar Portal
            </h1>
            <p className="text-slate-300 text-sm">
              Ministry of Tribal Affairs • Government of India
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-2">
              <div className="bg-white/5 backdrop-blur-sm p-3 rounded-lg border border-white/10">
                <span className="text-xs text-slate-400 block">Fellowship Number</span>
                <span className="text-sm font-semibold tracking-wider font-mono text-indigo-300">
                  {fellowship.fellowship_number}
                </span>
              </div>
              <div className="bg-white/5 backdrop-blur-sm p-3 rounded-lg border border-white/10">
                <span className="text-xs text-slate-400 block">Sanction Order</span>
                <span className="text-sm font-semibold tracking-wider font-mono text-emerald-300 truncate block">
                  {fellowship.sanction_order_number || 'PENDING'}
                </span>
              </div>
              <div className="bg-white/5 backdrop-blur-sm p-3 rounded-lg border border-white/10">
                <span className="text-xs text-slate-400 block">Host Institution</span>
                <span className="text-sm font-semibold text-slate-100 truncate block">
                  {fellowship.institution_name || 'N/A'}
                </span>
              </div>
              <div className="bg-white/5 backdrop-blur-sm p-3 rounded-lg border border-white/10">
                <span className="text-xs text-slate-400 block">Research Guide</span>
                <span className="text-sm font-semibold text-slate-100 truncate block">
                  {fellowship.guide_name || 'N/A'}
                </span>
              </div>
            </div>
          </div>

          {/* Tenure Progress Gauge */}
          <div className="bg-white/10 backdrop-blur-md p-5 rounded-xl border border-white/15 min-w-[220px] text-center space-y-2">
            <span className="text-xs font-medium text-slate-300 uppercase tracking-wider block">
              Academic Tenure
            </span>
            <div className="text-3xl font-extrabold text-white">
              Year {fellowship.current_year}{' '}
              <span className="text-sm font-normal text-slate-300">/ {fellowship.tenure_years}</span>
            </div>
            <div className="w-full bg-slate-700/50 rounded-full h-2.5 overflow-hidden">
              <div
                className="bg-gradient-to-r from-indigo-400 to-emerald-400 h-2.5 rounded-full transition-all duration-500"
                style={{ width: `${tenurePercent}%` }}
              ></div>
            </div>
            <span className="text-xs text-emerald-300 block">{tenurePercent}% Tenure Completed</span>
          </div>
        </div>
      </div>

      {actionMessage && (
        <div className="bg-emerald-50 border-l-4 border-emerald-500 p-4 rounded-r-lg flex items-center gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-600" />
          <p className="text-sm text-emerald-800">{actionMessage}</p>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="flex space-x-8" aria-label="Tabs">
          <button
            onClick={() => setActiveTab('disbursements')}
            className={`py-4 px-1 inline-flex items-center gap-2 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'disbursements'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <DollarSign className="w-4 h-4" />
            Disbursements & Grants ({disbursements.length})
          </button>
          <button
            onClick={() => setActiveTab('renewals')}
            className={`py-4 px-1 inline-flex items-center gap-2 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'renewals'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <Calendar className="w-4 h-4" />
            Annual Academic Renewals ({renewals.length})
          </button>
          <button
            onClick={() => setActiveTab('reports')}
            className={`py-4 px-1 inline-flex items-center gap-2 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'reports'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <BookOpen className="w-4 h-4" />
            Progress Reports ({progressReports.length})
          </button>
        </nav>
      </div>

      {/* Tab 1: Disbursements */}
      {activeTab === 'disbursements' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-900">5-Year Scheduled Disbursement Ledger</h2>
            <div className="flex items-center gap-2 text-xs text-slate-500 bg-slate-100 px-3 py-1.5 rounded-full">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              Direct Benefit Transfer (DBT) Simulation
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-6 py-3 text-left font-semibold text-slate-700">Installment</th>
                    <th className="px-6 py-3 text-left font-semibold text-slate-700">Period</th>
                    <th className="px-6 py-3 text-right font-semibold text-slate-700">Stipend</th>
                    <th className="px-6 py-3 text-right font-semibold text-slate-700">Contingency</th>
                    <th className="px-6 py-3 text-right font-semibold text-slate-700">Total Grant</th>
                    <th className="px-6 py-3 text-left font-semibold text-slate-700">Status</th>
                    <th className="px-6 py-3 text-left font-semibold text-slate-700">Bank & UTR</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {disbursements.map((inst) => (
                    <tr key={inst.id} className="hover:bg-slate-50/50 transition-colors">
                      <td className="px-6 py-4 font-medium text-slate-900">
                        Year {inst.academic_year} (Inst #{inst.installment_number})
                      </td>
                      <td className="px-6 py-4 text-slate-600 text-xs">
                        {inst.period_start} to {inst.period_end}
                      </td>
                      <td className="px-6 py-4 text-right font-mono text-slate-700">
                        ₹{inst.stipend_amount.toLocaleString('en-IN')}
                      </td>
                      <td className="px-6 py-4 text-right font-mono text-slate-700">
                        ₹{inst.contingency_amount.toLocaleString('en-IN')}
                      </td>
                      <td className="px-6 py-4 text-right font-mono font-bold text-indigo-700">
                        ₹{inst.total_amount.toLocaleString('en-IN')}
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            inst.payment_status === 'SUCCESS'
                              ? 'bg-emerald-100 text-emerald-800'
                              : inst.payment_status === 'APPROVED_FOR_PAYMENT'
                              ? 'bg-blue-100 text-blue-800'
                              : inst.payment_status === 'FAILED'
                              ? 'bg-red-100 text-red-800'
                              : inst.payment_status === 'CANCELLED'
                              ? 'bg-slate-100 text-slate-600'
                              : 'bg-amber-100 text-amber-800'
                          }`}
                        >
                          {inst.payment_status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-xs font-mono text-slate-600">
                        <div>A/C: {inst.account_number_masked}</div>
                        <div className="text-slate-400">IFSC: {inst.ifsc_code}</div>
                        {inst.bank_reference_utr && (
                          <div className="text-emerald-700 font-bold mt-1">
                            UTR: {inst.bank_reference_utr}
                          </div>
                        )}
                        {inst.failure_reason && (
                          <div className="text-red-600 mt-1">{inst.failure_reason}</div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Renewals */}
      {activeTab === 'renewals' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Submission Form */}
          <div className="lg:col-span-1 bg-white p-6 rounded-xl shadow-sm border border-slate-200 space-y-4">
            <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
              <Send className="w-4 h-4 text-indigo-600" />
              Submit Annual Renewal
            </h3>
            <p className="text-xs text-slate-500">
              Annual renewal for Year {fellowship.current_year + 1} continuation. Requires academic performance summary and continuation certificate.
            </p>

            <form onSubmit={handleRenewalSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Academic Year Applying For
                </label>
                <input
                  type="text"
                  readOnly
                  value={`Year ${fellowship.current_year + 1}`}
                  className="w-full text-sm bg-slate-50 border border-slate-200 rounded-lg p-2.5 font-medium text-slate-700"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Previous Year Marks / CGPA Percentage
                </label>
                <input
                  type="number"
                  step="0.1"
                  required
                  placeholder="e.g. 78.5"
                  value={marksPercentage}
                  onChange={(e) => setMarksPercentage(e.target.value)}
                  className="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Annual Research / Coursework Summary
                </label>
                <textarea
                  required
                  rows={4}
                  placeholder="Summarize course completion, chapters drafted, or experimental progress..."
                  value={renewalSummary}
                  onChange={(e) => setRenewalSummary(e.target.value)}
                  className="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:ring-indigo-500 focus:border-indigo-500"
                ></textarea>
              </div>

              <button
                type="submit"
                disabled={submittingRenewal || fellowship.current_year >= fellowship.tenure_years}
                className="w-full py-2.5 px-4 rounded-lg bg-indigo-600 text-white font-medium text-sm hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                {submittingRenewal ? 'Submitting...' : `Submit Renewal (Year ${fellowship.current_year + 1})`}
              </button>
            </form>
          </div>

          {/* History List */}
          <div className="lg:col-span-2 space-y-4">
            <h3 className="font-bold text-slate-900 text-base">Renewal Submissions History</h3>
            {renewals.length === 0 ? (
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-8 text-center text-slate-500 text-sm">
                No annual renewals submitted yet. Submit Year 2 renewal when Year 1 completes.
              </div>
            ) : (
              <div className="space-y-4">
                {renewals.map((r) => (
                  <div
                    key={r.id}
                    className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-900">Year {r.academic_year} Renewal</span>
                        <span className="text-xs text-slate-500">(Renewal #{r.renewal_number})</span>
                      </div>
                      <span
                        className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
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
                    </div>

                    <p className="text-sm text-slate-600">{r.annual_progress_summary}</p>

                    {r.marks_percentage && (
                      <div className="text-xs font-semibold text-slate-700">
                        Coursework Marks: {r.marks_percentage}%
                      </div>
                    )}

                    {r.reviewer_remarks && (
                      <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs text-slate-700 space-y-1">
                        <span className="font-bold block">Officer Remarks:</span>
                        <span>{r.reviewer_remarks}</span>
                      </div>
                    )}

                    {r.deficiency_id && (
                      <div className="bg-amber-50 p-3 rounded-lg border border-amber-200 text-xs text-amber-800 flex items-center justify-between">
                        <span>Action Required: Renewal document flagged deficient.</span>
                        <a
                          href={`/applications/${fellowship.application_id}`}
                          className="font-bold underline text-amber-900"
                        >
                          Resolve in Application Console
                        </a>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Reports */}
      {activeTab === 'reports' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Submission Form */}
          <div className="lg:col-span-1 bg-white p-6 rounded-xl shadow-sm border border-slate-200 space-y-4">
            <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
              <FileText className="w-4 h-4 text-indigo-600" />
              Submit Progress Report
            </h3>
            <p className="text-xs text-slate-500">
              Submit quarterly/semi-annual research outputs. Progress reports do not advance academic tenure years.
            </p>

            <form onSubmit={handleReportSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Research Description & Milestones
                </label>
                <textarea
                  required
                  rows={4}
                  placeholder="Outline recent publications, data collection, or conference presentations..."
                  value={reportDescription}
                  onChange={(e) => setReportDescription(e.target.value)}
                  className="w-full text-sm border border-slate-300 rounded-lg p-2.5 focus:ring-indigo-500 focus:border-indigo-500"
                ></textarea>
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="block text-[11px] font-medium text-slate-700 mb-1">
                    Publications
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={publicationsCount}
                    onChange={(e) => setPublicationsCount(parseInt(e.target.value) || 0)}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-slate-700 mb-1">
                    Presentations
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={presentationsCount}
                    onChange={(e) => setPresentationsCount(parseInt(e.target.value) || 0)}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-slate-700 mb-1">
                    Patents
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={patentsCount}
                    onChange={(e) => setPatentsCount(parseInt(e.target.value) || 0)}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={submittingReport}
                className="w-full py-2.5 px-4 rounded-lg bg-indigo-600 text-white font-medium text-sm hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                {submittingReport ? 'Submitting...' : 'Submit Progress Report'}
              </button>
            </form>
          </div>

          {/* History List */}
          <div className="lg:col-span-2 space-y-4">
            <h3 className="font-bold text-slate-900 text-base">Submitted Progress Reports</h3>
            {progressReports.length === 0 ? (
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-8 text-center text-slate-500 text-sm">
                No periodic progress reports submitted yet.
              </div>
            ) : (
              <div className="space-y-4">
                {progressReports.map((rep) => (
                  <div
                    key={rep.id}
                    className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-900">Year {rep.academic_year} Progress Report</span>
                        <span className="text-xs text-slate-500 font-mono">
                          {new Date(rep.submitted_at).toLocaleDateString()}
                        </span>
                      </div>
                      <span
                        className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                          rep.status === 'APPROVED'
                            ? 'bg-emerald-100 text-emerald-800'
                            : rep.status === 'DEFICIENT'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-blue-100 text-blue-800'
                        }`}
                      >
                        {rep.status}
                      </span>
                    </div>

                    <p className="text-sm text-slate-600">{rep.description}</p>

                    <div className="flex items-center gap-4 text-xs font-semibold text-slate-700 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                      <span>Publications: {rep.publications_count}</span>
                      <span>•</span>
                      <span>Presentations: {rep.presentations_count}</span>
                      <span>•</span>
                      <span>Patents: {rep.patents_count}</span>
                    </div>

                    {rep.reviewer_remarks && (
                      <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs text-slate-700">
                        <span className="font-bold block">Reviewer Remarks:</span>
                        <span>{rep.reviewer_remarks}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default FellowshipPortal;
