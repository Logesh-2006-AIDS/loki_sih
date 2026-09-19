import React, { useState } from 'react';
import {
  X,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  RotateCcw,
  ShieldCheck,
} from 'lucide-react';
import { Scheme, SchemeDetail, SchemeVersion, EligibilityCheckResponse } from '../types/scheme';
import { schemeService } from '../services/schemeService';

interface Props {
  scheme: Scheme | SchemeDetail;
  version?: SchemeVersion | null;
  isOpen: boolean;
  onClose: () => void;
}

export const SelfEligibilityModal: React.FC<Props> = ({
  scheme,
  version,
  isOpen,
  onClose,
}) => {
  const [answers, setAnswers] = useState<Record<string, any>>({
    community: 'ST',
    min_qualifying_percentage: 60.0,
    max_annual_family_income: 450000,
    course_type: 'Ph.D.',
    max_age: 28,
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<EligibilityCheckResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const currentVersionLabel =
    version?.scheme_version || scheme.scheme_version || '1.0';

  const handleInputChange = (field: string, value: any) => {
    setAnswers((prev) => ({ ...prev, [field]: value }));
  };

  const handleEvaluate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await schemeService.checkEligibility(
        scheme.id,
        answers,
        version?.id
      );
      setResult(res);
    } catch (err: any) {
      console.error('Self check failed', err);
      setError(
        err.response?.data?.error ||
          'Failed to evaluate eligibility. Please check input values.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full overflow-hidden border border-slate-200 animate-in fade-in zoom-in-95 duration-200">
        {/* Modal Header */}
        <div className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-teal-600 flex items-center justify-center text-white font-bold">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold">
                  Self-Eligibility Checker
                </h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-teal-900 text-teal-200 border border-teal-700">
                  {scheme.scheme_code} v{currentVersionLabel}
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Deterministic rule evaluation for {scheme.name}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors p-1 rounded-lg hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Prototype & Legal Notice Bar */}
        <div className="bg-amber-50 border-b border-amber-200 px-6 py-2.5 text-xs text-amber-900">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-amber-950">
                PROTOTYPE / DEMO CONFIGURATION (Indicative Screening Only)
              </p>
              <p className="text-[11px] text-amber-800 mt-0.5">
                Self-check is indicative only. Final eligibility is subject to document verification and official scrutiny.
              </p>
            </div>
          </div>
        </div>

        <div className="p-6 max-h-[75vh] overflow-y-auto">
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-800 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 text-red-600" />
              <span>{error}</span>
            </div>
          )}

          {!result ? (
            /* Input Form */
            <form onSubmit={handleEvaluate} className="space-y-4">
              <p className="text-xs text-slate-500 mb-2">
                Enter your details below to run a fast, private self-check against the configured eligibility criteria. No data is stored or submitted.
              </p>

              {/* 1. Category / Community */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Community / Caste Category *
                </label>
                <select
                  value={answers.community || ''}
                  onChange={(e) => handleInputChange('community', e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
                >
                  <option value="ST">Scheduled Tribe (ST)</option>
                  <option value="SC">Scheduled Caste (SC)</option>
                  <option value="OBC">Other Backward Classes (OBC)</option>
                  <option value="GENERAL">General / Unreserved</option>
                  <option value="EWS">Economically Weaker Section (EWS)</option>
                </select>
                <p className="text-[11px] text-slate-400 mt-1">
                  MoTA schemes are formulated specifically for Scheduled Tribe candidates.
                </p>
              </div>

              {/* 2. Qualifying Marks */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Postgraduate / Qualifying Degree Marks (%) *
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="100"
                  value={answers.min_qualifying_percentage ?? ''}
                  onChange={(e) =>
                    handleInputChange(
                      'min_qualifying_percentage',
                      parseFloat(e.target.value) || 0
                    )
                  }
                  required
                  placeholder="e.g. 62.5"
                  className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Standard benchmark configured in prototype: Minimum 55.0% marks.
                </p>
              </div>

              {/* 3. Annual Family Income */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Total Annual Family Income (₹) *
                </label>
                <input
                  type="number"
                  min="0"
                  value={answers.max_annual_family_income ?? ''}
                  onChange={(e) =>
                    handleInputChange(
                      'max_annual_family_income',
                      parseFloat(e.target.value) || 0
                    )
                  }
                  required
                  placeholder="e.g. 450000"
                  className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Configured demo ceiling: ₹6,00,000 p.a. (NFST) / ₹8,00,000 p.a. (NOS).
                </p>
              </div>

              {/* 4. Course Type (For NFST) */}
              {scheme.scheme_code === 'NFST' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Course Level Enrolled *
                  </label>
                  <select
                    value={answers.course_type || 'Ph.D.'}
                    onChange={(e) =>
                      handleInputChange('course_type', e.target.value)
                    }
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
                  >
                    <option value="Ph.D.">Ph.D. (Regular)</option>
                    <option value="M.Phil">M.Phil</option>
                    <option value="Integrated Ph.D.">Integrated Ph.D.</option>
                    <option value="Postgraduate Diploma">Postgraduate Diploma</option>
                    <option value="Undergraduate">Undergraduate</option>
                  </select>
                </div>
              )}

              {/* 5. Age (For NOS) */}
              {scheme.scheme_code === 'NOS' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Candidate Age (Years) *
                  </label>
                  <input
                    type="number"
                    min="18"
                    max="80"
                    value={answers.max_age ?? 28}
                    onChange={(e) =>
                      handleInputChange('max_age', parseInt(e.target.value, 10) || 0)
                    }
                    required
                    className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                  <p className="text-[11px] text-slate-400 mt-1">
                    Configured demo age ceiling: 35 years.
                  </p>
                </div>
              )}

              <div className="pt-4 border-t border-slate-100 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-medium text-slate-600 hover:text-slate-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-teal-700 hover:bg-teal-800 text-white text-xs font-semibold shadow-sm transition-all"
                >
                  {loading ? 'Evaluating Rules...' : 'Run Self-Check'}
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </form>
          ) : (
            /* Results View */
            <div className="space-y-5 animate-in fade-in">
              {/* Result Summary Banner */}
              <div
                className={`p-4 rounded-xl border ${
                  result.eligible
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-950'
                    : 'bg-amber-50 border-amber-200 text-amber-950'
                }`}
              >
                <div className="flex items-start gap-3">
                  {result.eligible ? (
                    <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0 mt-0.5" />
                  ) : (
                    <AlertTriangle className="w-6 h-6 text-amber-600 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <h4 className="text-sm font-bold">
                      {result.summary_message}
                    </h4>
                    <p className="text-xs mt-1 text-slate-600">
                      {result.disclaimer}
                    </p>
                  </div>
                </div>
              </div>

              {/* Itemized Rule Checks */}
              <div>
                <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2.5">
                  Detailed Criteria Evaluation Breakdown
                </h5>
                <div className="space-y-2">
                  {result.checks.map((check, idx) => (
                    <div
                      key={idx}
                      className={`p-3 rounded-lg border flex items-start justify-between gap-3 text-xs ${
                        check.passed
                          ? 'bg-white border-slate-200'
                          : 'bg-red-50/50 border-red-200'
                      }`}
                    >
                      <div className="flex items-start gap-2.5">
                        {check.passed ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                        ) : (
                          <X className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                        )}
                        <div>
                          <p className="font-semibold text-slate-900">
                            {check.label}
                          </p>
                          <p
                            className={`text-[11px] mt-0.5 ${
                              check.passed ? 'text-slate-600' : 'text-red-700 font-medium'
                            }`}
                          >
                            {check.message}
                          </p>
                        </div>
                      </div>

                      <div className="text-right shrink-0">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                            check.passed
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {check.passed ? 'PASSED' : 'NOT MET'}
                        </span>
                        <p className="text-[10px] text-slate-400 mt-1">
                          Actual: {String(check.actual ?? 'N/A')}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
                <button
                  type="button"
                  onClick={handleReset}
                  className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-600 hover:text-slate-900 transition-colors"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Test Different Values
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="px-5 py-2 text-xs font-semibold rounded-lg bg-slate-900 text-white hover:bg-slate-800 transition-colors"
                >
                  Done
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
