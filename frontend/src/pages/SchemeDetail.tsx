import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  CheckCircle2,
  FileText,
  AlertCircle,
  Lock,
  Unlock,
} from 'lucide-react';
import { SchemeDetail as SchemeDetailType, SchemeVersion } from '../types/scheme';
import { schemeService } from '../services/schemeService';
import { applicationService } from '../services/applicationService';
import { authService } from '../services/authService';
import { SelfEligibilityModal } from '../components/SelfEligibilityModal';

export const SchemeDetail: React.FC = () => {
  const { schemeId } = useParams<{ schemeId: string }>();
  const navigate = useNavigate();

  const [scheme, setScheme] = useState<SchemeDetailType | null>(null);
  const [versions, setVersions] = useState<SchemeVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'eligibility' | 'documents' | 'versions'>('overview');
  const [isCheckModalOpen, setIsCheckModalOpen] = useState(false);
  const [selectedVersionForCheck, setSelectedVersionForCheck] = useState<SchemeVersion | null>(null);

  const handleApply = async () => {
    if (!scheme) return;
    try {
      if (!authService.isAuthenticated()) {
        await authService.demoLogin('APPLICANT');
        window.dispatchEvent(new Event('auth-changed'));
      }
      const draft = await applicationService.createDraft(scheme.id);
      navigate(`/applications/${draft.id}`);
    } catch (err: any) {
      console.error('Failed to start application', err);
      alert(err.response?.data?.error || 'Unable to start application draft.');
    }
  };

  useEffect(() => {
    if (schemeId) {
      loadSchemeData(schemeId);
    }
  }, [schemeId]);

  const loadSchemeData = async (id: string) => {
    try {
      setLoading(true);
      const [detailData, versionList] = await Promise.all([
        schemeService.getScheme(id),
        schemeService.getSchemeVersions(id),
      ]);
      setScheme(detailData);
      setVersions(versionList);
    } catch (err) {
      console.error('Failed to load scheme details', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="inline-block w-8 h-8 border-4 border-teal-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="mt-3 text-xs text-slate-500">Loading scheme details...</p>
        </div>
      </div>
    );
  }

  if (!scheme) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
        <div className="text-center bg-white p-8 rounded-xl border border-slate-200 shadow-sm max-w-md">
          <AlertCircle className="w-10 h-10 text-red-500 mx-auto mb-3" />
          <h2 className="text-base font-bold text-slate-900">Scheme not found</h2>
          <p className="text-xs text-slate-500 mt-1 mb-4">The requested scheme ID does not exist.</p>
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-semibold"
          >
            Back to Scheme Explorer
          </button>
        </div>
      </div>
    );
  }

  const activeV = scheme.active_version;
  const rawDocs = activeV?.required_documents || scheme.required_documents || {};
  const docList = rawDocs.documents || [];

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Back navigation */}
        <button
          onClick={() => navigate('/')}
          className="inline-flex items-center gap-2 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Scheme Explorer
        </button>

        {/* Header Card */}
        <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div>
              <div className="flex items-center gap-2 flex-wrap mb-2">
                <span className="font-mono font-bold text-xs px-2.5 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-200">
                  {scheme.scheme_code}
                </span>
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-200">
                  Active v{scheme.scheme_version}
                </span>
                {scheme.is_demo && (
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-200">
                    Demonstration Configuration
                  </span>
                )}
              </div>
              <h1 className="text-xl sm:text-3xl font-extrabold text-slate-900">
                {scheme.name}
              </h1>
              <p className="text-xs sm:text-sm text-slate-500 mt-2 max-w-2xl">
                {scheme.description}
              </p>
            </div>

            {/* Quick Action Buttons */}
            <div className="shrink-0 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
              <button
                onClick={() => {
                  setSelectedVersionForCheck(activeV || null);
                  setIsCheckModalOpen(true);
                }}
                className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-teal-50 hover:bg-teal-100 text-teal-800 text-xs sm:text-sm font-bold border border-teal-200 transition-all shadow-sm"
              >
                <CheckCircle2 className="w-4 h-4" />
                Check Eligibility
              </button>
              <button
                onClick={handleApply}
                className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-teal-700 hover:bg-teal-800 text-white text-xs sm:text-sm font-bold shadow-md hover:shadow-lg transition-all"
              >
                <span>Apply for Fellowship</span>
              </button>
            </div>
          </div>

          {/* Prototype Notice Alert */}
          <div className="mt-6 p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 text-amber-700 shrink-0" />
            <span>
              <strong>Prototype Disclaimer:</strong> Eligibility rules, income limits, and required documents shown here are demo configurations for Smart India Hackathon testing. Official gazetted guidelines are subject to verification.
            </span>
          </div>

          {/* Navigation Tabs */}
          <div className="flex border-b border-slate-200 mt-6 -mb-6 gap-6 overflow-x-auto text-xs sm:text-sm font-semibold">
            <button
              onClick={() => setActiveTab('overview')}
              className={`pb-3 border-b-2 transition-colors ${
                activeTab === 'overview'
                  ? 'border-teal-700 text-teal-800'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              Overview & Objectives
            </button>
            <button
              onClick={() => setActiveTab('eligibility')}
              className={`pb-3 border-b-2 transition-colors ${
                activeTab === 'eligibility'
                  ? 'border-teal-700 text-teal-800'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              Eligibility Criteria
            </button>
            <button
              onClick={() => setActiveTab('documents')}
              className={`pb-3 border-b-2 transition-colors ${
                activeTab === 'documents'
                  ? 'border-teal-700 text-teal-800'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              Required Documents
            </button>
            <button
              onClick={() => setActiveTab('versions')}
              className={`pb-3 border-b-2 transition-colors flex items-center gap-1.5 ${
                activeTab === 'versions'
                  ? 'border-teal-700 text-teal-800'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              Version History ({versions.length})
            </button>
          </div>
        </div>

        {/* Tab Content */}
        <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-2">
                  Scheme Scope & Mandate
                </h3>
                <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                  {scheme.description}
                </p>
              </div>

              <div className="grid sm:grid-cols-2 gap-4 pt-4 border-t border-slate-100 text-xs">
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-100">
                  <span className="font-semibold text-slate-700 block mb-1">Target Community</span>
                  <p className="text-slate-600">Exclusively Scheduled Tribe (ST) scholars & researchers</p>
                </div>
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-100">
                  <span className="font-semibold text-slate-700 block mb-1">Authoritative Version</span>
                  <p className="text-slate-600">v{scheme.scheme_version} (Current Gazetted Prototype)</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'eligibility' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                    Configured Eligibility Parameters (v{scheme.scheme_version})
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Evaluated deterministically by the rules engine without AI or manual bias.
                  </p>
                </div>
                <button
                  onClick={() => {
                    setSelectedVersionForCheck(activeV || null);
                    setIsCheckModalOpen(true);
                  }}
                  className="px-3 py-1.5 rounded-lg bg-teal-50 hover:bg-teal-100 text-teal-800 font-semibold text-xs border border-teal-200 transition-colors"
                >
                  Run Checker
                </button>
              </div>

              <div className="grid sm:grid-cols-2 gap-4 text-xs">
                <div className="p-4 rounded-xl border border-slate-200 bg-white">
                  <span className="text-slate-500 font-medium block">Community / Category</span>
                  <span className="text-sm font-bold text-slate-900 mt-1 block">Scheduled Tribe (ST)</span>
                  <p className="text-[11px] text-slate-400 mt-1">Valid Caste/Community certificate required.</p>
                </div>

                <div className="p-4 rounded-xl border border-slate-200 bg-white">
                  <span className="text-slate-500 font-medium block">Qualifying Academic Marks</span>
                  <span className="text-sm font-bold text-slate-900 mt-1 block">Minimum 55.0%</span>
                  <p className="text-[11px] text-slate-400 mt-1">Or equivalent CGPA in postgraduate examination.</p>
                </div>

                <div className="p-4 rounded-xl border border-slate-200 bg-white">
                  <span className="text-slate-500 font-medium block">Family Income Ceiling</span>
                  <span className="text-sm font-bold text-slate-900 mt-1 block">
                    {scheme.scheme_code === 'NFST' ? '₹6,00,000 p.a.' : '₹8,00,000 p.a.'}
                  </span>
                  <p className="text-[11px] text-slate-400 mt-1">Annual combined income from all sources.</p>
                </div>

                {scheme.scheme_code === 'NOS' && (
                  <div className="p-4 rounded-xl border border-slate-200 bg-white">
                    <span className="text-slate-500 font-medium block">Maximum Age Ceiling</span>
                    <span className="text-sm font-bold text-slate-900 mt-1 block">35 Years</span>
                    <p className="text-[11px] text-slate-400 mt-1">As on application closing window.</p>
                  </div>
                )}

                {scheme.scheme_code === 'NFST' && (
                  <div className="p-4 rounded-xl border border-slate-200 bg-white">
                    <span className="text-slate-500 font-medium block">Eligible Degree Levels</span>
                    <span className="text-sm font-bold text-slate-900 mt-1 block">M.Phil / Ph.D. (Regular)</span>
                    <p className="text-[11px] text-slate-400 mt-1">In UGC-recognized universities or institutions.</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'documents' && (
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                  Mandatory Submission Documents
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Applicants must upload clear digital copies (PDF/JPEG) for verification.
                </p>
              </div>

              {docList.length > 0 ? (
                <div className="space-y-2.5">
                  {docList.map((doc: any, i: number) => (
                    <div
                      key={i}
                      className="p-3.5 rounded-xl border border-slate-200 flex items-center justify-between text-xs bg-slate-50/50"
                    >
                      <div className="flex items-center gap-3">
                        <FileText className="w-5 h-5 text-teal-600 shrink-0" />
                        <div>
                          <span className="font-bold text-slate-900 block">{doc.label}</span>
                          <span className="text-[11px] text-slate-400 font-mono">Code: {doc.type}</span>
                        </div>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">
                        MANDATORY
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500">No document checklist configured for this version.</p>
              )}
            </div>
          )}

          {activeTab === 'versions' && (
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                  Scheme Version History & Architecture
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  The system enforces strict version immutability. Historical applications bind permanently to their submission version.
                </p>
              </div>

              <div className="divide-y divide-slate-100 border border-slate-200 rounded-xl overflow-hidden text-xs">
                {versions.map((v) => (
                  <div
                    key={v.id}
                    className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white hover:bg-slate-50 transition-colors"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm text-slate-900">
                          v{v.scheme_version}
                        </span>
                        {v.is_active ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                            CURRENT ACTIVE
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600">
                            INACTIVE
                          </span>
                        )}
                        {v.is_locked ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-200 text-slate-800 flex items-center gap-1">
                            <Lock className="w-3 h-3" /> Locked
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700 flex items-center gap-1">
                            <Unlock className="w-3 h-3" /> Unlocked
                          </span>
                        )}
                      </div>
                      <p className="text-slate-500 mt-1">
                        {v.name}
                      </p>
                      <p className="text-[10px] text-slate-400 mt-0.5">
                        Created: {new Date(v.created_at).toLocaleDateString()}
                      </p>
                    </div>

                    <button
                      onClick={() => {
                        setSelectedVersionForCheck(v);
                        setIsCheckModalOpen(true);
                      }}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-teal-50 hover:bg-teal-100 text-teal-800 font-semibold text-xs border border-teal-200 transition-colors shrink-0"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Check Against v{v.scheme_version}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Self-Eligibility Modal */}
      {isCheckModalOpen && (
        <SelfEligibilityModal
          scheme={scheme}
          version={selectedVersionForCheck}
          isOpen={isCheckModalOpen}
          onClose={() => setIsCheckModalOpen(false)}
        />
      )}
    </div>
  );
};
