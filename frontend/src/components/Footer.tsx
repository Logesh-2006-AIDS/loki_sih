import React from 'react';
import { AlertCircle } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-white border-t border-slate-200 py-6 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <div>
            <p className="font-semibold text-slate-700">
              © 2026 Ministry of Tribal Affairs, Government of India. All rights reserved.
            </p>
            <p className="mt-0.5">
              AI-Enabled Scholarship & Fellowship Management System | Smart India Hackathon (SIH) Prototype
            </p>
          </div>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 text-xs">
            <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>
              <strong>Disclaimer:</strong> Scheme eligibility criteria & scoring thresholds shown in this prototype are demonstration data only.
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
};
