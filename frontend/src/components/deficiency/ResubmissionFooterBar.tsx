import React, { useState } from 'react';
import { Send, ShieldCheck, AlertCircle, Loader2 } from 'lucide-react';

interface ResubmissionFooterBarProps {
  totalCount: number;
  replacedCount: number;
  canResubmit: boolean;
  isSubmitting: boolean;
  onResubmit: (declarationConfirmed: boolean, remarks?: string) => Promise<void>;
}

export const ResubmissionFooterBar: React.FC<ResubmissionFooterBarProps> = ({
  totalCount,
  replacedCount,
  canResubmit,
  isSubmitting,
  onResubmit,
}) => {
  const [declarationChecked, setDeclarationChecked] = useState(false);
  const [remarks, setRemarks] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!declarationChecked) {
      setErrorMessage('You must confirm the authenticity declaration before resubmitting.');
      return;
    }
    setErrorMessage(null);
    try {
      await onResubmit(declarationChecked, remarks.trim() || undefined);
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? ((err as { response: { data: { error?: string } } }).response.data?.error || 'Resubmission failed.')
          : 'Resubmission failed.';
      setErrorMessage(msg);
    }
  };

  const isReady = canResubmit && declarationChecked && !isSubmitting;

  return (
    <div className="sticky bottom-4 z-20 mt-8 rounded-2xl bg-slate-900/95 border border-slate-700/80 p-5 sm:p-6 shadow-2xl backdrop-blur-xl">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        {/* Progress and status summary */}
        <div className="flex-1">
          <div className="flex items-center justify-between gap-4 mb-2">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
              <span className="text-sm font-semibold text-white">
                Deficiency Resolution Progress
              </span>
            </div>
            <span className="text-xs font-mono font-medium text-slate-300">
              {replacedCount} of {totalCount} Replaced
            </span>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden mb-3">
            <div
              className={`h-full transition-all duration-300 ${
                canResubmit ? 'bg-emerald-500' : 'bg-amber-500'
              }`}
              style={{ width: `${totalCount > 0 ? (replacedCount / totalCount) * 100 : 0}%` }}
            />
          </div>

          {/* Declaration Checkbox */}
          <label className="flex items-start gap-2.5 cursor-pointer select-none text-xs sm:text-sm text-slate-300">
            <input
              type="checkbox"
              checked={declarationChecked}
              onChange={(e) => setDeclarationChecked(e.target.checked)}
              disabled={!canResubmit || isSubmitting}
              className="mt-0.5 rounded border-slate-700 text-amber-500 focus:ring-amber-500/20 bg-slate-950 disabled:opacity-50"
            />
            <span>
              I confirm that all replacement documents uploaded are genuine, official government-issued certificates.
            </span>
          </label>

          {/* Optional remarks */}
          {canResubmit && (
            <div className="mt-3">
              <input
                type="text"
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                placeholder="Optional notes for scrutinizing officer (e.g. Verified with issuing authority)"
                disabled={isSubmitting}
                className="w-full text-xs rounded-lg bg-slate-950/80 border border-slate-700 p-2 text-slate-200 placeholder-slate-500 focus:ring-1 focus:ring-emerald-500"
              />
            </div>
          )}
        </div>

        {/* Action Button & Validation Alert */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
          {errorMessage && (
            <div className="text-xs text-red-400 flex items-center gap-1.5 px-3 py-2 bg-red-500/10 border border-red-500/20 rounded-lg">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          <button
            type="button"
            onClick={handleSubmit}
            disabled={!isReady}
            className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-emerald-500 hover:bg-emerald-400 disabled:bg-slate-800 disabled:text-slate-500 disabled:cursor-not-allowed text-slate-950 font-bold text-sm rounded-xl transition-all shadow-lg shadow-emerald-500/20"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Resubmitting...
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                Resubmit Application
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
