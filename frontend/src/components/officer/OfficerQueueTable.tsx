import React from 'react';
import { Link } from 'react-router-dom';
import { FileCheck, AlertTriangle, ArrowRight, ShieldCheck, MapPin, Calendar } from 'lucide-react';
import { OfficerQueueItem } from '../../types/officer';

interface OfficerQueueTableProps {
  items: OfficerQueueItem[];
  isLoading: boolean;
}

export const OfficerQueueTable: React.FC<OfficerQueueTableProps> = ({ items, isLoading }) => {
  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-12 text-center">
        <div className="inline-block animate-spin w-8 h-8 border-4 border-teal-600 border-t-transparent rounded-full mb-3" />
        <p className="text-sm font-medium text-slate-600">Loading assigned scrutiny queue...</p>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-12 text-center">
        <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 mx-auto flex items-center justify-center mb-3">
          <FileCheck className="w-6 h-6" />
        </div>
        <h3 className="text-base font-semibold text-slate-800">No applications in this queue</h3>
        <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
          There are currently no applications matching your filter criteria within your assigned jurisdiction.
        </p>
      </div>
    );
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'UNDER_MANUAL_REVIEW':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
            Pending Scrutiny
          </span>
        );
      case 'VERIFIED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
            Scrutiny Complete
          </span>
        );
      case 'DEFICIENT':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-orange-100 text-orange-800 border border-orange-200">
            Deficiency Flagged
          </span>
        );
      case 'REJECTED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-200">
            Rejected
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">
            {status}
          </span>
        );
    }
  };

  const getAiBadge = (item: OfficerQueueItem) => {
    if (item.ai_flagged_count > 0) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
          <AlertTriangle className="w-3 h-3 text-amber-600" />
          {item.ai_flagged_count} Flag{item.ai_flagged_count > 1 ? 's' : ''}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
        <ShieldCheck className="w-3 h-3 text-emerald-600" />
        AI Verified
      </span>
    );
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-slate-600">
          <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500 border-b border-slate-200">
            <tr>
              <th className="py-3.5 px-4 font-semibold">Reference / Scheme</th>
              <th className="py-3.5 px-4 font-semibold">Applicant Name</th>
              <th className="py-3.5 px-4 font-semibold">State</th>
              <th className="py-3.5 px-4 font-semibold">Submitted Date</th>
              <th className="py-3.5 px-4 font-semibold">AI Verification</th>
              <th className="py-3.5 px-4 font-semibold">Application Status</th>
              <th className="py-3.5 px-4 font-semibold text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {items.map((item) => (
              <tr key={item.id} className="hover:bg-slate-50/80 transition-colors">
                <td className="py-3 px-4">
                  <div className="font-mono font-semibold text-slate-900 text-xs sm:text-sm">
                    {item.reference_id}
                  </div>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-teal-100 text-teal-800">
                      {item.scheme_code}
                    </span>
                    <span className="text-xs text-slate-500 truncate max-w-[180px]" title={item.scheme_name}>
                      {item.scheme_name}
                    </span>
                  </div>
                </td>
                <td className="py-3 px-4 font-medium text-slate-800">
                  {item.applicant_name}
                </td>
                <td className="py-3 px-4">
                  <div className="flex items-center gap-1 text-slate-600 text-xs">
                    <MapPin className="w-3 h-3 text-slate-400" />
                    {item.state || 'Not specified'}
                  </div>
                </td>
                <td className="py-3 px-4 text-xs text-slate-500">
                  <div className="flex items-center gap-1">
                    <Calendar className="w-3 h-3 text-slate-400" />
                    {item.submitted_at
                      ? new Date(item.submitted_at).toLocaleDateString('en-IN', {
                          day: 'numeric',
                          month: 'short',
                          year: 'numeric',
                        })
                      : 'N/A'}
                  </div>
                </td>
                <td className="py-3 px-4">
                  {getAiBadge(item)}
                </td>
                <td className="py-3 px-4">
                  {getStatusBadge(item.status)}
                </td>
                <td className="py-3 px-4 text-right">
                  <Link
                    to={`/officer/applications/${item.id}/scrutiny`}
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-teal-700 hover:bg-teal-800 text-white transition-colors shadow-sm"
                  >
                    Scrutinize
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
