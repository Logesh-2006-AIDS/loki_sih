import React, { useState } from 'react';
import { AlertTriangle, ShieldCheck, X } from 'lucide-react';

interface AIOverrideModalProps {
  isOpen: boolean;
  documentType: string;
  flags: Array<{ field: string; reason?: string }>;
  onConfirm: (reason: string) => void;
  onCancel: () => void;
}

export const AIOverrideModal: React.FC<AIOverrideModalProps> = ({
  isOpen,
  documentType,
  flags,
  onConfirm,
  onCancel,
}) => {
  const [reason, setReason] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim() || reason.trim().length < 5) {
      setError('Please provide a substantive rationale (at least 5 characters) justifying why this AI flag is being overridden.');
      return;
    }
    setError(null);
    onConfirm(reason.trim());
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg overflow-hidden border border-amber-300 animate-in fade-in zoom-in-95 duration-150">
        <div className="bg-amber-950 text-amber-100 px-5 py-3.5 flex items-center justify-between border-b border-amber-800">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0" />
            <h3 className="text-sm font-bold tracking-wide uppercase">
              Confirm Human Override of AI Flag
            </h3>
          </div>
          <button
            onClick={onCancel}
            className="text-amber-300 hover:text-white p-1 rounded transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div className="bg-amber-50 p-3.5 rounded-lg border border-amber-200 text-xs text-amber-900">
            <p className="font-semibold mb-1">
              Document: <span className="font-mono text-amber-950">{documentType}</span>
            </p>
            <p className="mb-2 text-slate-700">
              The automated AI verification system raised flags on this document:
            </p>
            <ul className="list-disc list-inside space-y-1 text-slate-800 font-medium">
              {flags.map((f, i) => (
                <li key={i}>{f.reason || f.field}</li>
              ))}
            </ul>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Human Scrutiny Rationale / Justification <span className="text-rose-600">*</span>
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              placeholder="e.g. Spelling variation in tribal surname cross-checked and verified against state gazette ST list; certificate stamp authentic."
              className="w-full text-xs rounded-lg border border-slate-300 p-2.5 text-slate-900 focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
            />
            {error && <p className="text-xs text-rose-600 mt-1">{error}</p>}
            <p className="text-[11px] text-slate-500 mt-1">
              This explanation will be permanently recorded in the official audit trail alongside your officer identity.
            </p>
          </div>

          <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-200">
            <button
              type="button"
              onClick={onCancel}
              className="px-3.5 py-2 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-amber-600 hover:bg-amber-700 text-white shadow-sm transition-colors"
            >
              <ShieldCheck className="w-4 h-4" />
              Confirm Override & Verify
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
