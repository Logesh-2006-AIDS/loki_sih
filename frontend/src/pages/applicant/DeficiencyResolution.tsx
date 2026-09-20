import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  ShieldCheck,
} from 'lucide-react';
import { deficiencyService } from '../../services/deficiencyService';
import { PublicDeficiencyListResponse } from '../../types/deficiency';
import { DeficiencyCard } from '../../components/deficiency/DeficiencyCard';
import { ResubmissionFooterBar } from '../../components/deficiency/ResubmissionFooterBar';

export const DeficiencyResolution: React.FC = () => {
  const { applicationId } = useParams<{ applicationId: string }>();
  const navigate = useNavigate();

  const [data, setData] = useState<PublicDeficiencyListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [notification, setNotification] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);

  const fetchDeficiencies = useCallback(async () => {
    if (!applicationId) return;
    setIsLoading(true);
    try {
      const res = await deficiencyService.getDeficiencies(applicationId);
      setData(res);
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? ((err as { response: { data: { error?: string } } }).response.data?.error || 'Failed to load deficiencies.')
          : 'Failed to load deficiencies.';
      setNotification({ type: 'error', message: msg });
    } finally {
      setIsLoading(false);
    }
  }, [applicationId]);

  useEffect(() => {
    fetchDeficiencies();
  }, [fetchDeficiencies]);

  const handleUploadReplacement = async (
    deficiencyId: string,
    file: File,
    remarks?: string
  ) => {
    if (!applicationId) return;
    try {
      const res = await deficiencyService.uploadReplacementDocument(
        applicationId,
        deficiencyId,
        file,
        remarks
      );
      setNotification({
        type: 'success',
        message: res.message || 'Replacement uploaded successfully.',
      });
      await fetchDeficiencies();
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? ((err as { response: { data: { error?: string } } }).response.data?.error || 'Upload failed.')
          : 'Upload failed.';
      setNotification({ type: 'error', message: msg });
      throw err;
    }
  };

  const handleResubmit = async (declarationConfirmed: boolean, remarks?: string) => {
    if (!applicationId) return;
    setIsSubmitting(true);
    setNotification(null);
    try {
      const res = await deficiencyService.resubmitApplication(applicationId, {
        declaration_confirmed: declarationConfirmed,
        remarks,
      });
      setNotification({
        type: 'success',
        message: `Application ${res.reference_id} successfully resubmitted! Re-entering scrutiny.`,
      });
      setTimeout(() => {
        navigate('/dashboard');
      }, 2000);
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? ((err as { response: { data: { error?: string } } }).response.data?.error || 'Resubmission failed.')
          : 'Resubmission failed.';
      setNotification({ type: 'error', message: msg });
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin text-amber-500 mx-auto mb-3" />
          <p className="text-slate-400 text-sm">Loading deficiency dossier...</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-slate-950 p-6 flex items-center justify-center">
        <div className="text-center max-w-md">
          <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-3" />
          <h2 className="text-xl font-bold text-white mb-2">Deficiency Data Unavailable</h2>
          <p className="text-slate-400 text-sm mb-5">
            Unable to load deficiency records for this application. Please check your credentials or access rights.
          </p>
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-sm font-semibold rounded-lg"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        {/* Navigation & Header */}
        <div className="mb-6">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors mb-3"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </Link>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-amber-500/20 text-amber-400 rounded-lg">
                  <ShieldCheck className="w-6 h-6" />
                </div>
                <div>
                  <h1 className="text-xl sm:text-2xl font-bold text-white">
                    Deficiency Resolution Workbench
                  </h1>
                  <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
                    Resolve flagged document issues and resubmit your application for verification.
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="px-3 py-1 bg-amber-500/20 border border-amber-500/40 text-amber-300 rounded-full text-xs font-semibold">
                Status: {data.application_status}
              </span>
            </div>
          </div>
        </div>

        {/* Global Notification Banner */}
        {notification && (
          <div
            className={`p-4 rounded-xl border mb-6 flex items-start gap-3 ${
              notification.type === 'success'
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-200'
                : 'bg-red-500/10 border-red-500/30 text-red-200'
            }`}
          >
            {notification.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            )}
            <div className="text-sm font-medium">{notification.message}</div>
          </div>
        )}

        {/* Informational Guidance Box */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 sm:p-5 mb-6">
          <h3 className="text-xs uppercase tracking-wider font-semibold text-slate-300 mb-2">
            Resolution Instructions
          </h3>
          <ul className="text-xs sm:text-sm text-slate-400 space-y-1.5 list-disc list-inside">
            <li>
              Review the officer remarks on each deficient document card below carefully.
            </li>
            <li>
              Upload clear, authentic replacement documents in PDF, PNG, or JPG format (Max 5 MB).
            </li>
            <li>
              Previous documents are retained in the audit history; uploading a replacement creates a new version.
            </li>
            <li>
              You must upload replacements for all itemized deficiencies before the &ldquo;Resubmit Application&rdquo; button activates.
            </li>
          </ul>
        </div>

        {/* Deficiency Cards List */}
        <div className="space-y-5">
          {data.items.map((item) => (
            <DeficiencyCard
              key={item.id}
              deficiency={item}
              onUploadReplacement={handleUploadReplacement}
            />
          ))}
        </div>

        {/* Sticky Resubmission Footer Bar */}
        <ResubmissionFooterBar
          totalCount={data.total}
          replacedCount={data.replacement_uploaded_count}
          canResubmit={data.can_resubmit}
          isSubmitting={isSubmitting}
          onResubmit={handleResubmit}
        />
      </div>
    </div>
  );
};
