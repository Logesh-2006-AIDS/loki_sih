import React from 'react';
import { Check, X, AlertCircle } from 'lucide-react';

interface ComparisonResultItem {
  status: 'MATCH' | 'MISMATCH' | 'UNCLEAR' | string;
  application_value?: any;
  document_value?: any;
  field?: string;
  label?: string;
  similarity?: number;
  confidence?: number;
  notes?: string;
}

interface FieldComparisonGridProps {
  comparisonResults: Record<string, ComparisonResultItem>;
  extractedFields: Record<string, any>;
  fieldConfidences: Record<string, number>;
}

export const FieldComparisonGrid: React.FC<FieldComparisonGridProps> = ({
  comparisonResults,
  extractedFields,
  fieldConfidences,
}) => {
  const fieldKeys = Array.from(
    new Set([...Object.keys(comparisonResults), ...Object.keys(extractedFields)])
  );

  if (fieldKeys.length === 0) {
    return (
      <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-500 text-center">
        No field-level comparisons extracted for this document.
      </div>
    );
  }

  const getStatusPill = (status?: string) => {
    switch (status) {
      case 'MATCH':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
            <Check className="w-3 h-3 text-emerald-600 stroke-[3]" />
            MATCH
          </span>
        );
      case 'MISMATCH':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-300">
            <X className="w-3 h-3 text-rose-600 stroke-[3]" />
            MISMATCH
          </span>
        );
      case 'UNCLEAR':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-300">
            <AlertCircle className="w-3 h-3 text-amber-600 stroke-[2.5]" />
            UNCLEAR
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600">
            {status || 'EXTRACTED'}
          </span>
        );
    }
  };

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200">
      <table className="w-full text-left text-xs">
        <thead className="bg-slate-100 text-slate-600 font-semibold uppercase tracking-wider border-b border-slate-200">
          <tr>
            <th className="py-2.5 px-3">Field Name</th>
            <th className="py-2.5 px-3">Application Form Value</th>
            <th className="py-2.5 px-3">OCR Document Value</th>
            <th className="py-2.5 px-3">AI Confidence</th>
            <th className="py-2.5 px-3 text-right">Match Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 bg-white">
          {fieldKeys.map((key) => {
            const comp = comparisonResults[key] || {};
            const extracted = extractedFields[key] || {};
            const confidence =
              fieldConfidences[key] !== undefined
                ? fieldConfidences[key]
                : extracted.confidence;

            const appVal = comp.application_value !== undefined ? String(comp.application_value) : '—';
            const docVal =
              comp.document_value !== undefined
                ? String(comp.document_value)
                : extracted.value !== undefined
                ? String(extracted.value)
                : '—';
            const status = comp.status || (docVal !== '—' ? 'EXTRACTED' : 'NOT FOUND');

            const isMismatch = status === 'MISMATCH';

            return (
              <tr
                key={key}
                className={isMismatch ? 'bg-rose-50/60' : 'hover:bg-slate-50/70 transition-colors'}
              >
                <td className="py-2.5 px-3 font-semibold text-slate-800 capitalize">
                  {comp.label || key.replace(/_/g, ' ')}
                </td>
                <td className="py-2.5 px-3 font-mono text-slate-900 bg-slate-50/50">
                  {appVal}
                </td>
                <td className={`py-2.5 px-3 font-mono ${isMismatch ? 'text-rose-900 font-semibold' : 'text-slate-900'}`}>
                  {docVal}
                </td>
                <td className="py-2.5 px-3 text-slate-600">
                  {confidence !== undefined && confidence !== null ? (
                    <span
                      className={`inline-block font-mono ${
                        confidence >= 0.8
                          ? 'text-emerald-700 font-semibold'
                          : confidence >= 0.6
                          ? 'text-amber-700'
                          : 'text-rose-700 font-bold'
                      }`}
                    >
                      {(confidence * 100).toFixed(0)}%
                    </span>
                  ) : (
                    '—'
                  )}
                </td>
                <td className="py-2.5 px-3 text-right">
                  {getStatusPill(status)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
