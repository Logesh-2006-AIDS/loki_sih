import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Clock,
  Search,
  RefreshCw,
  UserCheck,
  UserX,
  AlertCircle,
  MapPin,
  Loader2,
  Award,
  ClipboardCheck,
} from 'lucide-react';
import { StaffRequestResponse, StaffRequestStats, StaffRequestStatus } from '../../types/userApproval';
import { userApprovalService } from '../../services/userApprovalService';

export const AdminUserApprovals: React.FC = () => {
  const [requests, setRequests] = useState<StaffRequestResponse[]>([]);
  const [stats, setStats] = useState<StaffRequestStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<'ALL' | StaffRequestStatus>('PENDING');
  const [roleFilter, setRoleFilter] = useState<'ALL' | 'OFFICER' | 'COMMITTEE'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  // Selected request for modal review
  const [selectedRequest, setSelectedRequest] = useState<StaffRequestResponse | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [rejectError, setRejectError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [statsData, listData] = await Promise.all([
        userApprovalService.getStats(),
        userApprovalService.listRequests(
          statusFilter === 'ALL' ? undefined : statusFilter,
          roleFilter === 'ALL' ? undefined : roleFilter,
          searchQuery
        ),
      ]);
      setStats(statsData);
      setRequests(listData);
    } catch (err: any) {
      console.error('Failed to load user approvals', err);
      setActionMessage({ type: 'error', text: 'Failed to load staff approval requests.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [statusFilter, roleFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchData();
  };

  const handleApprove = async (id: string) => {
    try {
      setActionLoading(true);
      const updated = await userApprovalService.approveRequest(id);
      setActionMessage({ type: 'success', text: `Approved staff account for ${updated.user_name} (${updated.requested_role}).` });
      setSelectedRequest(null);
      await fetchData();
    } catch (err: any) {
      console.error('Failed to approve request', err);
      setActionMessage({ type: 'error', text: err.response?.data?.error || 'Failed to approve request.' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (id: string) => {
    setRejectError(null);
    const trimmedReason = rejectReason.trim();

    if (!trimmedReason) {
      setRejectError('Please provide a reason for rejecting this registration.');
      return;
    }
    if (trimmedReason.length < 10) {
      setRejectError('Rejection reason must be at least 10 characters.');
      return;
    }
    if (trimmedReason.length > 1000) {
      setRejectError('Rejection reason cannot exceed 1000 characters.');
      return;
    }
    if (/<[^>]+>|script/i.test(trimmedReason)) {
      setRejectError('Rejection reason cannot contain HTML or script content.');
      return;
    }

    try {
      setActionLoading(true);
      const updated = await userApprovalService.rejectRequest(id, trimmedReason);
      setActionMessage({ type: 'success', text: `Rejected staff account request for ${updated.user_name}.` });
      setSelectedRequest(null);
      setShowRejectForm(false);
      setRejectReason('');
      setRejectError(null);
      await fetchData();
    } catch (err: any) {
      console.error('Failed to reject request', err);
      const backendErr = err.response?.data?.error || err.response?.data?.details?.[0]?.msg || 'Failed to reject request.';
      setRejectError(backendErr);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="bg-slate-900 text-white p-6 sm:p-8 rounded-2xl shadow-sm border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 uppercase tracking-wider">
                Staff Accreditation
              </span>
              <span className="text-xs text-slate-400">MoTA Administration</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold tracking-tight mt-1">
              Staff Registration & Account Approvals
            </h1>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl">
              Review and authorize Desk Verification Officer and Selection Committee registration requests. Privileged access is strictly withheld until administrative approval.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={fetchData}
              disabled={loading}
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition shadow-xs"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* Action Status Banner */}
        {actionMessage && (
          <div
            className={`p-4 rounded-xl border flex items-center justify-between gap-3 text-xs ${
              actionMessage.type === 'success'
                ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                : 'bg-red-50 border-red-200 text-red-900'
            }`}
          >
            <div className="flex items-center gap-2">
              {actionMessage.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
              )}
              <span className="font-semibold">{actionMessage.text}</span>
            </div>
            <button
              onClick={() => setActionMessage(null)}
              className="text-slate-400 hover:text-slate-600 font-bold"
            >
              ✕
            </button>
          </div>
        )}

        {/* Live Metrics Grid */}
        {stats && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
              <div>
                <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                  Pending Approvals
                </p>
                <p className="text-2xl font-extrabold text-amber-600 mt-1">
                  {stats.pending_count}
                </p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-amber-50 text-amber-700 flex items-center justify-center">
                <Clock className="w-5 h-5" />
              </div>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
              <div>
                <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                  Active Desk Officers
                </p>
                <p className="text-2xl font-extrabold text-teal-700 mt-1">
                  {stats.active_officers}
                </p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-teal-50 text-teal-700 flex items-center justify-center">
                <ClipboardCheck className="w-5 h-5" />
              </div>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
              <div>
                <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                  Active Committee
                </p>
                <p className="text-2xl font-extrabold text-indigo-700 mt-1">
                  {stats.active_committee}
                </p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-700 flex items-center justify-center">
                <Award className="w-5 h-5" />
              </div>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
              <div>
                <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                  Rejected Requests
                </p>
                <p className="text-2xl font-extrabold text-slate-600 mt-1">
                  {stats.rejected_count}
                </p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-slate-100 text-slate-600 flex items-center justify-center">
                <UserX className="w-5 h-5" />
              </div>
            </div>
          </div>
        )}

        {/* Filter Bar */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col md:flex-row items-center justify-between gap-4">
          {/* Status Tabs */}
          <div className="flex items-center gap-1.5 overflow-x-auto w-full md:w-auto">
            {(['PENDING', 'APPROVED', 'REJECTED', 'ALL'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setStatusFilter(tab)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
                  statusFilter === tab
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {tab === 'PENDING' ? 'Pending Review' : tab === 'ALL' ? 'All Requests' : tab}
              </button>
            ))}
          </div>

          {/* Search & Role Filter */}
          <div className="flex items-center gap-3 w-full md:w-auto justify-end">
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value as any)}
              className="text-xs bg-slate-50 border border-slate-300 rounded-lg px-2.5 py-1.5 text-slate-700 focus:ring-2 focus:ring-teal-600 outline-hidden font-medium"
            >
              <option value="ALL">All Roles</option>
              <option value="OFFICER">Desk Officer</option>
              <option value="COMMITTEE">Committee Member</option>
            </select>

            <form onSubmit={handleSearchSubmit} className="relative flex-1 sm:w-60">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search staff..."
                className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-600 outline-hidden"
              />
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-slate-400" />
            </form>
          </div>
        </div>

        {/* Requests Table */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
          {loading ? (
            <div className="p-12 text-center text-slate-400">
              <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-teal-600" />
              <p className="text-xs">Loading registration requests...</p>
            </div>
          ) : requests.length === 0 ? (
            <div className="p-12 text-center text-slate-500">
              <ShieldCheck className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="text-sm font-semibold text-slate-700">No requests found</p>
              <p className="text-xs text-slate-400 mt-1">
                There are no staff registration requests matching the selected filters.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="px-6 py-3.5">Candidate Details</th>
                    <th className="px-4 py-3.5">Requested Role</th>
                    <th className="px-4 py-3.5">Department & Jurisdiction</th>
                    <th className="px-4 py-3.5">Employee ID</th>
                    <th className="px-4 py-3.5">Submitted</th>
                    <th className="px-4 py-3.5">Status</th>
                    <th className="px-6 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {requests.map((r) => (
                    <tr key={r.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-6 py-4">
                        <div className="font-bold text-slate-900">{r.user_name}</div>
                        <div className="text-[11px] text-slate-500 font-mono">{r.user_email}</div>
                        {r.user_phone && (
                          <div className="text-[10px] text-slate-400">{r.user_phone}</div>
                        )}
                      </td>
                      <td className="px-4 py-4">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                            r.requested_role === 'OFFICER'
                              ? 'bg-teal-100 text-teal-800 border border-teal-200'
                              : 'bg-indigo-100 text-indigo-800 border border-indigo-200'
                          }`}
                        >
                          {r.requested_role === 'OFFICER' ? (
                            <ClipboardCheck className="w-3 h-3" />
                          ) : (
                            <Award className="w-3 h-3" />
                          )}
                          {r.requested_role}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <div className="font-medium text-slate-800">{r.department}</div>
                        <div className="text-[11px] text-slate-500">{r.designation}</div>
                        <div className="text-[10px] text-slate-400 flex items-center gap-1 mt-0.5">
                          <MapPin className="w-2.5 h-2.5" />
                          {r.jurisdiction}
                        </div>
                      </td>
                      <td className="px-4 py-4 font-mono text-[11px] text-slate-700">
                        {r.employee_id}
                      </td>
                      <td className="px-4 py-4 text-slate-500 text-[11px] whitespace-nowrap">
                        {new Date(r.submitted_at).toLocaleDateString('en-IN', {
                          day: 'numeric',
                          month: 'short',
                          year: 'numeric',
                        })}
                      </td>
                      <td className="px-4 py-4">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                            r.status === 'PENDING'
                              ? 'bg-amber-100 text-amber-800 border border-amber-200'
                              : r.status === 'APPROVED'
                              ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                              : 'bg-red-100 text-red-800 border border-red-200'
                          }`}
                        >
                          {r.status === 'PENDING' && <Clock className="w-2.5 h-2.5" />}
                          {r.status === 'APPROVED' && <CheckCircle2 className="w-2.5 h-2.5" />}
                          {r.status === 'REJECTED' && <XCircle className="w-2.5 h-2.5" />}
                          {r.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => {
                            setSelectedRequest(r);
                            setShowRejectForm(false);
                            setRejectReason('');
                          }}
                          className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-[11px] transition shadow-2xs"
                        >
                          Review
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Review Modal */}
        {selectedRequest && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full overflow-hidden animate-in fade-in zoom-in-95 duration-150">
              <div className="bg-slate-900 px-6 py-4 text-white flex items-center justify-between border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-teal-400" />
                  <h3 className="text-sm font-bold">Staff Accreditation Review</h3>
                </div>
                <button
                  onClick={() => {
                    setSelectedRequest(null);
                    setShowRejectForm(false);
                    setRejectReason('');
                    setRejectError(null);
                  }}
                  className="text-slate-400 hover:text-white font-bold text-sm"
                >
                  ✕
                </button>
              </div>

              <div className="p-6 space-y-4 text-xs">
                {/* Profile Header */}
                <div className="flex items-start justify-between border-b border-slate-100 pb-3">
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">{selectedRequest.user_name}</h4>
                    <p className="text-slate-500 font-mono text-[11px]">{selectedRequest.user_email}</p>
                    {selectedRequest.user_phone && (
                      <p className="text-slate-400 text-[10px]">{selectedRequest.user_phone}</p>
                    )}
                  </div>
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                      selectedRequest.status === 'PENDING'
                        ? 'bg-amber-100 text-amber-800'
                        : selectedRequest.status === 'APPROVED'
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-red-100 text-red-800'
                    }`}
                  >
                    {selectedRequest.status}
                  </span>
                </div>

                {/* Details Grid */}
                <div className="grid grid-cols-2 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200">
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Requested Role</span>
                    <p className="font-bold text-slate-800 mt-0.5">{selectedRequest.requested_role}</p>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Official Employee ID</span>
                    <p className="font-mono font-bold text-slate-800 mt-0.5">{selectedRequest.employee_id}</p>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Department / Org</span>
                    <p className="font-medium text-slate-800 mt-0.5">{selectedRequest.department}</p>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Designation</span>
                    <p className="font-medium text-slate-800 mt-0.5">{selectedRequest.designation}</p>
                  </div>
                  <div className="col-span-2">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Jurisdiction / Jurisdiction</span>
                    <p className="font-medium text-slate-800 mt-0.5">{selectedRequest.jurisdiction}</p>
                  </div>
                </div>

                {/* Review Audit History if already processed */}
                {selectedRequest.reviewed_at && (
                  <div className="p-3 bg-slate-100 rounded-lg text-[11px] text-slate-600 space-y-1">
                    <p>
                      <strong>Reviewed by:</strong> {selectedRequest.reviewer_name || 'System Administrator'}
                    </p>
                    <p>
                      <strong>Reviewed on:</strong>{' '}
                      {new Date(selectedRequest.reviewed_at).toLocaleString('en-IN')}
                    </p>
                    {selectedRequest.rejection_reason && (
                      <p className="text-red-700">
                        <strong>Rejection Rationale:</strong> {selectedRequest.rejection_reason}
                      </p>
                    )}
                  </div>
                )}

                {/* Rejection Form Input */}
                {showRejectForm && (
                  <div className="p-4 rounded-xl bg-red-50 border border-red-200 space-y-3 animate-in fade-in duration-100">
                    <div>
                      <label htmlFor="rejection-reason" className="block text-xs font-bold text-red-900 mb-1">
                        Rejection Reason *
                      </label>
                      <textarea
                        id="rejection-reason"
                        rows={3}
                        value={rejectReason}
                        onChange={(e) => {
                          setRejectReason(e.target.value);
                          if (rejectError) setRejectError(null);
                        }}
                        placeholder="e.g. Official institutional identification details could not be verified."
                        className="w-full text-xs p-2.5 rounded-lg border border-red-300 bg-white focus:ring-2 focus:ring-red-500 outline-hidden"
                      />
                      {rejectError && (
                        <p className="mt-1 text-xs font-semibold text-red-600 flex items-center gap-1">
                          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                          <span>{rejectError}</span>
                        </p>
                      )}
                    </div>
                    <div className="flex items-center justify-end gap-2 pt-1">
                      <button
                        type="button"
                        onClick={() => {
                          setShowRejectForm(false);
                          setRejectReason('');
                          setRejectError(null);
                        }}
                        className="px-3.5 py-1.5 text-xs text-slate-700 font-semibold hover:bg-slate-200 rounded-lg transition"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        onClick={() => handleReject(selectedRequest.id)}
                        disabled={actionLoading}
                        className="px-4 py-1.5 text-xs bg-red-700 hover:bg-red-800 text-white font-bold rounded-lg shadow-xs transition disabled:opacity-50"
                      >
                        {actionLoading ? 'Rejecting...' : 'Reject Registration'}
                      </button>
                    </div>
                  </div>
                )}

                {/* Action Buttons for Pending Request */}
                {selectedRequest.status === 'PENDING' && !showRejectForm && (
                  <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                    <button
                      type="button"
                      onClick={() => {
                        setShowRejectForm(true);
                        setRejectError(null);
                      }}
                      className="px-4 py-2 rounded-lg bg-red-50 hover:bg-red-100 text-red-700 font-bold text-xs border border-red-200 transition"
                    >
                      Reject Request
                    </button>
                    <button
                      type="button"
                      onClick={() => handleApprove(selectedRequest.id)}
                      disabled={actionLoading}
                      className="px-5 py-2 rounded-lg bg-teal-700 hover:bg-teal-800 text-white font-bold text-xs transition shadow-sm flex items-center gap-1.5"
                    >
                      {actionLoading ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>Approving...</span>
                        </>
                      ) : (
                        <>
                          <UserCheck className="w-3.5 h-3.5" />
                          <span>Approve & Activate Staff</span>
                        </>
                      )}
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminUserApprovals;
