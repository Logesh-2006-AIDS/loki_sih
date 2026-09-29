import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  Lock,
  Mail,
  User,
  Phone,
  Building,
  Briefcase,
  MapPin,
  BadgeAlert,
  AlertCircle,
  CheckCircle2,
  Loader2,
  GraduationCap,
  ClipboardCheck,
  Award,
  Eye,
  EyeOff,
} from 'lucide-react';
import { authService } from '../services/authService';

type RegisterRole = 'APPLICANT' | 'OFFICER' | 'COMMITTEE';

export const Register: React.FC = () => {
  const navigate = useNavigate();

  const [role, setRole] = useState<RegisterRole>('APPLICANT');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Password Visibility Toggles
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Staff specific fields
  const [employeeId, setEmployeeId] = useState('');
  const [department, setDepartment] = useState('');
  const [designation, setDesignation] = useState('');
  const [jurisdiction, setJurisdiction] = useState('');

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [submittedSuccess, setSubmittedSuccess] = useState<RegisterRole | null>(null);

  const handleRoleChange = (newRole: RegisterRole) => {
    setRole(newRole);
    setErrors({});
    setErrorMessage(null);
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    // 1. Full Name
    const trimmedName = fullName.trim();
    if (!trimmedName) {
      newErrors.fullName = 'Full Name is required';
    } else if (trimmedName.length < 2 || trimmedName.length > 100) {
      newErrors.fullName = 'Full Name must be between 2 and 100 characters';
    } else if (!/^[a-zA-Z\s\.\-']+$/.test(trimmedName)) {
      newErrors.fullName = 'Full Name can only contain letters and spaces';
    }

    // 2. Email Address
    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      newErrors.email = 'Enter a valid email address';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      newErrors.email = 'Enter a valid email address';
    }

    // 3. Mobile Number (10-digit Indian Mobile)
    const rawPhone = phone.trim().replace(/[\s\-]/g, '');
    if (!rawPhone) {
      newErrors.phone = 'Enter a valid 10-digit Indian mobile number';
    } else if (!/^(?:\+91|91|0)?[6-9]\d{9}$/.test(rawPhone)) {
      newErrors.phone = 'Enter a valid 10-digit Indian mobile number';
    }

    // 4. Password (min 8 chars, uppercase, lowercase, number, special char)
    if (!password) {
      newErrors.password = 'Password must contain at least 8 characters, including uppercase, lowercase, number and special character';
    } else if (
      password.length < 8 ||
      !/[A-Z]/.test(password) ||
      !/[a-z]/.test(password) ||
      !/\d/.test(password) ||
      !/[!@#$%^&*(),.?":{}|<>\-_/\\+=~`[\]]/.test(password)
    ) {
      newErrors.password = 'Password must contain at least 8 characters, including uppercase, lowercase, number and special character';
    }

    // 5. Confirm Password
    if (!confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    } else if (password !== confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    // 6. Staff verification fields
    if (role !== 'APPLICANT') {
      if (!employeeId.trim()) {
        newErrors.employeeId = role === 'OFFICER' ? 'Employee ID is required' : 'Member/Employee ID is required';
      }
      if (!department.trim()) {
        newErrors.department = role === 'OFFICER' ? 'Department is required' : 'Department/Institution is required';
      }
      if (!designation.trim()) {
        newErrors.designation = role === 'OFFICER' ? 'Designation is required' : 'Designation/Committee role is required';
      }
      if (!jurisdiction.trim()) {
        newErrors.jurisdiction = 'Jurisdiction is required';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const mapBackendValidationErrors = (
    err: any,
    currentRole: RegisterRole
  ): { fieldErrors: Record<string, string>; summaryError: string } => {
    const fieldErrors: Record<string, string> = {};
    let summaryError = 'Registration failed. Please check the form and try again.';

    if (!err) {
      return { fieldErrors, summaryError: 'Registration failed. Please try again or contact the administrator.' };
    }

    // Network or server connection failure
    if (!err.response) {
      return {
        fieldErrors,
        summaryError: 'Registration failed. Please try again or contact the administrator.',
      };
    }

    const status = err.response.status;
    const data = err.response.data;

    // 1. Conflict: Duplicate email (409)
    const isDuplicate =
      status === 409 ||
      (typeof data?.error === 'string' &&
        (data.error.toLowerCase().includes('already exists') ||
          data.error.toLowerCase().includes('already registered')));

    if (isDuplicate) {
      fieldErrors.email = 'This email address is already registered';
      return { fieldErrors, summaryError: 'This email address is already registered' };
    }

    // 2. Admin self-registration prohibited (400)
    if (status === 400 && typeof data?.error === 'string' && data.error.toLowerCase().includes('prohibited')) {
      return { fieldErrors, summaryError: 'Admin registration is prohibited through this portal.' };
    }

    // 3. FastAPI / Pydantic validation errors (422)
    interface ValidationErrorItem {
      loc?: (string | number)[];
      msg?: string;
      type?: string;
    }

    const validationItems: ValidationErrorItem[] = Array.isArray(data?.details)
      ? data.details
      : Array.isArray(data?.detail)
      ? data.detail
      : [];

    if (validationItems.length > 0) {
      for (const item of validationItems) {
        const loc = item.loc || [];
        const rawField = loc.length > 0 ? String(loc[loc.length - 1]) : '';
        const rawMsg = (item.msg || '').replace(/^Value error,\s*/i, '').trim();

        let targetKey: string | null = null;
        let userMsg = rawMsg;

        switch (rawField) {
          case 'full_name':
            targetKey = 'fullName';
            userMsg = 'Full Name is required';
            if (rawMsg.toLowerCase().includes('between 2 and 100') || rawMsg.toLowerCase().includes('letters')) {
              userMsg = 'Full Name must be between 2 and 100 characters and contain only letters and spaces';
            }
            break;

          case 'email':
            targetKey = 'email';
            userMsg = rawMsg.toLowerCase().includes('already')
              ? 'This email address is already registered'
              : 'Enter a valid email address';
            break;

          case 'phone':
            targetKey = 'phone';
            userMsg = 'Enter a valid 10-digit Indian mobile number';
            break;

          case 'password':
            targetKey = 'password';
            userMsg = 'Password must contain at least 8 characters, including uppercase, lowercase, number and special character';
            break;

          case 'employee_id':
            targetKey = 'employeeId';
            userMsg = currentRole === 'OFFICER' ? 'Employee ID is required' : 'Member/Employee ID is required';
            break;

          case 'department':
            targetKey = 'department';
            userMsg = currentRole === 'OFFICER' ? 'Department is required' : 'Department/Institution is required';
            break;

          case 'designation':
            targetKey = 'designation';
            userMsg = currentRole === 'OFFICER' ? 'Designation is required' : 'Designation/Committee role is required';
            break;

          case 'jurisdiction':
            targetKey = 'jurisdiction';
            userMsg = 'Jurisdiction is required';
            break;

          default:
            break;
        }

        if (targetKey) {
          fieldErrors[targetKey] = userMsg;
        }
      }

      const firstMsg = Object.values(fieldErrors)[0];
      summaryError = firstMsg || 'Please correct the highlighted errors.';
      return { fieldErrors, summaryError };
    }

    // 4. Unexpected server error (500+)
    if (status >= 500) {
      return {
        fieldErrors,
        summaryError: 'Registration failed. Please try again or contact the administrator.',
      };
    }

    // 5. Generic safe fallback
    if (typeof data?.error === 'string' && data.error.length > 0 && data.error.length < 150) {
      summaryError = data.error;
    } else if (typeof data?.detail === 'string' && data.detail.length > 0 && data.detail.length < 150) {
      summaryError = data.detail;
    } else {
      summaryError = 'Registration failed. Please try again or contact the administrator.';
    }

    return { fieldErrors, summaryError };
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);
    try {
      if (role === 'APPLICANT') {
        await authService.registerApplicant({
          full_name: fullName.trim(),
          email: email.trim(),
          phone: phone.trim(),
          password,
        });
        setSubmittedSuccess('APPLICANT');
      } else {
        await authService.registerStaff({
          full_name: fullName.trim(),
          email: email.trim(),
          phone: phone.trim(),
          password,
          requested_role: role,
          employee_id: employeeId.trim(),
          department: department.trim(),
          designation: designation.trim(),
          jurisdiction: jurisdiction.trim(),
        });
        setSubmittedSuccess(role);
      }
    } catch (err: any) {
      console.error('Registration failed', err);
      const { fieldErrors, summaryError } = mapBackendValidationErrors(err, role);
      if (Object.keys(fieldErrors).length > 0) {
        setErrors((prev) => ({ ...prev, ...fieldErrors }));
      }
      setErrorMessage(summaryError);
    } finally {
      setIsLoading(false);
    }
  };

  if (submittedSuccess) {
    return (
      <div className="min-h-[85vh] flex flex-col justify-center items-center px-4 py-12 bg-slate-50">
        <div className="w-full max-w-lg bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden p-8 text-center animate-in fade-in duration-200">
          {submittedSuccess === 'APPLICANT' ? (
            <>
              <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center mx-auto mb-4">
                <CheckCircle2 className="w-9 h-9" />
              </div>
              <h2 className="text-xl font-bold text-slate-900">Applicant Account Activated</h2>
              <p className="text-sm text-slate-600 mt-2 mb-6">
                Your applicant registration has been created successfully. You may now log in to submit scholarship and fellowship applications.
              </p>
              <button
                onClick={() => navigate('/login')}
                className="w-full py-2.5 px-4 rounded-lg bg-teal-700 hover:bg-teal-800 text-white font-semibold text-sm transition-all shadow-md"
              >
                Proceed to Login
              </button>
            </>
          ) : (
            <>
              <div className="w-16 h-16 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center mx-auto mb-4">
                <ShieldCheck className="w-9 h-9" />
              </div>
              <h2 className="text-xl font-bold text-slate-900">
                {submittedSuccess === 'OFFICER' ? 'Officer Account Pending Approval' : 'Committee Account Pending Approval'}
              </h2>
              <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs text-left my-4 space-y-2">
                <p className="font-semibold flex items-center gap-1.5">
                  <BadgeAlert className="w-4 h-4 text-amber-700 shrink-0" />
                  Government Accreditation Review Required
                </p>
                <p>
                  Your registration request for role{' '}
                  <strong className="font-mono text-amber-950">{submittedSuccess}</strong> has been securely logged with the Ministry of Tribal Affairs.
                </p>
                <p className="text-slate-600">
                  Privileged portal access will become available immediately upon verification and approval by a System Administrator.
                </p>
              </div>
              <p className="text-xs text-slate-500 mb-6">
                You will be able to log in to access the {submittedSuccess === 'OFFICER' ? 'Verification Officer Console' : 'Committee Workbench'} once approved.
              </p>
              <button
                onClick={() => navigate('/login')}
                className="w-full py-2.5 px-4 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-semibold text-sm transition-all shadow-md"
              >
                Return to Login
              </button>
            </>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[85vh] flex flex-col justify-center items-center px-4 py-12 bg-slate-50">
      <div className="w-full max-w-xl">
        {/* Ministry Branding Header */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-teal-700 text-white font-bold text-xl shadow-lg mb-3">
            MoTA
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Ministry of Tribal Affairs
          </h1>
          <p className="text-xs text-slate-500 font-medium mt-1">
            Government of India | Portal Account Registration
          </p>
        </div>

        {/* Registration Card */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden">
          <div className="bg-slate-900 px-6 py-4 text-white flex items-center justify-between border-b border-slate-800">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-teal-400" />
              <h2 className="text-sm font-semibold tracking-wide">Create Portal Account</h2>
            </div>
            <span className="text-[11px] font-mono text-slate-400">Step 1 of 1</span>
          </div>

          <form onSubmit={handleSubmit} noValidate className="p-6 sm:p-8 space-y-6">
            {errorMessage && (
              <div className="p-3.5 rounded-lg bg-red-50 border border-red-200 flex items-start gap-2.5 text-xs text-red-700">
                <AlertCircle className="w-4 h-4 shrink-0 text-red-600 mt-0.5" />
                <span className="font-medium">{errorMessage}</span>
              </div>
            )}

            {/* Account Role Selector */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-2">
                I am registering as:
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <button
                  type="button"
                  onClick={() => handleRoleChange('APPLICANT')}
                  className={`p-3 rounded-xl border text-left flex flex-col justify-between transition-all ${
                    role === 'APPLICANT'
                      ? 'border-teal-600 bg-teal-50/50 ring-2 ring-teal-500/20 shadow-xs'
                      : 'border-slate-200 hover:border-slate-300 bg-white'
                  }`}
                >
                  <div className="flex items-center justify-between w-full mb-1">
                    <GraduationCap className={`w-5 h-5 ${role === 'APPLICANT' ? 'text-teal-700' : 'text-slate-400'}`} />
                    <span className={`w-2.5 h-2.5 rounded-full ${role === 'APPLICANT' ? 'bg-teal-600' : 'bg-slate-300'}`} />
                  </div>
                  <div>
                    <p className={`text-xs font-bold ${role === 'APPLICANT' ? 'text-teal-950' : 'text-slate-800'}`}>
                      Applicant
                    </p>
                    <p className="text-[10px] text-slate-500 mt-0.5">
                      Student / Scholar
                    </p>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => handleRoleChange('OFFICER')}
                  className={`p-3 rounded-xl border text-left flex flex-col justify-between transition-all ${
                    role === 'OFFICER'
                      ? 'border-teal-600 bg-teal-50/50 ring-2 ring-teal-500/20 shadow-xs'
                      : 'border-slate-200 hover:border-slate-300 bg-white'
                  }`}
                >
                  <div className="flex items-center justify-between w-full mb-1">
                    <ClipboardCheck className={`w-5 h-5 ${role === 'OFFICER' ? 'text-teal-700' : 'text-slate-400'}`} />
                    <span className={`w-2.5 h-2.5 rounded-full ${role === 'OFFICER' ? 'bg-teal-600' : 'bg-slate-300'}`} />
                  </div>
                  <div>
                    <p className={`text-xs font-bold ${role === 'OFFICER' ? 'text-teal-950' : 'text-slate-800'}`}>
                      Desk Officer
                    </p>
                    <p className="text-[10px] text-slate-500 mt-0.5">
                      Verification Staff
                    </p>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => handleRoleChange('COMMITTEE')}
                  className={`p-3 rounded-xl border text-left flex flex-col justify-between transition-all ${
                    role === 'COMMITTEE'
                      ? 'border-teal-600 bg-teal-50/50 ring-2 ring-teal-500/20 shadow-xs'
                      : 'border-slate-200 hover:border-slate-300 bg-white'
                  }`}
                >
                  <div className="flex items-center justify-between w-full mb-1">
                    <Award className={`w-5 h-5 ${role === 'COMMITTEE' ? 'text-teal-700' : 'text-slate-400'}`} />
                    <span className={`w-2.5 h-2.5 rounded-full ${role === 'COMMITTEE' ? 'bg-teal-600' : 'bg-slate-300'}`} />
                  </div>
                  <div>
                    <p className={`text-xs font-bold ${role === 'COMMITTEE' ? 'text-teal-950' : 'text-slate-800'}`}>
                      Committee
                    </p>
                    <p className="text-[10px] text-slate-500 mt-0.5">
                      Selection Board
                    </p>
                  </div>
                </button>
              </div>
            </div>

            {/* Approval Requirement Notice for Staff */}
            {role !== 'APPLICANT' && (
              <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900 flex items-start gap-2.5">
                <BadgeAlert className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
                <p>
                  <strong>Admin Verification Required:</strong> {role === 'OFFICER' ? 'Desk Officer' : 'Committee Member'} accounts require administrative verification. Your registration will be placed in <em>Pending Approval</em> status until reviewed by the portal administrator.
                </p>
              </div>
            )}

            {/* Personal Details Section */}
            <div className="space-y-4">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider border-b border-slate-100 pb-1.5">
                1. Account Credentials
              </h3>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Full Name <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <User className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => {
                      setFullName(e.target.value);
                      if (errors.fullName) setErrors((prev) => ({ ...prev, fullName: '' }));
                    }}
                    placeholder="Enter your complete legal name"
                    className={`w-full pl-9 pr-3 py-2 text-sm bg-slate-50 border ${
                      errors.fullName ? 'border-red-500 ring-1 ring-red-500' : 'border-slate-300 focus:ring-2 focus:ring-teal-600 focus:border-teal-600'
                    } rounded-lg outline-hidden transition`}
                  />
                </div>
                {errors.fullName && (
                  <p className="mt-1 text-xs text-red-600 flex items-center gap-1 animate-in fade-in duration-100">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                    <span>{errors.fullName}</span>
                  </p>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    {role === 'APPLICANT' ? 'Email Address' : 'Official Email Address'}{' '}
                    <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                      <Mail className="w-4 h-4" />
                    </div>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => {
                        setEmail(e.target.value);
                        if (errors.email) setErrors((prev) => ({ ...prev, email: '' }));
                      }}
                      placeholder={role === 'APPLICANT' ? 'name@example.com' : 'officer@mota.gov.in'}
                      className={`w-full pl-9 pr-3 py-2 text-sm bg-slate-50 border ${
                        errors.email ? 'border-red-500 ring-1 ring-red-500' : 'border-slate-300 focus:ring-2 focus:ring-teal-600 focus:border-teal-600'
                      } rounded-lg outline-hidden transition`}
                    />
                  </div>
                  {errors.email && (
                    <p className="mt-1 text-xs text-red-600 flex items-center gap-1 animate-in fade-in duration-100">
                      <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                      <span>{errors.email}</span>
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Mobile Number <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                      <Phone className="w-4 h-4" />
                    </div>
                    <input
                      type="tel"
                      value={phone}
                      onChange={(e) => {
                        setPhone(e.target.value);
                        if (errors.phone) setErrors((prev) => ({ ...prev, phone: '' }));
                      }}
                      placeholder="+91 9876543210"
                      className={`w-full pl-9 pr-3 py-2 text-sm bg-slate-50 border ${
                        errors.phone ? 'border-red-500 ring-1 ring-red-500' : 'border-slate-300 focus:ring-2 focus:ring-teal-600 focus:border-teal-600'
                      } rounded-lg outline-hidden transition`}
                    />
                  </div>
                  {errors.phone && (
                    <p className="mt-1 text-xs text-red-600 flex items-center gap-1 animate-in fade-in duration-100">
                      <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                      <span>{errors.phone}</span>
                    </p>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Password <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                      <Lock className="w-4 h-4" />
                    </div>
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => {
                        setPassword(e.target.value);
                        if (errors.password) setErrors((prev) => ({ ...prev, password: '' }));
                      }}
                      placeholder="Min 8 chars: A-Z, a-z, 0-9, special"
                      className={`w-full pl-9 pr-11 py-2 text-sm bg-slate-50 border ${
                        errors.password ? 'border-red-500 ring-1 ring-red-500' : 'border-slate-300 focus:ring-2 focus:ring-teal-600 focus:border-teal-600'
                      } rounded-lg outline-hidden transition`}
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
                  {errors.password && (
                    <p className="mt-1 text-xs text-red-600 flex items-center gap-1 animate-in fade-in duration-100">
                      <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                      <span>{errors.password}</span>
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Confirm Password <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                      <Lock className="w-4 h-4" />
                    </div>
                    <input
                      type={showConfirmPassword ? 'text' : 'password'}
                      value={confirmPassword}
                      onChange={(e) => {
                        setConfirmPassword(e.target.value);
                        if (errors.confirmPassword) setErrors((prev) => ({ ...prev, confirmPassword: '' }));
                      }}
                      placeholder="Re-enter password"
                      className={`w-full pl-9 pr-11 py-2 text-sm bg-slate-50 border ${
                        errors.confirmPassword ? 'border-red-500 ring-1 ring-red-500' : 'border-slate-300 focus:ring-2 focus:ring-teal-600 focus:border-teal-600'
                      } rounded-lg outline-hidden transition`}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-500 hover:text-slate-700 cursor-pointer z-10 focus:outline-hidden"
                      aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                      title={showConfirmPassword ? 'Hide password' : 'Show password'}
                    >
                      {showConfirmPassword ? <EyeOff className="w-5 h-5 text-slate-500 hover:text-slate-700" /> : <Eye className="w-5 h-5 text-slate-500 hover:text-slate-700" />}
                    </button>
                  </div>
                  {errors.confirmPassword && (
                    <p className="mt-1 text-xs text-red-600 flex items-center gap-1 animate-in fade-in duration-100">
                      <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                      <span>{errors.confirmPassword}</span>
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Staff Official Verification Section */}
            {role !== 'APPLICANT' && (
              <div className="space-y-4 pt-2">
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider border-b border-slate-100 pb-1.5 flex items-center justify-between">
                  <span>2. Official Institutional Credentials</span>
                  <span className="text-[10px] font-medium text-amber-700 bg-amber-100 px-2 py-0.5 rounded">
                    Admin Verification
                  </span>
                </h3>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      {role === 'OFFICER' ? 'Employee ID' : 'Member / Employee ID'}{' '}
                      <span className="text-red-500">*</span>
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                        <User className="w-4 h-4" />
                      </div>
                      <input
                        type="text"
                        value={employeeId}
                        onChange={(e) => {
                          setEmployeeId(e.target.value);
                          if (errors.employeeId) setErrors((prev) => ({ ...prev, employeeId: '' }));
                        }}
                        placeholder={role === 'OFFICER' ? 'e.g. MOTA-VO-8821' : 'e.g. COMM-EXP-772'}
                        className={`w-full pl-9 pr-3 py-2 text-sm bg-slate-50 border ${
                          errors.employeeId ? 'border-red-500 ring-1 ring-red-500' : 'border-slate-300 focus:ring-2 focus:ring-teal-600 focus:border-teal-600'
                        } rounded-lg outline-hidden transition font-mono text-xs`}
                      />
                    </div>
                    {errors.employeeId && (
                      <p className="mt-1 text-xs text-red-600 flex items-center gap-1 animate-in fade-in duration-100">
                        <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                        <span>{errors.employeeId}</span>
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      {role === 'OFFICER' ? 'Department' : 'Department / Institution'}{' '}
                      <span className="text-red-500">*</span>
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                        <Building className="w-4 h-4" />
                      </div>
                      <input
                        type="text"
                        value={department}
                        onChange={(e) => {
                          setDepartment(e.target.value);
                          if (errors.department) setErrors((prev) => ({ ...prev, department: '' }));
                        }}
                        placeholder={role === 'OFFICER' ? 'e.g. Tribal Welfare Directorate' : 'e.g. Anthropology Department'}
                        className={`w-full pl-9 pr-3 py-2 text-sm bg-slate-50 border ${
                          errors.department ? 'border-red-500 ring-1 ring-red-500' : 'border-slate-300 focus:ring-2 focus:ring-teal-600 focus:border-teal-600'
                        } rounded-lg outline-hidden transition`}
                      />
                    </div>
                    {errors.department && (
                      <p className="mt-1 text-xs text-red-600 flex items-center gap-1 animate-in fade-in duration-100">
                        <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                        <span>{errors.department}</span>
                      </p>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      {role === 'OFFICER' ? 'Designation' : 'Designation / Committee Role'}{' '}
                      <span className="text-red-500">*</span>
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                        <Briefcase className="w-4 h-4" />
                      </div>
                      <input
                        type="text"
                        value={designation}
                        onChange={(e) => {
                          setDesignation(e.target.value);
                          if (errors.designation) setErrors((prev) => ({ ...prev, designation: '' }));
                        }}
                        placeholder={role === 'OFFICER' ? 'e.g. Assistant Scrutiny Officer' : 'e.g. Subject Matter Expert'}
                        className={`w-full pl-9 pr-3 py-2 text-sm bg-slate-50 border ${
                          errors.designation ? 'border-red-500 ring-1 ring-red-500' : 'border-slate-300 focus:ring-2 focus:ring-teal-600 focus:border-teal-600'
                        } rounded-lg outline-hidden transition`}
                      />
                    </div>
                    {errors.designation && (
                      <p className="mt-1 text-xs text-red-600 flex items-center gap-1 animate-in fade-in duration-100">
                        <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                        <span>{errors.designation}</span>
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Jurisdiction <span className="text-red-500">*</span>
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                        <MapPin className="w-4 h-4" />
                      </div>
                      <input
                        type="text"
                        value={jurisdiction}
                        onChange={(e) => {
                          setJurisdiction(e.target.value);
                          if (errors.jurisdiction) setErrors((prev) => ({ ...prev, jurisdiction: '' }));
                        }}
                        placeholder={role === 'OFFICER' ? 'e.g. Jharkhand / Ranchi' : 'e.g. Anthropology Board'}
                        className={`w-full pl-9 pr-3 py-2 text-sm bg-slate-50 border ${
                          errors.jurisdiction ? 'border-red-500 ring-1 ring-red-500' : 'border-slate-300 focus:ring-2 focus:ring-teal-600 focus:border-teal-600'
                        } rounded-lg outline-hidden transition`}
                      />
                    </div>
                    {errors.jurisdiction && (
                      <p className="mt-1 text-xs text-red-600 flex items-center gap-1 animate-in fade-in duration-100">
                        <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                        <span>{errors.jurisdiction}</span>
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-4 py-2.5 px-4 rounded-lg bg-teal-700 hover:bg-teal-800 focus:ring-4 focus:ring-teal-200 text-white font-semibold text-sm transition-all shadow-md flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Submitting Registration...</span>
                </>
              ) : role === 'APPLICANT' ? (
                <span>Register Applicant Account</span>
              ) : (
                <span>Submit Staff Registration Request</span>
              )}
            </button>

            <div className="text-center pt-2 border-t border-slate-100">
              <p className="text-xs text-slate-500">
                Already registered?{' '}
                <Link to="/login" className="font-semibold text-teal-700 hover:underline">
                  Sign in here
                </Link>
              </p>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Register;
