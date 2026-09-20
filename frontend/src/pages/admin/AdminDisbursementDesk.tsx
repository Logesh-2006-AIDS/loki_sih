import React, { useState, useEffect } from 'react';
import {
  CreditCard,
  CheckCircle2,
  ShieldCheck,
  RefreshCw,
  AlertTriangle,
  Send,
  RotateCcw,
} from 'lucide-react';
import fellowshipService from '../../services/fellowshipService';
import { DisbursementInstallment } from '../../types/fellowship';

export const AdminDisbursementDesk: React.FC = () => {
  const [installments, setInstallments] = useState<DisbursementInstallment[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null);

  // Simulation controls
  const [simulatedAccountSuffix, setSimulatedAccountSuffix] = useState<'NORMAL' | '9999' | '8888'>('NORMAL');

  useEffect(() => {
    loadDisbursements();
  }, [filterStatus]);

  const loadDisbursements = async () => {
    setLoading(true);
    setError(null);
    try {
      const statusParam = filterStatus === 'ALL' ? undefined : filterStatus;
      const data = await fellowshipService.listAllDisbursements(statusParam);
      setInstallments(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load disbursements.');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id: string) => {
    setProcessingId(id);
    setError(null);
    try {
      await fellowshipService.approveDisbursement(id, 'Approved by Administrative Disbursement Desk');
      setSuccessMessage('Installment approved for payment. Financial amounts are now locked.');
      await loadDisbursements();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Approval failed.');
    } finally {
      setProcessingId(null);
    }
  };

  const handleExecute = async (id: string) => {
    setProcessingId(id);
    setError(null);
    try {
      const override = simulatedAccountSuffix === 'NORMAL' ? undefined : `12345678${simulatedAccountSuffix}`;
      const res = await fellowshipService.executeDisbursement(id, override);
      if (res.status === 'SUCCESS') {
        setSuccessMessage(`Payment dispatched successfully! PFMS Ref: ${res.pfms_reference_id}, Bank UTR: ${res.bank_reference_utr}`);
      } else {
        setError(`Disbursement failed at PFMS gateway: ${res.failure_reason}`);
      }
      await loadDisbursements();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Dispatch execution failed.');
    } finally {
      setProcessingId(null);
    }
  };

  const handleRetry = async (id: string) => {
    setProcessingId(id);
    setError(null);
    try {
      const override = simulatedAccountSuffix === 'NORMAL' ? undefined : `12345678${simulatedAccountSuffix}`;
      const res = await fellowshipService.retryDisbursement(id, override);
      if (res.status === 'SUCCESS') {
        setSuccessMessage(`Retry succeeded! PFMS Ref: ${res.pfms_reference_id}, Bank UTR: ${res.bank_reference_utr}`);
      } else {
        setError(`Retry failed: ${res.failure_reason}. Status: ${res.status}`);
      }
      await loadDisbursements();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Payment retry failed.');
    } finally {
      setProcessingId(null);
    }
  };

  const formatINR = (val: number) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);
  };

  // Metrics
  const totalDisbursed = installments.filter((i) => i.payment_status === 'SUCCESS').reduce((acc, i) => acc + i.total_amount, 0);
  const pendingApprovalCount = installments.filter((i) => i.payment_status === 'SCHEDULED' || i.payment_status === 'PENDING_APPROVAL').length;
  const readyDispatchCount = installments.filter((i) => i.payment_status === 'APPROVED_FOR_PAYMENT').length;
  const failedCount = installments.filter((i) => i.payment_status === 'FAILED' || i.payment_status === 'RETRY_EXHAUSTED').length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Statutory Simulation Notice Banner */}
      <div className="bg-amber-500/10 border-2 border-amber-500/40 rounded-2xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-amber-900 shadow-sm">
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />
          <div className="text-xs font-semibold">
            <span className="font-extrabold uppercase tracking-wide bg-amber-200/80 px-2 py-0.5 rounded text-amber-950 mr-2">
              SIMULATED DBT GATEWAY
            </span>
            <span>SIMULATED ENVIRONMENT: No actual government funds were transferred. All DBT dispatches use mock PFMS adapters.</span>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs bg-white/80 px-3 py-1.5 rounded-lg border border-amber-300">
          <span className="font-medium text-slate-700">Simulate Response:</span>
          <select
            value={simulatedAccountSuffix}
            onChange={(e) => setSimulatedAccountSuffix(e.target.value as any)}
            className="font-bold text-xs bg-transparent text-slate-800 outline-none"
          >
            <option value="NORMAL">Normal Success (200 OK)</option>
            <option value="9999">Simulate Account Mismatch (9999)</option>
            <option value="8888">Simulate Invalid IFSC (8888)</option>
          </select>
        </div>
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <CreditCard className="w-7 h-7 text-indigo-600" />
            Statutory Disbursement & DBT Desk
          </h1>
          <p className="text-sm text-slate-500">
            Admin oversight for direct benefit transfer (DBT) installments, approval locks, and PFMS gateway dispatches.
          </p>
        </div>
        <button
          onClick={loadDisbursements}
          className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 shadow-sm"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh Registry
        </button>
      </div>

      {/* Alerts */}
      {successMessage && (
        <div className="bg-emerald-50 border-l-4 border-emerald-500 p-4 rounded-r-lg text-sm text-emerald-800 flex items-center justify-between">
          <span>{successMessage}</span>
          <button onClick={() => setSuccessMessage(null)} className="text-emerald-700 font-bold">✕</button>
        </div>
      )}
      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-r-lg text-sm text-red-800 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-700 font-bold">✕</button>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Disbursed</div>
          <div className="text-2xl font-extrabold text-slate-900 mt-1">{formatINR(totalDisbursed)}</div>
          <div className="text-xs text-emerald-600 font-semibold mt-1 flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5" /> Settled via PFMS Mock
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">Pending Approval</div>
          <div className="text-2xl font-extrabold text-amber-600 mt-1">{pendingApprovalCount}</div>
          <div className="text-xs text-slate-500 mt-1">Requires official amount lock</div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">Approved Ready For Dispatch</div>
          <div className="text-2xl font-extrabold text-indigo-600 mt-1">{readyDispatchCount}</div>
          <div className="text-xs text-indigo-600 font-semibold mt-1">Row-locked & idempotent</div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">Failed / Exhausted</div>
          <div className="text-2xl font-extrabold text-red-600 mt-1">{failedCount}</div>
          <div className="text-xs text-red-600 mt-1">Retry limit: max 3 attempts</div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 text-xs">
        <span className="font-semibold text-slate-500 mr-2">Filter:</span>
        {['ALL', 'SCHEDULED', 'APPROVED_FOR_PAYMENT', 'SUCCESS', 'FAILED', 'RETRY_EXHAUSTED'].map((st) => (
          <button
            key={st}
            onClick={() => setFilterStatus(st)}
            className={`px-3 py-1.5 rounded-lg font-semibold transition-colors ${
              filterStatus === st
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            {st}
          </button>
        ))}
      </div>

      {/* Main Table */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-5 py-3 text-left font-semibold text-slate-700">Installment & Period</th>
              <th className="px-5 py-3 text-left font-semibold text-slate-700">Beneficiary Banking</th>
              <th className="px-5 py-3 text-right font-semibold text-slate-700">Amount Breakdown</th>
              <th className="px-5 py-3 text-left font-semibold text-slate-700">Status & Audit</th>
              <th className="px-5 py-3 text-right font-semibold text-slate-700">Administrative Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {installments.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center text-slate-500">
                  {loading ? 'Loading disbursement installments...' : 'No disbursement records matching the filter.'}
                </td>
              </tr>
            ) : (
              installments.map((inst) => {
                const isProcessing = processingId === inst.id;
                return (
                  <tr key={inst.id} className="hover:bg-slate-50/50">
                    <td className="px-5 py-4">
                      <div className="font-bold text-slate-900">
                        Installment #{inst.installment_number} (Year {inst.academic_year})
                      </div>
                      <div className="text-xs text-slate-500 font-mono mt-0.5">
                        {inst.period_start} → {inst.period_end}
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono mt-0.5 truncate max-w-[180px]">
                        Req: {inst.payment_request_id}
                      </div>
                    </td>

                    <td className="px-5 py-4">
                      <div className="font-mono text-xs font-bold text-slate-800">
                        {inst.account_number_masked}
                      </div>
                      <div className="text-xs text-slate-500 font-mono">IFSC: {inst.ifsc_code}</div>
                      <div className="text-[11px] text-slate-400">Mode: {inst.integration_mode}</div>
                    </td>

                    <td className="px-5 py-4 text-right">
                      <div className="font-bold text-slate-900 text-base">{formatINR(inst.total_amount)}</div>
                      <div className="text-[11px] text-slate-500">
                        Stipend: {formatINR(inst.stipend_amount)} | HRA: {formatINR(inst.hra_amount)}
                      </div>
                      <div className="text-[11px] text-slate-500">Contingency: {formatINR(inst.contingency_amount)}</div>
                    </td>

                    <td className="px-5 py-4">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold ${
                            inst.payment_status === 'SUCCESS'
                              ? 'bg-emerald-100 text-emerald-800'
                              : inst.payment_status === 'APPROVED_FOR_PAYMENT'
                              ? 'bg-indigo-100 text-indigo-800'
                              : inst.payment_status === 'FAILED'
                              ? 'bg-red-100 text-red-800'
                              : inst.payment_status === 'RETRY_EXHAUSTED'
                              ? 'bg-rose-200 text-rose-900'
                              : 'bg-amber-100 text-amber-800'
                          }`}
                        >
                          {inst.payment_status}
                        </span>
                        {inst.retry_count > 0 && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                            Attempt {inst.retry_count}/3
                          </span>
                        )}
                      </div>

                      {inst.bank_reference_utr && (
                        <div className="text-[11px] text-slate-600 font-mono mt-1">
                          UTR: <span className="font-bold text-emerald-700">{inst.bank_reference_utr}</span>
                        </div>
                      )}

                      {inst.failure_reason && (
                        <div className="text-[11px] text-red-600 font-medium mt-1 max-w-xs">
                          Reason: {inst.failure_reason}
                        </div>
                      )}
                    </td>

                    <td className="px-5 py-4 text-right">
                      {(inst.payment_status === 'SCHEDULED' || inst.payment_status === 'PENDING_APPROVAL') && (
                        <button
                          onClick={() => handleApprove(inst.id)}
                          disabled={isProcessing}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-300 transition-colors shadow-sm disabled:opacity-50"
                        >
                          <ShieldCheck className="w-3.5 h-3.5" />
                          Approve Amount
                        </button>
                      )}

                      {inst.payment_status === 'APPROVED_FOR_PAYMENT' && (
                        <button
                          onClick={() => handleExecute(inst.id)}
                          disabled={isProcessing}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm transition-colors disabled:opacity-50"
                        >
                          <Send className="w-3.5 h-3.5" />
                          {isProcessing ? 'Dispatching...' : 'Execute Dispatch'}
                        </button>
                      )}

                      {inst.payment_status === 'FAILED' && inst.retry_count < 3 && (
                        <button
                          onClick={() => handleRetry(inst.id)}
                          disabled={isProcessing}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-300 transition-colors shadow-sm disabled:opacity-50"
                        >
                          <RotateCcw className="w-3.5 h-3.5" />
                          {isProcessing ? 'Retrying...' : `Retry (${inst.retry_count}/3)`}
                        </button>
                      )}

                      {inst.payment_status === 'RETRY_EXHAUSTED' && (
                        <span className="text-xs font-bold text-slate-400 italic">
                          Retry Cap Reached
                        </span>
                      )}

                      {inst.payment_status === 'SUCCESS' && (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-600">
                          <CheckCircle2 className="w-4 h-4" /> Settled
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default AdminDisbursementDesk;
