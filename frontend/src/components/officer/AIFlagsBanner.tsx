import React from 'react';
import { AlertTriangle, Info } from 'lucide-react';

interface AIFlag {
  field: string;
  label?: string;
  application_value?: string | null;
  document_value?: string | null;
  reason?: string;
  severity?: string;
}

interface AIFlagsBannerProps {
  flags: AIFlag[];
  overallConfidence?: number | null;
}

export const AIFlagsBanner: React.FC<AIFlagsBannerProps> = ({ flags, overallConfidence }) => {
  if (!flags || flags.length === 0) {
    return null;
  }

  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50/80 p-3.5 mb-4 shadow-sm">
      <div className="flex items-start gap-2.5">
        <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
        <div className="flex-1">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="text-xs font-bold text-amber-900 tracking-wide uppercase">
              AI Verification Flags Detected ({flags.length})
            </h4>
            {overallConfidence !== null && overallConfidence !== undefined && (
              <span className="text-[11px] font-medium text-amber-800 bg-amber-200/70 px-2 py-0.5 rounded">
                Overall AI Confidence: {(overallConfidence * 100).toFixed(0)}%
              </span>
            )}
          </div>

          <div className="mt-2 space-y-1.5">
            {flags.map((flag, idx) => (
              <div
                key={idx}
                className="text-xs text-amber-900 bg-white/70 p-2 rounded border border-amber-200/80 flex flex-wrap items-center justify-between gap-2"
              >
                <div>
                  <span className="font-semibold capitalize text-slate-800">
                    {flag.label || flag.field.replace(/_/g, ' ')}:
                  </span>{' '}
                  <span className="text-slate-700">{flag.reason}</span>
                </div>
                {flag.severity && (
                  <span
                    className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${
                      flag.severity === 'HIGH'
                        ? 'bg-rose-100 text-rose-800 border border-rose-200'
                        : 'bg-amber-100 text-amber-800 border border-amber-200'
                    }`}
                  >
                    {flag.severity} Priority
                  </span>
                )}
              </div>
            ))}
          </div>

          <div className="mt-2.5 flex items-center gap-1.5 text-[11px] text-amber-800/90 italic">
            <Info className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
            <span>
              <strong>Statutory Rule:</strong> AI assists, human decides. You may override these flags if physical examination or revenue rules substantiate validity.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
