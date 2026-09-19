import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BookOpen,
  Award,
  Search,
  CheckCircle2,
  ArrowRight,
  ShieldCheck,
  AlertCircle,
  FileText,
} from 'lucide-react';
import { Scheme } from '../types/scheme';
import { schemeService } from '../services/schemeService';
import { SelfEligibilityModal } from '../components/SelfEligibilityModal';

export const SchemeExplorer: React.FC = () => {
  const navigate = useNavigate();
  const [schemes, setSchemes] = useState<Scheme[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [activeCheckScheme, setActiveCheckScheme] = useState<Scheme | null>(null);

  useEffect(() => {
    fetchSchemes();
  }, []);

  const fetchSchemes = async () => {
    try {
      setLoading(true);
      const data = await schemeService.getSchemes();
      setSchemes(data);
    } catch (err) {
      console.error('Failed to load schemes', err);
    } finally {
      setLoading(false);
    }
  };

  const filteredSchemes = schemes.filter((s) => {
    const matchesSearch =
      s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.scheme_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (s.description || '').toLowerCase().includes(searchTerm.toLowerCase());

    if (selectedCategory === 'ALL') return matchesSearch;
    if (selectedCategory === 'HIGHER')
      return matchesSearch && s.scheme_code === 'NFST';
    if (selectedCategory === 'OVERSEAS')
      return matchesSearch && s.scheme_code === 'NOS';
    return matchesSearch;
  });

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      {/* Hero Banner */}
      <section className="bg-slate-900 text-white py-12 px-4 sm:px-6 lg:px-8 border-b border-slate-800">
        <div className="max-w-5xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-950 border border-teal-700 text-teal-300 text-xs font-semibold mb-4">
            <ShieldCheck className="w-4 h-4 text-teal-400" />
            Configurable Scheme Engine — Phase 1 Architecture
          </div>
          <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight">
            National Scholarship & Fellowship Explorer
          </h1>
          <p className="mt-3 text-sm sm:text-base text-slate-300 max-w-3xl mx-auto">
            Discover Central Sector Fellowships and Overseas Scholarships for Scheduled Tribe (ST) scholars.
            Run fast, private self-eligibility checks against versioned scheme rules.
          </p>

          {/* Prototype Disclaimer Banner */}
          <div className="mt-6 max-w-2xl mx-auto px-4 py-2.5 rounded-xl bg-amber-950/80 border border-amber-800 text-amber-200 text-xs flex items-center justify-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              <strong>Demonstration Prototype:</strong> Official rules and gazetted criteria are pending administrative verification.
            </span>
          </div>
        </div>
      </section>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Search and Category Filters */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-8 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search scheme name or code (NFST, NOS)..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-xs sm:text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500"
            />
          </div>

          <div className="flex items-center gap-1.5 self-start sm:self-auto w-full sm:w-auto overflow-x-auto">
            <button
              onClick={() => setSelectedCategory('ALL')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                selectedCategory === 'ALL'
                  ? 'bg-teal-700 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              All Schemes
            </button>
            <button
              onClick={() => setSelectedCategory('HIGHER')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                selectedCategory === 'HIGHER'
                  ? 'bg-teal-700 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              Higher Education (Ph.D.)
            </button>
            <button
              onClick={() => setSelectedCategory('OVERSEAS')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                selectedCategory === 'OVERSEAS'
                  ? 'bg-teal-700 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              Overseas Studies
            </button>
          </div>
        </div>

        {/* Schemes Grid */}
        {loading ? (
          <div className="text-center py-16">
            <div className="inline-block w-8 h-8 border-4 border-teal-600 border-t-transparent rounded-full animate-spin"></div>
            <p className="mt-3 text-xs text-slate-500">Loading active schemes...</p>
          </div>
        ) : filteredSchemes.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-xl border border-slate-200 p-8">
            <BookOpen className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h3 className="text-sm font-semibold text-slate-800">No schemes found</h3>
            <p className="text-xs text-slate-500 mt-1">Try adjusting your search query.</p>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 gap-6">
            {filteredSchemes.map((s) => {
              const isNFST = s.scheme_code === 'NFST';
              return (
                <div
                  key={s.id}
                  className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col hover:shadow-md transition-shadow"
                >
                  {/* Card Top */}
                  <div className="flex items-start justify-between gap-3 mb-4">
                    <div className="flex items-center space-x-3">
                      <div
                        className={`w-12 h-12 rounded-xl flex items-center justify-center font-bold text-lg ${
                          isNFST
                            ? 'bg-teal-100 text-teal-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {isNFST ? <BookOpen className="w-6 h-6" /> : <Award className="w-6 h-6" />}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                            {s.scheme_code}
                          </span>
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                            Active v{s.scheme_version}
                          </span>
                          {s.is_demo && (
                            <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-200">
                              Demo Config
                            </span>
                          )}
                        </div>
                        <h3 className="text-base sm:text-lg font-bold text-slate-900 mt-1">
                          {s.name}
                        </h3>
                      </div>
                    </div>
                  </div>

                  {/* Description */}
                  <p className="text-xs sm:text-sm text-slate-600 mb-5 flex-1 line-clamp-3">
                    {s.description}
                  </p>

                  {/* Highlights */}
                  <div className="space-y-1.5 mb-6 text-xs text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-100">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-3.5 h-3.5 text-teal-600 shrink-0" />
                      <span>
                        Target: {isNFST ? 'ST Scholars pursuing M.Phil / Ph.D. in India' : 'ST Candidates for Masters / Ph.D. abroad'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <FileText className="w-3.5 h-3.5 text-teal-600 shrink-0" />
                      <span>
                        Mandatory documents: Caste, Marksheets, Income Certificate
                      </span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-100">
                    <button
                      onClick={() => setActiveCheckScheme(s)}
                      className="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-teal-50 hover:bg-teal-100 text-teal-800 text-xs font-semibold border border-teal-200 transition-colors"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Check Eligibility
                    </button>
                    <button
                      onClick={() => navigate(`/schemes/${s.id}`)}
                      className="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold transition-colors"
                    >
                      View Details
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>

      {/* Self-Eligibility Modal */}
      {activeCheckScheme && (
        <SelfEligibilityModal
          scheme={activeCheckScheme}
          isOpen={!!activeCheckScheme}
          onClose={() => setActiveCheckScheme(null)}
        />
      )}
    </div>
  );
};
