import React from 'react';
import { AlertTriangle, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

interface DeficiencyBannerProps {
  applicationId: string;
  referenceId: string;
  deficiencyCount?: number;
}

export const DeficiencyBanner: React.FC<DeficiencyBannerProps> = ({
  applicationId,
  referenceId,
  deficiencyCount = 1,
}) => {
  return (
    <div className="bg-amber-500/10 border-l-4 border-amber-500 rounded-r-xl p-4 sm:p-5 mb-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 backdrop-blur-md">
      <div className="flex items-start gap-3">
        <div className="p-2 bg-amber-500/20 rounded-lg text-amber-400 shrink-0 mt-0.5">
          <AlertTriangle className="w-5 h-5" />
        </div>
        <div>
          <h4 className="text-amber-300 font-semibold text-sm sm:text-base">
            Action Required: Document Deficiencies Flagged
          </h4>
          <p className="text-gray-300 text-xs sm:text-sm mt-0.5 leading-relaxed">
            Application <span className="font-mono font-medium text-amber-200">{referenceId}</span> has {deficiencyCount} document deficiency item(s) flagged during desk scrutiny. Please upload valid replacements to continue your evaluation.
          </p>
        </div>
      </div>
      <Link
        to={`/applications/${applicationId}/deficiencies`}
        className="inline-flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold text-xs sm:text-sm rounded-lg transition-colors shrink-0 shadow-md shadow-amber-500/20"
      >
        Resolve Deficiencies
        <ArrowRight className="w-4 h-4" />
      </Link>
    </div>
  );
};
