import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Lock,
  Unlock,
  CheckCircle2,
  AlertTriangle,
  Award,
  BarChart3,
  RefreshCw,
  Scale,
} from 'lucide-react';
import { committeeService } from '../../services/committeeService';
import {
  CommitteeBatch,
  MeritRankItem,
  SelectionResultItem,
} from '../../types/committee';

export const MeritRankingConsole: React.FC = () => {
  const { batchId } = useParams<{ batchId: string }>();
  const navigate = useNavigate();

  const [batch, setBatch] = useState<CommitteeBatch | null>(null);
  const [ranking, setRanking] = useState<MeritRankItem[]>([]);
  const [results, setResults] = useState<SelectionResultItem[]>([]);
  const [boundaryTieFlag, setBoundaryTieFlag] = useState(false);
  const [tiedCandidateIds, setTiedCandidateIds] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Tie Resolution Modal State
  const [isTieModalOpen, setIsTieModalOpen] = useState(false);
  const [preferredId, setPreferredId] = useState('');
  const [secondaryId, setSecondaryId] = useState('');
  const [tieRationale, setTieRationale] = useState('');
  const [tieOrderRef, setTieOrderRef] = useState('');
  const [isResolvingTie, setIsResolvingTie] = useState(false);

  // Finalization Form State
  const [isFinalizeModalOpen, setIsFinalizeModalOpen] = useState(false);
  const [resolutionRef, setResolutionRef] = useState('');
  const [committeeMinutes, setCommitteeMinutes] = useState('');
  const [meetingDate, setMeetingDate] = useState(new Date().toISOString().split('T')[0]);
  const [isFinalizing, setIsFinalizing] = useState(false);

  // Administrative Override Modal State (Admin Only)
  const [isOverrideModalOpen, setIsOverrideModalOpen] = useState(false);
  const [overrideAppId, setOverrideAppId] = useState('');
  const [targetStatus, setTargetStatus] = useState<'SELECTED' | 'REJECTED'>('SELECTED');
  const [overrideReason, setOverrideReason] = useState('');
  const [overrideAuthorityRef, setOverrideAuthorityRef] = useState('');
  const [isOverriding, setIsOverriding] = useState(false);

  const fetchConsoleData = useCallback(async () => {
    if (!batchId) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const batchData = await committeeService.getBatchDetails(batchId);
      setBatch(batchData);

      if (batchData.is_locked || batchData.status === 'FINALIZED') {
        const [rankingData, resultsData] = await Promise.all([
          committeeService.getBatchRanking(batchId).catch(() => []),
          batchData.status === 'FINALIZED'
            ? committeeService.getBatchResults(batchId).catch(() => [])
            : Promise.resolve([]),
        ]);
        setRanking(rankingData);
        setResults(resultsData);
      }
    } catch (err: any) {
      console.error('Failed to load ranking console data', err);
      setErrorMsg(err.response?.data?.message || 'Failed to load ranking console.');
    } finally {
      setIsLoading(false);
    }
  }, [batchId]);

  useEffect(() => {
    fetchConsoleData();
  }, [fetchConsoleData]);

  // Actions
  const handleLockEvaluations = async () => {
    if (!batchId) return;
    if (!window.confirm('Are you sure you want to lock committee evaluations? This verifies quorum for all candidates and permanently seals member scorecards.')) {
      return;
    }
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      await committeeService.lockBatchEvaluations(batchId);
      setSuccessMsg('Batch evaluations successfully locked. Quorum verified for all candidates.');
      fetchConsoleData();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.message || 'Failed to lock evaluations. Ensure all candidates satisfy required quorum.');
    }
  };

  const handleCalculateMerit = async () => {
    if (!batchId) return;
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const res = await committeeService.calculateBatchMerit(batchId);
      setBoundaryTieFlag(res.boundary_tie_flag);
      setTiedCandidateIds(res.tied_candidate_ids);
      setSuccessMsg(`Deterministic merit calculation completed for ${res.scored_count} candidates.`);
      const rankingData = await committeeService.getBatchRanking(batchId);
      setRanking(rankingData);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.message || 'Failed to calculate merit scores.');
    }
  };

  const handleOpenTieResolution = () => {
    if (ranking.length >= 2) {
      // Find candidate IDs from tied ids or top 2
      const candidate1 = tiedCandidateIds[0] || ranking[0]?.application_id;
      const candidate2 = tiedCandidateIds[1] || ranking[1]?.application_id;
      setPreferredId(candidate1);
      setSecondaryId(candidate2);
      setTieOrderRef(`MTA-TIE-${new Date().getFullYear()}-${Math.floor(1000 + Math.random() * 9000)}`);
      setTieRationale('');
      setIsTieModalOpen(true);
    }
  };

  const handleResolveTie = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!batchId || !preferredId || !secondaryId || !tieRationale.trim()) {
      alert('Please fill out all tie resolution fields.');
      return;
    }
    setIsResolvingTie(true);
    setErrorMsg(null);
    try {
      await committeeService.resolveBoundaryTie(batchId, {
        preferred_candidate_id: preferredId,
        secondary_candidate_id: secondaryId,
        statutory_justification: tieRationale.trim(),
        authority_order_reference: tieOrderRef.trim(),
      });
      setSuccessMsg('Boundary tie resolved cleanly by chairperson resolution.');
      setIsTieModalOpen(false);
      setBoundaryTieFlag(false);
      // Re-fetch ranking
      const rankingData = await committeeService.getBatchRanking(batchId);
      setRanking(rankingData);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.message || 'Failed to resolve boundary tie.');
    } finally {
      setIsResolvingTie(false);
    }
  };

  const handleFinalizeBatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!batchId || !resolutionRef.trim() || !committeeMinutes.trim()) {
      alert('Please provide meeting minutes and resolution order reference.');
      return;
    }
    setIsFinalizing(true);
    setErrorMsg(null);
    try {
      const res = await committeeService.finalizeBatch(batchId, {
        resolution_reference: resolutionRef.trim(),
        committee_minutes: committeeMinutes.trim(),
        meeting_date: new Date(meetingDate).toISOString(),
      });
      setSuccessMsg(`Selection finalized: ${res.selected_count} Selected, ${res.waitlisted_count} Waitlisted, ${res.rejected_count} Rejected.`);
      setIsFinalizeModalOpen(false);
      fetchConsoleData();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.message || 'Failed to finalize selection cohort.');
    } finally {
      setIsFinalizing(false);
    }
  };

  const handleAdminOverride = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!overrideAppId || !overrideReason.trim() || !overrideAuthorityRef.trim()) {
      alert('Please complete all override justification fields.');
      return;
    }
    setIsOverriding(true);
    setErrorMsg(null);
    try {
      await committeeService.selectionOverride({
        application_id: overrideAppId,
        target_status: targetStatus,
        override_reason: overrideReason.trim(),
        authority_reference: overrideAuthorityRef.trim(),
        selection_round: 2,
      });
      setSuccessMsg('Administrative selection override executed. Merit rank preserved permanently.');
      setIsOverrideModalOpen(false);
      fetchConsoleData();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.message || 'Failed to execute administrative override.');
    } finally {
      setIsOverriding(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 pb-20">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <button
            onClick={() => navigate('/committee')}
            className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-slate-800 mb-2 transition"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Committee Dashboard
          </button>
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-slate-900">
                  Merit Ranking & Allocation: <span className="text-indigo-600">{batch?.name}</span>
                </h1>
                {batch?.status === 'FINALIZED' ? (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <CheckCircle2 className="w-3 h-3" /> Finalized
                  </span>
                ) : batch?.is_locked ? (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                    <Lock className="w-3 h-3" /> Locked
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                    <Unlock className="w-3 h-3" /> Scrutiny In Progress
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Deterministic calculation driven by frozen scheme version rules snapshot.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2.5">
              <button
                onClick={fetchConsoleData}
                disabled={isLoading}
                className="inline-flex items-center gap-1.5 px-3 py-2 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium rounded-lg border border-slate-300 transition"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh
              </button>

              {!batch?.is_locked && batch?.status !== 'FINALIZED' && (
                <button
                  onClick={handleLockEvaluations}
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold rounded-lg shadow-sm transition"
                >
                  <Lock className="w-3.5 h-3.5" />
                  Lock Evaluations
                </button>
              )}

              {batch?.is_locked && batch?.status !== 'FINALIZED' && (
                <>
                  <button
                    onClick={handleCalculateMerit}
                    className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg shadow-sm transition"
                  >
                    <BarChart3 className="w-3.5 h-3.5" />
                    Calculate Merit & Rank
                  </button>
                  <button
                    onClick={() => {
                      setResolutionRef(`MTA-SEL-${new Date().getFullYear()}-001`);
                      setCommitteeMinutes('Selection Committee met in camera and scrutinized candidate dossiers.');
                      setIsFinalizeModalOpen(true);
                    }}
                    disabled={boundaryTieFlag || ranking.length === 0}
                    className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg shadow-sm transition disabled:opacity-50"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Finalize Allocation
                  </button>
                </>
              )}

              <button
                onClick={() => {
                  if (ranking.length > 0) {
                    setOverrideAppId(ranking[0].application_id);
                  }
                  setOverrideAuthorityRef(`GOI-SEC-DISP-${new Date().getFullYear()}`);
                  setIsOverrideModalOpen(true);
                }}
                className="inline-flex items-center gap-1.5 px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium rounded-lg transition"
              >
                <Scale className="w-3.5 h-3.5" />
                Admin Override
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {successMsg && (
          <div className="mb-6 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {errorMsg && (
          <div className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Boundary Tie Warning Banner */}
        {boundaryTieFlag && (
          <div className="mb-6 p-5 rounded-xl bg-amber-50 border-2 border-amber-300 text-amber-900 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-6 h-6 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-bold text-amber-900">Selection Boundary Tie Detected</h3>
                <p className="text-xs text-amber-800 mt-0.5">
                  Two or more candidates have identical scores crossing the quota cut-off boundary. Automatic quota allocation is blocked to prevent arbitrary assignment. Chairperson resolution is mandatory before finalization.
                </p>
              </div>
            </div>
            <button
              onClick={handleOpenTieResolution}
              className="inline-flex items-center gap-2 px-4 py-2 bg-amber-700 hover:bg-amber-600 text-white text-xs font-bold rounded-lg shadow-sm whitespace-nowrap transition"
            >
              <Scale className="w-4 h-4" />
              Resolve Boundary Tie
            </button>
          </div>
        )}

        {/* Dynamic Ranking Table */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200/80 overflow-hidden mb-8">
          <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900">Dynamic Merit Ranking List</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Deterministic calculation combining academic marks and consensus committee scorecard
              </p>
            </div>
            <span className="text-xs text-slate-400 font-mono">
              {ranking.length} Ranked Candidates
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-center font-semibold text-slate-700">Rank</th>
                  <th className="px-6 py-3 text-left font-semibold text-slate-700">Candidate</th>
                  <th className="px-6 py-3 text-left font-semibold text-slate-700">Reference ID</th>
                  <th className="px-6 py-3 text-center font-semibold text-slate-700">Total Score</th>
                  <th className="px-6 py-3 text-center font-semibold text-slate-700">Tie-Break Level</th>
                  <th className="px-6 py-3 text-center font-semibold text-slate-700">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {ranking.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-slate-400">
                      {batch?.is_locked
                        ? 'Evaluations are locked. Click "Calculate Merit & Rank" to generate the ranking table.'
                        : 'Cohort evaluations must be locked before merit calculation can execute.'}
                    </td>
                  </tr>
                ) : (
                  ranking.map((r) => {
                    const outcome = results.find((res) => res.application_id === r.application_id);

                    return (
                      <tr key={r.application_id} className="hover:bg-slate-50/80 transition">
                        <td className="px-6 py-4 text-center">
                          <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-slate-900 text-white text-xs font-bold">
                            {r.rank}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <div className="font-semibold text-slate-900">{r.applicant_name}</div>
                        </td>
                        <td className="px-6 py-4 font-mono text-xs text-slate-600">
                          {r.reference_id}
                        </td>
                        <td className="px-6 py-4 text-center">
                          <span className="font-mono font-bold text-indigo-600 text-base">
                            {r.total_score.toFixed(2)}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-center">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${
                              r.tie_break_level === 'CO_RANKED_TIED'
                                ? 'bg-amber-100 text-amber-800'
                                : r.tie_break_level === 'CHAIRPERSON_RESOLUTION'
                                ? 'bg-purple-100 text-purple-800'
                                : 'bg-slate-100 text-slate-700'
                            }`}
                          >
                            {r.tie_break_level || 'DIRECT_SCORE'}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-center">
                          {outcome ? (
                            <span
                              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold ${
                                outcome.result === 'SELECTED'
                                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                  : outcome.result === 'WAITLISTED'
                                  ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                  : 'bg-rose-50 text-rose-700 border border-rose-200'
                              }`}
                            >
                              {outcome.result}
                              {outcome.is_override && ' (Overridden)'}
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                              {r.status}
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Finalized Selection History & Orders (if finalized) */}
        {batch?.status === 'FINALIZED' && results.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200/80 p-6">
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-100">
              <Award className="w-5 h-5 text-emerald-600" />
              <h2 className="text-base font-bold text-slate-900">Official Finalized Outcomes</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200">
                <span className="text-emerald-800 font-semibold block mb-1">Selected Candidates</span>
                <span className="text-2xl font-bold text-emerald-900">
                  {results.filter((r) => r.result === 'SELECTED').length}
                </span>
              </div>
              <div className="p-4 rounded-xl bg-amber-50/70 border border-amber-200">
                <span className="text-amber-800 font-semibold block mb-1">Waitlisted Candidates</span>
                <span className="text-2xl font-bold text-amber-900">
                  {results.filter((r) => r.result === 'WAITLISTED').length}
                </span>
              </div>
              <div className="p-4 rounded-xl bg-rose-50/70 border border-rose-200">
                <span className="text-rose-800 font-semibold block mb-1">Non-Selected / Rejected</span>
                <span className="text-2xl font-bold text-rose-900">
                  {results.filter((r) => r.result === 'REJECTED').length}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Modal: Chairperson Boundary Tie Resolution */}
      {isTieModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-xl max-w-xl w-full p-6 border border-slate-200">
            <div className="flex items-center gap-2.5 mb-2">
              <Scale className="w-5 h-5 text-amber-600" />
              <h3 className="text-lg font-bold text-slate-900">Chairperson Tie Resolution</h3>
            </div>
            <p className="text-xs text-slate-500 mb-4">
              Break an exact boundary tie crossing the selection quota. Every tie resolution is permanently audited.
            </p>

            <form onSubmit={handleResolveTie} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Preferred Candidate (Rank 1 / Selected)</label>
                <select
                  value={preferredId}
                  onChange={(e) => setPreferredId(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white text-slate-800"
                  required
                >
                  {ranking.map((r) => (
                    <option key={r.application_id} value={r.application_id}>
                      {r.applicant_name} ({r.reference_id}) - Score {r.total_score.toFixed(2)}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Secondary Candidate (Rank 2 / Waitlisted)</label>
                <select
                  value={secondaryId}
                  onChange={(e) => setSecondaryId(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white text-slate-800"
                  required
                >
                  {ranking.map((r) => (
                    <option key={r.application_id} value={r.application_id}>
                      {r.applicant_name} ({r.reference_id}) - Score {r.total_score.toFixed(2)}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Authority Resolution Reference</label>
                <input
                  type="text"
                  value={tieOrderRef}
                  onChange={(e) => setTieOrderRef(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 text-slate-800 font-mono"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Statutory Justification / Rationale</label>
                <textarea
                  rows={3}
                  value={tieRationale}
                  onChange={(e) => setTieRationale(e.target.value)}
                  placeholder="Detail published peer-reviewed papers, domain specialization, or statutory preference..."
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 text-slate-800"
                  required
                />
              </div>

              <div className="pt-3 border-t border-slate-200 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setIsTieModalOpen(false)}
                  className="px-4 py-2 text-xs text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isResolvingTie}
                  className="px-4 py-2 text-xs font-semibold text-white bg-amber-600 hover:bg-amber-500 rounded-lg"
                >
                  {isResolvingTie ? 'Recording Resolution...' : 'Commit Tie Resolution'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Finalize Batch Selection */}
      {isFinalizeModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-xl max-w-xl w-full p-6 border border-slate-200">
            <div className="flex items-center gap-2.5 mb-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              <h3 className="text-lg font-bold text-slate-900">Finalize Batch Selection</h3>
            </div>
            <p className="text-xs text-slate-500 mb-4">
              Commit final selection, waitlisting, and rejection allocations according to frozen quota rules.
            </p>

            <form onSubmit={handleFinalizeBatch} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Resolution Order Reference</label>
                <input
                  type="text"
                  value={resolutionRef}
                  onChange={(e) => setResolutionRef(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 text-slate-800 font-mono"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Meeting Date</label>
                <input
                  type="date"
                  value={meetingDate}
                  onChange={(e) => setMeetingDate(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 text-slate-800"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Official Selection Committee Minutes</label>
                <textarea
                  rows={4}
                  value={committeeMinutes}
                  onChange={(e) => setCommitteeMinutes(e.target.value)}
                  placeholder="Record summary of committee quorum, deliberations, and consensus approval..."
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 text-slate-800"
                  required
                />
              </div>

              <div className="pt-3 border-t border-slate-200 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setIsFinalizeModalOpen(false)}
                  className="px-4 py-2 text-xs text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isFinalizing}
                  className="px-4 py-2 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg"
                >
                  {isFinalizing ? 'Finalizing...' : 'Commit Final Selection'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Administrative Override (Admin Only) */}
      {isOverrideModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-xl max-w-xl w-full p-6 border border-slate-200">
            <div className="flex items-center gap-2.5 mb-2">
              <Scale className="w-5 h-5 text-indigo-600" />
              <h3 className="text-lg font-bold text-slate-900">Administrative Selection Override</h3>
            </div>
            <p className="text-xs text-slate-500 mb-4">
              Restricted to Ministry Admins. Modifies candidate outcome while permanently preserving original merit rank.
            </p>

            <form onSubmit={handleAdminOverride} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Candidate Application</label>
                <select
                  value={overrideAppId}
                  onChange={(e) => setOverrideAppId(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white text-slate-800"
                  required
                >
                  {ranking.map((r) => (
                    <option key={r.application_id} value={r.application_id}>
                      {r.applicant_name} ({r.reference_id}) - Merit Rank #{r.rank}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Target Override Status</label>
                <select
                  value={targetStatus}
                  onChange={(e: any) => setTargetStatus(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white text-slate-800"
                >
                  <option value="SELECTED">SELECTED (Special Dispensation)</option>
                  <option value="REJECTED">REJECTED (Disqualification / Ineligibility)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Authority Directive Reference</label>
                <input
                  type="text"
                  value={overrideAuthorityRef}
                  onChange={(e) => setOverrideAuthorityRef(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 text-slate-800 font-mono"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Detailed Statutory Justification</label>
                <textarea
                  rows={3}
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  placeholder="Record full statutory basis, ministry directive, or court order details..."
                  className="w-full text-xs border border-slate-300 rounded-lg p-2.5 text-slate-800"
                  required
                />
              </div>

              <div className="pt-3 border-t border-slate-200 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setIsOverrideModalOpen(false)}
                  className="px-4 py-2 text-xs text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isOverriding}
                  className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg"
                >
                  {isOverriding ? 'Recording Override...' : 'Execute Override'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default MeritRankingConsole;
