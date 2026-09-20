import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, MapPin, Calendar, BookOpen, ShieldCheck, UserCheck } from 'lucide-react';
import { OfficerApplicationScrutinyResponse } from '../../types/officer';

interface ScrutinyHeaderProps {
  data: OfficerApplicationScrutinyResponse;
}

export const ScrutinyHeader: React.FC<ScrutinyHeaderProps> = ({ data }) => {
  const applicantState =
    (data.form_data?.personal?.state) || (data.form_data?.state) || 'Not specified';

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'UNDER_MANUAL_REVIEW':
        return (
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-300">
            Pending Officer Scrutiny
          </span>
        );
      case 'VERIFIED':
        return (
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
            Scrutiny Complete (Verified)
          </span>
        );
      case 'DEFICIENT':
        return (
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-orange-100 text-orange-800 border border-orange-300">
            Flagged Deficient (Phase 5 Handoff)
          </span>
        );
      case 'REJECTED':
        return (
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-300">
            Disqualified / Rejected
          </span>
        );
      default:
        return (
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="bg-white border-b border-slate-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        {/* Navigation Breadcrumb */}
        <div className="flex items-center justify-between mb-3">
          <Link
            to="/officer/dashboard"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-teal-700 hover:text-teal-900 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Assigned Queue
          </Link>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
              <ShieldCheck className="w-3 h-3 text-teal-600" />
              Assigned Desk Jurisdiction Confirmed
            </span>
          </div>
        </div>

        {/* Title and Metadata Bar */}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl sm:text-2xl font-bold font-mono tracking-tight text-slate-900">
                {data.reference_id}
              </h1>
              {getStatusBadge(data.status)}
            </div>
            <p className="text-sm font-medium text-slate-600 mt-1">
              Applicant: <span className="font-semibold text-slate-900">{data.applicant_name}</span>
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs text-slate-600 bg-slate-50 px-3.5 py-2 rounded-lg border border-slate-200">
            <div className="flex items-center gap-1.5">
              <BookOpen className="w-3.5 h-3.5 text-teal-600" />
              <span className="font-semibold text-slate-800">{data.scheme_code}</span>
              <span className="text-slate-400">|</span>
              <span>v{data.scheme_version || '1.0'}</span>
            </div>
            <span className="text-slate-300">•</span>
            <div className="flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-slate-400" />
              <span>State: <strong className="text-slate-800">{applicantState}</strong></span>
            </div>
            <span className="text-slate-300">•</span>
            <div className="flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-slate-400" />
              <span>
                Submitted:{' '}
                {data.submitted_at
                  ? new Date(data.submitted_at).toLocaleDateString('en-IN', {
                      day: 'numeric',
                      month: 'short',
                      year: 'numeric',
                    })
                  : 'Draft'}
              </span>
            </div>
          </div>
        </div>

        {data.scrutiny_officer_name && (
          <div className="mt-3 text-xs text-slate-500 flex items-center gap-1">
            <UserCheck className="w-3.5 h-3.5 text-teal-600" />
            <span>
              Scrutinized by <strong>{data.scrutiny_officer_name}</strong> on{' '}
              {data.scrutiny_completed_at ? new Date(data.scrutiny_completed_at).toLocaleString('en-IN') : ''}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
