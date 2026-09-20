import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { BookOpen, Settings, UserCheck, LogOut, FileText, ClipboardCheck, Award, BarChart3, CreditCard } from 'lucide-react';
import { authService, DEMO_CREDENTIALS } from '../services/authService';
import { UserProfile } from '../types/scheme';

export const Navbar: React.FC = () => {
  const location = useLocation();
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [loadingRole, setLoadingRole] = useState<string | null>(null);

  useEffect(() => {
    setCurrentUser(authService.getCurrentUser());
  }, []);

  const handleDemoSwitch = async (role: 'APPLICANT' | 'OFFICER' | 'COMMITTEE' | 'ADMIN') => {
    try {
      setLoadingRole(role);
      const user = await authService.demoLogin(role);
      setCurrentUser(user);
      // Reload page state or dispatch event so active view updates
      window.dispatchEvent(new Event('auth-changed'));
    } catch (err) {
      console.error('Demo login failed', err);
    } finally {
      setLoadingRole(null);
    }
  };

  const handleLogout = () => {
    authService.logout();
    setCurrentUser(null);
    window.dispatchEvent(new Event('auth-changed'));
  };

  return (
    <header className="bg-slate-900 text-white border-b border-slate-800 shadow-md">
      {/* 1. Official Ministry Header */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-full bg-teal-600 flex items-center justify-center font-bold text-lg text-white shadow-md">
            MoTA
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm sm:text-base font-semibold tracking-wide">
                Ministry of Tribal Affairs
              </h1>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-teal-900 text-teal-200 border border-teal-700">
                Phase 8 Fellowship & DBT Management
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Government of India | AI-Enabled Fellowship & Scholarship Portal
            </p>
          </div>
        </div>

        {/* Primary Navigation */}
        <nav className="flex items-center space-x-1 sm:space-x-3 text-sm font-medium">
          <Link
            to="/"
            className={`px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5 ${
              location.pathname === '/'
                ? 'bg-teal-700 text-white'
                : 'text-slate-300 hover:text-white hover:bg-slate-800'
            }`}
          >
            <BookOpen className="w-4 h-4" />
            Scheme Explorer
          </Link>
          <Link
            to="/applicant/dashboard"
            className={`px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5 ${
              location.pathname.startsWith('/applicant/dashboard') || location.pathname.startsWith('/applications')
                ? 'bg-teal-700 text-white'
                : 'text-slate-300 hover:text-white hover:bg-slate-800'
            }`}
          >
            <FileText className="w-4 h-4" />
            My Applications
          </Link>
          {currentUser?.role === 'APPLICANT' && (
            <Link
              to="/applicant/fellowship"
              className={`px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5 ${
                location.pathname === '/applicant/fellowship'
                  ? 'bg-emerald-700 text-white'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800'
              }`}
            >
              <Award className="w-4 h-4" />
              Fellowship Portal
            </Link>
          )}
          {(currentUser?.role === 'OFFICER' || currentUser?.role === 'ADMIN') && (
            <Link
              to="/officer/dashboard"
              className={`px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5 ${
                location.pathname === '/officer/dashboard'
                  ? 'bg-teal-700 text-white'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800'
              }`}
            >
              <ClipboardCheck className="w-4 h-4" />
              Officer Queue
            </Link>
          )}
          {(currentUser?.role === 'OFFICER' || currentUser?.role === 'ADMIN') && (
            <Link
              to="/officer/fellowships"
              className={`px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5 ${
                location.pathname === '/officer/fellowships'
                  ? 'bg-teal-700 text-white'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800'
              }`}
            >
              <BookOpen className="w-4 h-4" />
              Fellowship Scrutiny
            </Link>
          )}
          {(currentUser?.role === 'COMMITTEE' || currentUser?.role === 'ADMIN') && (
            <Link
              to="/committee"
              className={`px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5 ${
                location.pathname.startsWith('/committee')
                  ? 'bg-purple-700 text-white'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800'
              }`}
            >
              <Award className="w-4 h-4" />
              Committee Workbench
            </Link>
          )}
          {currentUser?.role === 'ADMIN' && (
            <Link
              to="/admin/disbursements"
              className={`px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5 ${
                location.pathname === '/admin/disbursements'
                  ? 'bg-indigo-700 text-white'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800'
              }`}
            >
              <CreditCard className="w-4 h-4" />
              Disbursement Desk
            </Link>
          )}
          {currentUser?.role === 'ADMIN' && (
            <Link
              to="/admin/analytics"
              className={`px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5 ${
                location.pathname === '/admin/analytics'
                  ? 'bg-indigo-700 text-white'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800'
              }`}
            >
              <BarChart3 className="w-4 h-4" />
              Executive Analytics
            </Link>
          )}
          <Link
            to="/admin/schemes"
            className={`px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5 ${
              location.pathname.startsWith('/admin/schemes')
                ? 'bg-amber-600 text-white'
                : 'text-slate-300 hover:text-white hover:bg-slate-800'
            }`}
          >
            <Settings className="w-4 h-4" />
            Admin Schemes
          </Link>
        </nav>
      </div>

      {/* 2. Isolated Demo Bar with High-Visibility Disclaimer */}
      <div className="bg-slate-950 border-t border-slate-800 px-4 py-2">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-amber-950/80 border border-amber-800 text-amber-300 font-semibold uppercase tracking-wider text-[10px]">
              Prototype Demo Mode
            </span>
            <span className="text-slate-400 hidden sm:inline">
              Simulated 1-click test authentication (Not a production security mechanism)
            </span>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-slate-400">Switch Role:</span>
            {(['APPLICANT', 'OFFICER', 'COMMITTEE', 'ADMIN'] as const).map((role) => {
              const isActive = currentUser?.role === role;
              return (
                <button
                  key={role}
                  onClick={() => handleDemoSwitch(role)}
                  disabled={loadingRole === role}
                  className={`px-2 py-1 rounded text-xs transition-all font-medium flex items-center gap-1 ${
                    isActive
                      ? 'bg-teal-600 text-white font-semibold ring-1 ring-teal-400 shadow-sm'
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white'
                  }`}
                  title={`Login as ${DEMO_CREDENTIALS[role].roleName}`}
                >
                  {isActive && <UserCheck className="w-3 h-3" />}
                  {loadingRole === role ? 'Switching...' : role}
                </button>
              );
            })}

            {currentUser && (
              <button
                onClick={handleLogout}
                className="ml-2 px-2 py-1 rounded bg-red-900/40 text-red-300 hover:bg-red-800/60 border border-red-800 text-xs flex items-center gap-1"
                title="Log out"
              >
                <LogOut className="w-3 h-3" />
                Logout
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
