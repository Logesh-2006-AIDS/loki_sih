import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { ShieldCheck, Lock, Mail, AlertCircle, Loader2, Eye, EyeOff, XCircle } from 'lucide-react';
import { authService } from '../services/authService';
import { getRoleDashboard } from '../components/auth/ProtectedRoute';

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [rejectionInfo, setRejectionInfo] = useState<{ message: string; reason: string } | null>(null);

  // If already authenticated, redirect immediately to canonical dashboard
  useEffect(() => {
    if (authService.isAuthenticated()) {
      const user = authService.getCurrentUser();
      if (user) {
        navigate(getRoleDashboard(user.role), { replace: true });
      }
    }
  }, [navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setRejectionInfo(null);

    if (!email.trim() || !password) {
      setErrorMessage('Please enter both email address and password.');
      return;
    }

    setIsLoading(true);
    try {
      const user = await authService.login(email, password);
      // Determine destination
      const fromPath = (location.state as any)?.from?.pathname;
      if (fromPath && fromPath !== '/login') {
        navigate(fromPath, { replace: true });
      } else {
        navigate(getRoleDashboard(user.role), { replace: true });
      }
    } catch (err: any) {
      console.error('Authentication failure', err);
      const resData = err.response?.data;
      if (err.response?.status === 403 && resData?.reason) {
        setRejectionInfo({
          message: resData.error || 'Your registration request was not approved.',
          reason: String(resData.reason),
        });
      } else {
        const detail = resData?.error || resData?.detail;
        if (detail && typeof detail === 'string') {
          setErrorMessage(detail);
        } else {
          setErrorMessage('Invalid email or password. Please verify your credentials.');
        }
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[85vh] flex flex-col justify-center items-center px-4 py-12 bg-slate-50">
      <div className="w-full max-w-md">
        {/* Ministry Branding Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-teal-700 text-white font-bold text-xl shadow-lg mb-3">
            MoTA
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Ministry of Tribal Affairs
          </h1>
          <p className="text-xs text-slate-500 font-medium mt-1">
            Government of India | AI-Enabled Fellowship & Scholarship Portal
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden">
          <div className="bg-slate-900 px-6 py-4 text-white flex items-center justify-between border-b border-slate-800">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-teal-400" />
              <h2 className="text-sm font-semibold tracking-wide">Portal Authentication</h2>
            </div>
            <span className="text-[11px] font-mono text-slate-400">Secure Access</span>
          </div>

          <form onSubmit={handleSubmit} className="p-6 sm:p-8 space-y-5">
            {rejectionInfo && (
              <div
                id="rejection-alert"
                className="p-4 rounded-xl bg-red-50 border border-red-200 text-xs text-red-900 space-y-2.5 animate-in fade-in duration-150"
              >
                <div className="flex items-center gap-2 text-red-800 font-bold text-sm">
                  <XCircle className="w-5 h-5 shrink-0 text-red-600" />
                  <span>Registration Not Approved</span>
                </div>
                <p className="font-medium text-slate-700">
                  {rejectionInfo.message}
                </p>
                <div className="p-3 bg-white/90 rounded-lg border border-red-100 text-slate-800 space-y-1">
                  <span className="text-[11px] font-semibold text-slate-500 block">
                    Reason provided by the administrator:
                  </span>
                  <p className="text-xs font-semibold text-red-950 italic whitespace-pre-wrap">
                    "{rejectionInfo.reason}"
                  </p>
                </div>
                <p className="text-[11px] text-slate-500">
                  Please contact the portal administrator at{' '}
                  <a
                    href="mailto:loki@gmail.com"
                    className="font-semibold text-teal-700 hover:text-teal-800 underline underline-offset-2"
                  >
                    loki@gmail.com
                  </a>{' '}
                  if you believe this decision was made in error.
                </p>
              </div>
            )}

            {errorMessage && !rejectionInfo && (
              <div className="p-3.5 rounded-lg bg-red-50 border border-red-200 flex items-start gap-2.5 text-xs text-red-700 animate-in fade-in duration-150">
                <AlertCircle className="w-4 h-4 shrink-0 text-red-600 mt-0.5" />
                <span className="font-medium">{errorMessage}</span>
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-xs font-semibold text-slate-700 mb-1.5">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  id="email"
                  type="email"
                  required
                  autoFocus
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="e.g. name@example.gov.in"
                  className="w-full pl-9 pr-3 py-2 text-sm bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-600 focus:border-teal-600 outline-hidden transition"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-semibold text-slate-700 mb-1.5">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your account password"
                  className="w-full pl-9 pr-11 py-2 text-sm bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-600 focus:border-teal-600 outline-hidden transition"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-500 hover:text-slate-700 cursor-pointer z-10 focus:outline-hidden"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  title={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-5 h-5 text-slate-500 hover:text-slate-700" /> : <Eye className="w-5 h-5 text-slate-500 hover:text-slate-700" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-2 py-2.5 px-4 rounded-lg bg-teal-700 hover:bg-teal-800 focus:ring-4 focus:ring-teal-200 text-white font-semibold text-sm transition-all shadow-md flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Verifying Credentials...</span>
                </>
              ) : (
                <span>Login</span>
              )}
            </button>
            <div className="text-center pt-2 border-t border-slate-100">
              <p className="text-xs text-slate-500">
                Don't have an account?{' '}
                <Link to="/register" className="font-semibold text-teal-700 hover:underline">
                  Create Account
                </Link>
              </p>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Login;
