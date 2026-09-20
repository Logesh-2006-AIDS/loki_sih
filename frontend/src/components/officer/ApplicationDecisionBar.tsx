import React, { useState } from 'react';
import { CheckCircle2, AlertTriangle, XCircle, Send, AlertCircle } from 'lucide-react';
import { OfficerDocumentScrutinyItem } from '../../types/officer';

interface ApplicationDecisionBarProps {
  documents: OfficerDocumentScrutinyItem[];
  requiredDocConfigs?: Array<{ code: string; label?: string; required?: boolean }> | null;
  currentStatus: string;
  isSubmitting: boolean;
  onSubmitDecision: (decision: 'VERIFIED' | 'DEFICIENT' | 'REJECTED', remarks: string) => Promise<void>;
}

export const ApplicationDecisionBar: React.FC<ApplicationDecisionBarProps> = ({
  documents,
  requiredDocConfigs,
  currentStatus,
  isSubmitting,
  onSubmitDecision,
}) => {
  const [overallRemarks, setOverallRemarks] = useState('');
  const [pendingDecision, setPendingDecision] = useState<'VERIFIED' | 'DEFICIENT' | 'REJECTED' | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Check document status counts
  const verifiedCount = documents.filter((d) => d.officer_decision === 'VERIFIED').length;
  const deficientCount = documents.filter((d) => d.officer_decision === 'RESUBMISSION_REQUIRED').length;
  const rejectedCount = documents.filter((d) => d.officer_decision === 'REJECTED').length;
  const totalDocs = documents.length;

  // Determine if all required documents have human verification
  const requiredCodes = (requiredDocConfigs || [])
    .filter((d) => d.required !== false)
    .map((d) => d.code);

  const docMap = new Map(documents.map((d) => [d.document_type, d]));
  const missingHumanVerifications = requiredCodes.filter(
    (code) => docMap.get(code)?.officer_decision !== 'VERIFIED'
  );

  const canApprove =
    missingHumanVerifications.length === 0 && deficientCount === 0 && rejectedCount === 0;

  const canFlagDeficient = deficientCount > 0;

  const handleTriggerAction = (decision: 'VERIFIED' | 'DEFICIENT' | 'REJECTED') => {
    setErrorMessage(null);

    if (decision === 'VERIFIED' && !canApprove) {
      if (deficientCount > 0 || rejectedCount > 0) {
        setErrorMessage('Cannot approve application while documents are flagged Deficient or Rejected.');
      } else {
        setErrorMessage(
          `Cannot approve application: ${missingHumanVerifications.length} mandatory document(s) still require explicit human officer verification.`
        );
      }
      return;
    }

    if (!overallRemarks.trim()) {
      setErrorMessage('Please enter overall scrutiny remarks before submitting final determination.');
      return;
    }

    setPendingDecision(decision);
  };

  const handleConfirmSubmit = async () => {
    if (!pendingDecision) return;
    setErrorMessage(null);
    try {
      await onSubmitDecision(pendingDecision, overallRemarks.trim());
      setPendingDecision(null);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.error || 'Failed to submit application scrutiny decision');
      setPendingDecision(null);
    }
  };

  const isAlreadyFinalized = currentStatus !== 'UNDER_MANUAL_REVIEW';

  return (
    <div className="sticky bottom-0 z-30 bg-slate-900 text-white border-t border-slate-700 shadow-2xl py-4 px-4 sm:px-6">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
        {/* Scrutiny Progress Checklist */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 text-xs">
          <div className="font-semibold tracking-wide uppercase text-slate-400">
            Document Scrutiny Status:
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`px-2 py-0.5 rounded-full font-bold flex items-center gap-1 ${
                verifiedCount === totalDocs && totalDocs > 0
                  ? 'bg-emerald-800 text-emerald-100 border border-emerald-600'
                  : 'bg-slate-800 text-slate-300 border border-slate-700'
              }`}
            >
              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
              {verifiedCount}/{totalDocs} Human Verified
            </span>

            {deficientCount > 0 && (
              <span className="px-2 py-0.5 rounded-full font-bold bg-orange-950 text-orange-200 border border-orange-700 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3 text-orange-400" />
                {deficientCount} Deficient
              </span>
            )}

            {rejectedCount > 0 && (
              <span className="px-2 py-0.5 rounded-full font-bold bg-rose-950 text-rose-200 border border-rose-700 flex items-center gap-1">
                <XCircle className="w-3 h-3 text-rose-400" />
                {rejectedCount} Rejected
              </span>
            )}
          </div>
        </div>

        {/* Remarks Input & Action Buttons */}
        <div className="flex-1 max-w-2xl flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
          <input
            type="text"
            disabled={isAlreadyFinalized}
            value={overallRemarks}
            onChange={(e) => setOverallRemarks(e.target.value)}
            placeholder={
              isAlreadyFinalized
                ? 'Scrutiny determination already finalized'
                : 'Enter comprehensive scrutiny remarks (required)...'
            }
            className="flex-1 text-xs rounded-lg bg-slate-800 border border-slate-700 p-2.5 text-white placeholder-slate-400 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 disabled:opacity-50"
          />

          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={isAlreadyFinalized || isSubmitting || !canApprove}
              onClick={() => handleTriggerAction('VERIFIED')}
              className="px-3.5 py-2 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors disabled:opacity-40 disabled:hover:bg-emerald-600 flex items-center gap-1.5 shadow-sm"
              title={
                canApprove
                  ? 'Approve application'
                  : 'All mandatory documents must have explicit human verification'
              }
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              Approve (Verified)
            </button>

            <button
              type="button"
              disabled={isAlreadyFinalized || isSubmitting || !canFlagDeficient}
              onClick={() => handleTriggerAction('DEFICIENT')}
              className="px-3 py-2 rounded-lg text-xs font-semibold bg-orange-600 hover:bg-orange-500 text-white transition-colors disabled:opacity-40 disabled:hover:bg-orange-600 flex items-center gap-1.5 shadow-sm"
              title="Flag application as deficient (Phase 5 handoff)"
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              Flag Deficient
            </button>

            <button
              type="button"
              disabled={isAlreadyFinalized || isSubmitting}
              onClick={() => handleTriggerAction('REJECTED')}
              className="px-3 py-2 rounded-lg text-xs font-semibold bg-rose-700 hover:bg-rose-600 text-white transition-colors disabled:opacity-40 disabled:hover:bg-rose-700 flex items-center gap-1.5 shadow-sm"
            >
              <XCircle className="w-3.5 h-3.5" />
              Reject
            </button>
          </div>
        </div>
      </div>

      {errorMessage && (
        <div className="max-w-7xl mx-auto mt-2 text-xs text-rose-400 flex items-center gap-1">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Confirmation Modal */}
      {pendingDecision && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-xs p-4 text-slate-900">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-5 border border-slate-300">
            <h3 className="text-base font-bold text-slate-900 mb-2 flex items-center gap-2">
              Confirm Final Scrutiny Determination
            </h3>
            <p className="text-xs text-slate-600 mb-4">
              Are you sure you want to finalize this application scrutiny decision as{' '}
              <strong className="text-slate-900 font-bold uppercase">{pendingDecision}</strong>?
            </p>

            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs mb-4">
              <span className="font-semibold text-slate-700 block mb-1">Remarks to record:</span>
              <p className="italic text-slate-800">{overallRemarks}</p>
            </div>

            {pendingDecision === 'DEFICIENT' && (
              <p className="text-[11px] text-amber-800 bg-amber-50 p-2.5 rounded border border-amber-200 mb-4">
                <strong>Phase 5 Notice:</strong> Marking this application as DEFICIENT will create OPEN deficiency records in the database. Phase 5 will consume this to manage applicant resubmission.
              </p>
            )}

            <div className="flex items-center justify-end gap-2.5">
              <button
                type="button"
                onClick={() => setPendingDecision(null)}
                className="px-3.5 py-1.5 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmSubmit}
                disabled={isSubmitting}
                className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-teal-800 hover:bg-teal-900 text-white shadow-sm flex items-center gap-1.5"
              >
                <Send className="w-3.5 h-3.5" />
                {isSubmitting ? 'Submitting...' : 'Confirm & Finalize'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
