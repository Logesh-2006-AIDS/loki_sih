import React from 'react';
import { Award, BookOpen, ShieldCheck, CheckCircle2, ArrowRight } from 'lucide-react';

export const App: React.FC = () => {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      {/* Top Gov Header */}
      <header className="bg-slate-900 text-white border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-full bg-teal-600 flex items-center justify-center font-bold text-lg text-white shadow-md">
              MoTA
            </div>
            <div>
              <h1 className="text-sm sm:text-base font-semibold tracking-wide">
                Ministry of Tribal Affairs
              </h1>
              <p className="text-xs text-slate-400">
                Government of India | AI-Enabled Fellowship & Scholarship Portal
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-teal-900 text-teal-200 border border-teal-700">
              Phase 0 Foundation
            </span>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="text-center max-w-3xl mx-auto mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-medium mb-4">
            <ShieldCheck className="w-4 h-4 text-teal-600" />
            AI-Driven Automated Verification & Transparent Evaluation
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            National Scholarship & Fellowship Management System
          </h2>
          <p className="mt-4 text-base sm:text-lg text-slate-600">
            Empowering Scheduled Tribe (ST) students and scholars with automated eligibility verification,
            transparent merit processing, and direct scheme disbursement management.
          </p>
        </div>

        {/* Schemes Grid */}
        <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
          {/* NFST Scheme Card */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-lg bg-teal-100 text-teal-700 flex items-center justify-center mb-4">
              <BookOpen className="w-6 h-6" />
            </div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xl font-bold text-slate-900">NFST Scheme</h3>
              <span className="text-xs font-semibold px-2 py-1 rounded bg-amber-100 text-amber-800 border border-amber-200">
                Higher Education
              </span>
            </div>
            <p className="text-sm text-slate-600 mb-4">
              National Fellowship for Higher Education of ST Students pursuing regular M.Phil. and Ph.D. degrees in Sciences, Humanities, and Engineering.
            </p>
            <ul className="space-y-2 mb-6 text-sm text-slate-600">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-teal-600" />
                M.Phil & Ph.D Fellowship Grants
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-teal-600" />
                Automated UGC/NET & Document Verification
              </li>
            </ul>
            <button className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-teal-700 hover:bg-teal-800 text-white text-sm font-medium transition-colors">
              Explore Scheme
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          {/* NOS Scheme Card */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center mb-4">
              <Award className="w-6 h-6" />
            </div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xl font-bold text-slate-900">NOS Scheme</h3>
              <span className="text-xs font-semibold px-2 py-1 rounded bg-teal-100 text-teal-800 border border-teal-200">
                Overseas Studies
              </span>
            </div>
            <p className="text-sm text-slate-600 mb-4">
              National Overseas Scholarship scheme for ST candidates selected to pursue Master's, Ph.D., and Post-Doctoral research programs abroad.
            </p>
            <ul className="space-y-2 mb-6 text-sm text-slate-600">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-amber-600" />
                Top 500 QS World University Ranked Institutions
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-amber-600" />
                Tuition, Contingency & Living Allowances
              </li>
            </ul>
            <button className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-sm font-medium transition-colors">
              Explore Scheme
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-6 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-xs text-slate-500">
          <p>© 2026 Ministry of Tribal Affairs, Government of India. All rights reserved.</p>
          <p className="mt-1">Smart India Hackathon (SIH) | Prototype v0.1.0</p>
        </div>
      </footer>
    </div>
  );
};

export default App;
