import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Lock,
  Unlock,
  CheckCircle2,
  Clock,
  ShieldCheck,
  Eye,
  BarChart3,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import { committeeService } from '../../services/committeeService';
import { CommitteeBatch, CommitteeDossier } from '../../types/committee';

export const CommitteeQueue: React.FC = () => {
  const { batchId } = useParams<{ batchId: string }>();
  const navigate = useNavigate();

  const [batch, setBatch] = useState<CommitteeBatch | null>(null);
  const [dossiers, setDossiers] = useState<CommitteeDossier[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchQueue = useCallback(async () => {
    if (!batchId) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const [batchData, dossiersData] = await Promise.all([
        committeeService.getBatchDetails(batchId),
        committeeService.getBatchApplications(batchId),
      ]);
      setBatch(batchData);
      setDossiers(dossiersData);
    } catch (err: any) {
      console.error('Failed to load committee queue', err);
      setErrorMsg(err.response?.data?.message || 'Failed to load committee candidate queue.');
    } finally {
      setIsLoading(false);
    }
  }, [batchId]);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="flex items-center gap-3 text-indigo-600 font-medium text-sm">
          <RefreshCw className="w-5 h-5 animate-spin" />
          Loading Candidate Scrutiny Queue...
        </div>
      </div>
    );
  }

  if (errorMsg || !batch) {
    return (
      <div className="min-h-screen bg-slate-50 p-8">
        <div className="max-w-3xl mx-auto bg-white rounded-xl shadow-sm border border-rose-200 p-6">
          <div className="flex items-center gap-3 text-rose-600 mb-4">
            <AlertCircle className="w-6 h-6" />
            <h2 className="text-lg font-bold">Error Loading Cohort</h2>
          </div>
          <p className="text-sm text-slate-600 mb-6">{errorMsg || 'Cohort batch not found.'}</p>
          <button
            onClick={() => navigate('/committee')}
            className="inline-flex items-center gap-2 px-4 py-2 bg-slate-800 text-white text-sm font-medium rounded-lg hover:bg-slate-700"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 pb-20">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <button
                onClick={() => navigate('/committee')}
                className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-slate-800 mb-2 transition"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Back to Committee Dashboard
              </button>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-slate-900">{batch.name}</h1>
                {batch.status === 'FINALIZED' ? (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <CheckCircle2 className="w-3 h-3" /> Finalized
                  </span>
                ) : batch.is_locked ? (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                    <Lock className="w-3 h-3" /> Locked
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                    <Unlock className="w-3 h-3" /> Open Scrutiny
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Batch ID: <span className="font-mono text-slate-700">{batch.id}</span> • {dossiers.length} Candidates in Cohort
              </p>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={fetchQueue}
                className="inline-flex items-center gap-1.5 px-3 py-2 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium rounded-lg border border-slate-300 transition"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Refresh Queue
              </button>
              <button
                onClick={() => navigate(`/committee/batches/${batch.id}/ranking`)}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg shadow-sm transition"
              >
                <BarChart3 className="w-4 h-4" />
                Ranking Console
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Blind Review Notice */}
        <div className="mb-6 p-4 rounded-xl bg-indigo-50 border border-indigo-200 flex items-start gap-3">
          <ShieldCheck className="w-5 h-5 text-indigo-600 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-indigo-900">
            <span className="font-bold">Independent Blind Evaluation Protocol Active: </span>
            You are evaluating candidate dossiers independently. Peer committee scores and provisional ranks remain sealed until all candidates satisfy required quorum and the cohort is locked.
          </div>
        </div>

        {/* Candidate Table */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200/80 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900">Candidate Evaluation Dossiers</h2>
            <span className="text-xs text-slate-500">
              Per-Candidate Quorum: <strong className="text-slate-800">{dossiers[0]?.required_quorum || 2} reviews</strong>
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-left font-semibold text-slate-700">Reference ID</th>
                  <th className="px-6 py-3 text-left font-semibold text-slate-700">Candidate</th>
                  <th className="px-6 py-3 text-left font-semibold text-slate-700">Category & State</th>
                  <th className="px-6 py-3 text-center font-semibold text-slate-700">Quorum Progress</th>
                  <th className="px-6 py-3 text-center font-semibold text-slate-700">Your Status</th>
                  <th className="px-6 py-3 text-right font-semibold text-slate-700">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {dossiers.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-slate-400">
                      No candidate dossiers found in this batch.
                    </td>
                  </tr>
                ) : (
                  dossiers.map((d) => {
                    const isQuorumMet = d.completed_reviews_count >= d.required_quorum;
                    const hasMyReview = Boolean(d.my_review);

                    return (
                      <tr key={d.application_id} className="hover:bg-slate-50/80 transition">
                        <td className="px-6 py-4 font-mono font-semibold text-slate-900 text-xs">
                          {d.reference_id}
                        </td>
                        <td className="px-6 py-4">
                          <div className="font-semibold text-slate-900">{d.applicant_name}</div>
                          <div className="text-xs text-slate-400">
                            {d.academic_summary?.percentage_marks
                              ? `Marks: ${d.academic_summary.percentage_marks}%`
                              : 'Verified Credentials'}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-xs">
                          <span className="font-medium text-slate-800">{d.category || 'ST'}</span>
                          <span className="text-slate-400 ml-1.5">• {d.state || 'India'}</span>
                        </td>
                        <td className="px-6 py-4 text-center">
                          <div className="inline-flex items-center gap-1.5">
                            <span
                              className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                                isQuorumMet
                                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                  : 'bg-amber-50 text-amber-700 border border-amber-200'
                              }`}
                            >
                              {d.completed_reviews_count} / {d.required_quorum} Reviews
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-center">
                          {hasMyReview ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                              <CheckCircle2 className="w-3 h-3" />
                              {d.my_review?.recommendation || 'Scored'}
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600">
                              <Clock className="w-3 h-3 text-slate-400" />
                              Pending Review
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <button
                            onClick={() =>
                              navigate(`/committee/batches/${batch.id}/scrutiny/${d.application_id}`)
                            }
                            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                              hasMyReview
                                ? 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                                : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm'
                            }`}
                          >
                            <Eye className="w-3.5 h-3.5" />
                            {hasMyReview ? 'Edit Scorecard' : 'Scrutinize Dossier'}
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CommitteeQueue;
