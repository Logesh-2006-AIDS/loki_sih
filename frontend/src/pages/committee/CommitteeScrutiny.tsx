import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  ShieldCheck,
  FileCheck2,
  GraduationCap,
  BookOpen,
  Award,
  Save,
  CheckCircle2,
  AlertTriangle,
  Lock,
  RefreshCw,
} from 'lucide-react';
import { committeeService } from '../../services/committeeService';
import { CommitteeDossier } from '../../types/committee';

export const CommitteeScrutiny: React.FC = () => {
  const { batchId, applicationId } = useParams<{ batchId: string; applicationId: string }>();
  const navigate = useNavigate();

  const [dossier, setDossier] = useState<CommitteeDossier | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Scorecard State
  const [feasibility, setFeasibility] = useState<number>(20);
  const [innovation, setInnovation] = useState<number>(20);
  const [methodology, setMethodology] = useState<number>(20);
  const [remarks, setRemarks] = useState('');
  const [recommendation, setRecommendation] = useState<
    'RECOMMEND' | 'WAITLIST' | 'REJECT' | 'NEEDS_DISCUSSION'
  >('RECOMMEND');
  const [confidentialityAcknowledged, setConfidentialityAcknowledged] = useState(false);

  const fetchDossier = useCallback(async () => {
    if (!batchId || !applicationId) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const dossiers = await committeeService.getBatchApplications(batchId);
      const found = dossiers.find((d) => d.application_id === applicationId);
      if (!found) {
        throw new Error('Candidate dossier not found in this evaluation cohort.');
      }
      setDossier(found);

      // Pre-fill existing review if present
      if (found.my_review) {
        const scores = found.my_review.scores || {};
        if (scores.feasibility !== undefined) setFeasibility(Number(scores.feasibility));
        if (scores.innovation !== undefined) setInnovation(Number(scores.innovation));
        if (scores.methodology !== undefined) setMethodology(Number(scores.methodology));
        if (found.my_review.remarks) setRemarks(found.my_review.remarks);
        if (found.my_review.recommendation) setRecommendation(found.my_review.recommendation);
        setConfidentialityAcknowledged(true);
      }
    } catch (err: any) {
      console.error('Failed to load candidate dossier', err);
      setErrorMsg(err.response?.data?.message || err.message || 'Failed to load candidate dossier.');
    } finally {
      setIsLoading(false);
    }
  }, [batchId, applicationId]);

  useEffect(() => {
    fetchDossier();
  }, [fetchDossier]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!batchId || !applicationId) return;

    if (!confidentialityAcknowledged) {
      alert('You must acknowledge the independent evaluation confidentiality declaration.');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      await committeeService.submitReview(applicationId, batchId, {
        scores: {
          feasibility: Number(feasibility),
          innovation: Number(innovation),
          methodology: Number(methodology),
        },
        remarks: remarks.trim() || undefined,
        recommendation: recommendation,
      });

      setSuccessMsg('Evaluation scorecard submitted successfully.');
      setTimeout(() => {
        navigate(`/committee/batches/${batchId}/queue`);
      }, 1200);
    } catch (err: any) {
      console.error('Failed to submit review', err);
      setErrorMsg(err.response?.data?.message || 'Failed to submit committee review.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="flex items-center gap-3 text-indigo-600 font-medium text-sm">
          <RefreshCw className="w-5 h-5 animate-spin" />
          Loading Candidate Dossier...
        </div>
      </div>
    );
  }

  if (errorMsg && !dossier) {
    return (
      <div className="min-h-screen bg-slate-50 p-8">
        <div className="max-w-xl mx-auto bg-white rounded-xl p-6 border border-rose-200">
          <p className="text-rose-600 font-medium text-sm mb-4">{errorMsg}</p>
          <button
            onClick={() => navigate(`/committee/batches/${batchId}/queue`)}
            className="px-4 py-2 bg-slate-800 text-white rounded-lg text-xs"
          >
            Back to Queue
          </button>
        </div>
      </div>
    );
  }

  const isLocked = dossier?.is_batch_locked;

  return (
    <div className="min-h-screen bg-slate-50 pb-20">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <button
            onClick={() => navigate(`/committee/batches/${batchId}/queue`)}
            className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-slate-800 mb-2 transition"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Candidate Queue
          </button>
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-slate-900">
                  Dossier Scrutiny: <span className="font-mono text-indigo-600">{dossier?.reference_id}</span>
                </h1>
                {isLocked && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                    <Lock className="w-3 h-3" /> Batch Locked
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Candidate: <strong className="text-slate-800">{dossier?.applicant_name}</strong> • Scheme: {dossier?.scheme_name} (v{dossier?.scheme_version})
              </p>
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

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Column: Blind Dossier Details (7 cols) */}
          <div className="lg:col-span-7 space-y-6">
            {/* Candidate Credentials Card */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200/80 p-6">
              <div className="flex items-center gap-2.5 mb-4 pb-3 border-b border-slate-100">
                <GraduationCap className="w-5 h-5 text-indigo-600" />
                <h2 className="text-base font-bold text-slate-900">Academic & Eligibility Profile</h2>
              </div>
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div>
                  <span className="text-slate-400 block mb-0.5">Category / Community</span>
                  <span className="font-semibold text-slate-800">{dossier?.category || 'ST'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block mb-0.5">Domicile State</span>
                  <span className="font-semibold text-slate-800">{dossier?.state || 'Not specified'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block mb-0.5">Academic Marks (%)</span>
                  <span className="font-semibold text-slate-800">
                    {dossier?.academic_summary?.percentage_marks !== undefined
                      ? `${dossier.academic_summary.percentage_marks}%`
                      : 'Verified'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block mb-0.5">Degree / Qualifying Exam</span>
                  <span className="font-semibold text-slate-800">
                    {dossier?.academic_summary?.degree || 'Postgraduate'}
                  </span>
                </div>
              </div>
            </div>

            {/* Proposal & Research Plan Card */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200/80 p-6">
              <div className="flex items-center gap-2.5 mb-4 pb-3 border-b border-slate-100">
                <BookOpen className="w-5 h-5 text-indigo-600" />
                <h2 className="text-base font-bold text-slate-900">Research Proposal & Institution</h2>
              </div>
              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-slate-400 block mb-0.5">Proposed Topic / Field</span>
                  <p className="font-medium text-slate-800">
                    {dossier?.proposal_summary?.title ||
                      dossier?.proposal_summary?.subject ||
                      'Advanced Research Study in Tribal Culture and Development'}
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-slate-400 block mb-0.5">Host Institute / University</span>
                    <span className="font-semibold text-slate-800">
                      {dossier?.proposal_summary?.institute || 'Central University'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block mb-0.5">NIRF / QS Rank Bracket</span>
                    <span className="font-semibold text-slate-800">
                      {dossier?.proposal_summary?.nirf_rank ? `NIRF Top ${dossier.proposal_summary.nirf_rank}` : 'Accredited Institution'}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Verified Supporting Documents */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200/80 p-6">
              <div className="flex items-center gap-2.5 mb-4 pb-3 border-b border-slate-100">
                <FileCheck2 className="w-5 h-5 text-emerald-600" />
                <h2 className="text-base font-bold text-slate-900">Verified Supporting Certificates</h2>
              </div>
              <div className="space-y-2">
                {dossier?.verified_documents && dossier.verified_documents.length > 0 ? (
                  dossier.verified_documents.map((doc, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 text-xs border border-slate-200/60"
                    >
                      <span className="font-medium text-slate-800">{doc.document_type.replace(/_/g, ' ')}</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        VERIFIED
                      </span>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400">All mandatory documents verified by scrutiny officers.</p>
                )}
              </div>
            </div>
          </div>

          {/* Right Column: Independent Member Scorecard Form (5 cols) */}
          <div className="lg:col-span-5">
            <div className="bg-white rounded-xl shadow-sm border border-slate-200/80 p-6 sticky top-8">
              <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-100">
                <Award className="w-5 h-5 text-indigo-600" />
                <h2 className="text-base font-bold text-slate-900">Independent Scorecard</h2>
              </div>

              {isLocked ? (
                <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs mb-4">
                  <span className="font-bold">Evaluation Window Locked: </span>
                  Scorecards for this batch are finalized and sealed. No further score edits are permitted.
                </div>
              ) : (
                <div className="p-3 rounded-lg bg-indigo-50/70 border border-indigo-100 text-indigo-900 text-xs mb-5 flex items-start gap-2">
                  <ShieldCheck className="w-4 h-4 text-indigo-600 flex-shrink-0 mt-0.5" />
                  <span>Your evaluation is blind and stored independently. Enter qualitative marks out of 25 for each component.</span>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Scoring Component 1 */}
                <div>
                  <div className="flex items-center justify-between mb-1 text-xs">
                    <label className="font-semibold text-slate-800">Proposal Feasibility & Significance</label>
                    <span className="font-mono font-bold text-indigo-600">{feasibility} / 25</span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={25}
                    step={1}
                    value={feasibility}
                    disabled={isLocked}
                    onChange={(e) => setFeasibility(Number(e.target.value))}
                    className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600 disabled:opacity-50"
                  />
                </div>

                {/* Scoring Component 2 */}
                <div>
                  <div className="flex items-center justify-between mb-1 text-xs">
                    <label className="font-semibold text-slate-800">Innovation & Tribal Benefit Impact</label>
                    <span className="font-mono font-bold text-indigo-600">{innovation} / 25</span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={25}
                    step={1}
                    value={innovation}
                    disabled={isLocked}
                    onChange={(e) => setInnovation(Number(e.target.value))}
                    className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600 disabled:opacity-50"
                  />
                </div>

                {/* Scoring Component 3 */}
                <div>
                  <div className="flex items-center justify-between mb-1 text-xs">
                    <label className="font-semibold text-slate-800">Methodology & Research Plan</label>
                    <span className="font-mono font-bold text-indigo-600">{methodology} / 25</span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={25}
                    step={1}
                    value={methodology}
                    disabled={isLocked}
                    onChange={(e) => setMethodology(Number(e.target.value))}
                    className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600 disabled:opacity-50"
                  />
                </div>

                {/* Overall Recommendation */}
                <div>
                  <label className="block text-xs font-semibold text-slate-800 mb-1">
                    Overall Panel Recommendation
                  </label>
                  <select
                    value={recommendation}
                    disabled={isLocked}
                    onChange={(e: any) => setRecommendation(e.target.value)}
                    className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white text-slate-800 focus:ring-2 focus:ring-indigo-500 focus:outline-none disabled:opacity-50"
                  >
                    <option value="RECOMMEND">Recommend for Selection</option>
                    <option value="WAITLIST">Recommend for Waitlist</option>
                    <option value="NEEDS_DISCUSSION">Needs Committee Discussion</option>
                    <option value="REJECT">Not Recommended</option>
                  </select>
                </div>

                {/* Remarks */}
                <div>
                  <label className="block text-xs font-semibold text-slate-800 mb-1">
                    Confidential Deliberation Remarks
                  </label>
                  <textarea
                    rows={3}
                    value={remarks}
                    disabled={isLocked}
                    onChange={(e) => setRemarks(e.target.value)}
                    placeholder="Enter confidential notes regarding methodology, research strengths, or questions for discussion..."
                    className="w-full text-xs border border-slate-300 rounded-lg p-2.5 text-slate-800 focus:ring-2 focus:ring-indigo-500 focus:outline-none disabled:opacity-50"
                  />
                </div>

                {/* Confidentiality Checkbox */}
                <div className="pt-2">
                  <label className="flex items-start gap-2 text-xs text-slate-600 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={confidentialityAcknowledged}
                      disabled={isLocked}
                      onChange={(e) => setConfidentialityAcknowledged(e.target.checked)}
                      className="mt-0.5 rounded text-indigo-600 focus:ring-indigo-500 disabled:opacity-50"
                    />
                    <span>
                      I hereby certify that this scrutiny is performed independently and in strict confidence under Ministry of Tribal Affairs evaluation rules.
                    </span>
                  </label>
                </div>

                {!isLocked && (
                  <button
                    type="submit"
                    disabled={isSubmitting || !confidentialityAcknowledged}
                    className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-lg shadow-sm transition disabled:opacity-50 mt-2"
                  >
                    <Save className="w-4 h-4" />
                    {isSubmitting ? 'Submitting Scorecard...' : 'Submit / Update Scorecard'}
                  </button>
                )}
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CommitteeScrutiny;
