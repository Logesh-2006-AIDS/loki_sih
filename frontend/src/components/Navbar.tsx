import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  BookOpen,
  Settings,
  LogOut,
  FileText,
  ClipboardCheck,
  Award,
  BarChart3,
  CreditCard,
  UserCheck,
  LogIn,
} from 'lucide-react';
import { authService } from '../services/authService';
import { UserProfile } from '../types/scheme';

export const Navbar: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);

  const syncUser = () => {
    setCurrentUser(authService.getCurrentUser());
  };

  useEffect(() => {
    syncUser();
    // Validate session with backend /auth/me on mount
    authService.fetchCurrentUser().then((user) => {
      setCurrentUser(user);
    });

    const handleAuthChanged = () => syncUser();
    window.addEventListener('auth-changed', handleAuthChanged);
    return () => window.removeEventListener('auth-changed', handleAuthChanged);
  }, []);

  const handleLogout = () => {
    authService.logout();
    setCurrentUser(null);
    navigate('/login', { replace: true });
  };

  const getRoleLabel = (role?: string) => {
    switch (role) {
      case 'APPLICANT':
        return 'Applicant';
      case 'OFFICER':
        return 'Desk Officer';
      case 'COMMITTEE':
        return 'Committee';
      case 'ADMIN':
        return 'Administrator';
      default:
        return 'User';
    }
  };

  const isRole = (role: string) => currentUser?.role === role;

  return (
    <header className="bg-slate-900 text-white border-b border-slate-800 shadow-md">
      {/* Official Ministry Header */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex flex-wrap items-center justify-between gap-4">
        <Link to="/" className="flex items-center space-x-3 group">
          <div className="w-10 h-10 rounded-full bg-teal-600 flex items-center justify-center font-bold text-lg text-white shadow-md group-hover:bg-teal-500 transition-colors">
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
        </Link>

        {/* Primary Role-Aware Navigation */}
        <nav className="flex items-center space-x-1 sm:space-x-2 text-sm font-medium flex-wrap">
          {/* Public / Common Navigation */}
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

          {/* Applicant Navigation */}
          {isRole('APPLICANT') && (
            <>
              <Link
                to="/applicant/dashboard"
                className={`px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5 ${
                  location.pathname.startsWith('/applicant/dashboard') ||
                  location.pathname.startsWith('/applications')
                    ? 'bg-teal-700 text-white'
                    : 'text-slate-300 hover:text-white hover:bg-slate-800'
                }`}
              >
                <FileText className="w-4 h-4" />
                My Applications
              </Link>
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
            </>
          )}

          {/* Officer Navigation */}
          {isRole('OFFICER') && (
            <>
              <Link
                to="/officer/dashboard"
                className={`px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5 ${
                  location.pathname === '/officer/dashboard' ||
                  location.pathname.includes('/scrutiny')
                    ? 'bg-teal-700 text-white'
                    : 'text-slate-300 hover:text-white hover:bg-slate-800'
                }`}
              >
                <ClipboardCheck className="w-4 h-4" />
                Officer Queue
              </Link>
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
            </>
          )}

          {/* Committee Navigation */}
          {isRole('COMMITTEE') && (
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

          {/* Administrator Navigation */}
          {isRole('ADMIN') && (
            <>
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
              <Link
                to="/admin/user-approvals"
                className={`px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5 ${
                  location.pathname.startsWith('/admin/user-approvals')
                    ? 'bg-amber-600 text-white'
                    : 'text-slate-300 hover:text-white hover:bg-slate-800'
                }`}
              >
                <UserCheck className="w-4 h-4" />
                User Approvals
              </Link>
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
            </>
          )}

          {/* User Account State Controls */}
          {currentUser ? (
            <div className="flex items-center gap-2 pl-2 sm:pl-4 border-l border-slate-700 ml-1">
              <div className="flex flex-col text-right">
                <span className="text-xs font-semibold text-white leading-tight">
                  {currentUser.full_name}
                </span>
                <span className="text-[10px] text-teal-300 font-medium">
                  {getRoleLabel(currentUser.role)}
                </span>
              </div>
              <button
                onClick={handleLogout}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md bg-slate-800 hover:bg-red-900/60 hover:text-red-200 text-slate-300 text-xs font-medium border border-slate-700 transition-colors"
                title="Log out of portal"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold shadow-sm transition-colors ml-2"
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>Login</span>
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
};

export default Navbar;
