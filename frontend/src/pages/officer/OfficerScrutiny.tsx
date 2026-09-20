import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  FileText,
  UserCheck,
  BookOpen,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { officerService } from '../../services/officerService';
import { OfficerApplicationScrutinyResponse } from '../../types/officer';
import { ScrutinyHeader } from '../../components/officer/ScrutinyHeader';
import { ApplicationDetailsCard } from '../../components/officer/ApplicationDetailsCard';
import { DocumentScrutinyCard } from '../../components/officer/DocumentScrutinyCard';
import { ApplicationDecisionBar } from '../../components/officer/ApplicationDecisionBar';

export const OfficerScrutiny: React.FC = () => {
  const { applicationId } = useParams<{ applicationId: string }>();
  const navigate = useNavigate();

  const [data, setData] = useState<OfficerApplicationScrutinyResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState<'documents' | 'dossier' | 'scheme'>('documents');
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(
    null
  );

  const fetchScrutinyData = useCallback(async () => {
    if (!applicationId) return;
    setIsLoading(true);
    try {
      const res = await officerService.getScrutiny(applicationId);
      setData(res);
    } catch (err: any) {
      console.error('Failed to load application scrutiny details', err);
      setNotification({
        type: 'error',
        message: err.response?.data?.error || 'Failed to access application scrutiny workspace.',
      });
    } finally {
      setIsLoading(false);
    }
  }, [applicationId]);

  useEffect(() => {
    fetchScrutinyData();
  }, [fetchScrutinyData]);

  const handleSaveDocumentDecision = async (
    documentId: string,
    decision: 'VERIFIED' | 'RESUBMISSION_REQUIRED' | 'REJECTED',
    remarks?: string,
    aiOverride?: boolean,
    overrideReason?: string
  ) => {
    try {
      const updatedDoc = await officerService.recordDocumentDecision(documentId, {
        decision,
        remarks,
        ai_override: aiOverride,
        override_reason: overrideReason,
      });

      // Update document item in local state
      setData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          documents: prev.documents.map((d) => (d.id === documentId ? updatedDoc : d)),
        };
      });

      setNotification({
        type: 'success',
        message: `Decision saved: ${decision.replace(/_/g, ' ')} recorded for document.`,
      });
      setTimeout(() => setNotification(null), 4000);
    } catch (err: any) {
      console.error('Failed to save document scrutiny decision', err);
      setNotification({
        type: 'error',
        message: err.response?.data?.error || 'Failed to save document decision.',
      });
      throw err;
    }
  };

  const handleSubmitApplicationDecision = async (
    decision: 'VERIFIED' | 'DEFICIENT' | 'REJECTED',
    remarks: string
  ) => {
    if (!applicationId) return;
    setIsSubmitting(true);
    try {
      const updatedApp = await officerService.recordApplicationDecision(applicationId, {
        decision,
        remarks,
      });

      setData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          status: updatedApp.status,
          scrutiny_remarks: remarks,
        };
      });

      setNotification({
        type: 'success',
        message: `Application scrutiny finalized successfully: ${decision}.`,
      });

      // After 2.5 seconds, navigate back to queue
      setTimeout(() => {
        navigate('/officer/dashboard');
      }, 2500);
    } catch (err: any) {
      console.error('Failed to finalize application scrutiny', err);
      setNotification({
        type: 'error',
        message: err.response?.data?.error || 'Failed to finalize application determination.',
      });
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6">
        <Loader2 className="w-10 h-10 animate-spin text-teal-700 mb-3" />
        <h2 className="text-base font-semibold text-slate-800">
          Loading Human Scrutiny Workspace...
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Assembling original documents, OCR evidence, and jurisdiction verification...
        </p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-slate-50 p-8 flex flex-col items-center justify-center text-center">
        <div className="w-14 h-14 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center mb-3">
          <AlertCircle className="w-8 h-8" />
        </div>
        <h2 className="text-lg font-bold text-slate-900">Application Access Restricted</h2>
        <p className="text-sm text-slate-600 max-w-md mt-1 mb-4">
          {notification?.message ||
            'You do not have desk verification jurisdiction over this application, or it does not exist.'}
        </p>
        <button
          onClick={() => navigate('/officer/dashboard')}
          className="px-4 py-2 rounded-lg text-xs font-semibold bg-teal-800 text-white hover:bg-teal-700"
        >
          Return to Assigned Queue
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-100/60 flex flex-col justify-between">
      <div>
        {/* Top Header */}
        <ScrutinyHeader data={data} />

        {/* Floating Notification Toast */}
        {notification && (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-4">
            <div
              className={`p-3.5 rounded-lg text-xs font-medium flex items-center justify-between border ${
                notification.type === 'success'
                  ? 'bg-emerald-50 text-emerald-900 border-emerald-300'
                  : 'bg-rose-50 text-rose-900 border-rose-300'
              }`}
            >
              <div className="flex items-center gap-2">
                {notification.type === 'success' ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
                )}
                <span>{notification.message}</span>
              </div>
              <button
                onClick={() => setNotification(null)}
                className="text-slate-500 hover:text-slate-700 font-bold ml-4"
              >
                ✕
              </button>
            </div>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6">
          <div className="flex border-b border-slate-200 gap-6">
            <button
              onClick={() => setActiveTab('documents')}
              className={`pb-3 text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-colors border-b-2 ${
                activeTab === 'documents'
                  ? 'border-teal-700 text-teal-900'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              <FileText className="w-4 h-4" />
              Document Scrutiny & AI Evidence ({data.documents.length})
            </button>

            <button
              onClick={() => setActiveTab('dossier')}
              className={`pb-3 text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-colors border-b-2 ${
                activeTab === 'dossier'
                  ? 'border-teal-700 text-teal-900'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              <UserCheck className="w-4 h-4" />
              Applicant Dossier & Form Data
            </button>

            <button
              onClick={() => setActiveTab('scheme')}
              className={`pb-3 text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-colors border-b-2 ${
                activeTab === 'scheme'
                  ? 'border-teal-700 text-teal-900'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              <BookOpen className="w-4 h-4" />
              Scheme Rules Snapshot ({data.scheme_code})
            </button>
          </div>
        </div>

        {/* Tab Content Area */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6 pb-12">
          {activeTab === 'documents' && (
            <div>
              <div className="mb-4 flex items-center justify-between">
                <p className="text-xs text-slate-500">
                  Carefully examine each uploaded certificate against the extracted OCR fields and AI flags. Record individual determinations below.
                </p>
              </div>

              {data.documents.map((doc) => (
                <DocumentScrutinyCard
                  key={doc.id}
                  document={doc}
                  onSaveDecision={handleSaveDocumentDecision}
                />
              ))}
            </div>
          )}

          {activeTab === 'dossier' && (
            <ApplicationDetailsCard data={data} />
          )}

          {activeTab === 'scheme' && (
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
              <h3 className="text-sm font-bold text-slate-900 mb-2 uppercase tracking-wide">
                Governing Scheme Eligibility Rules ({data.scheme_name})
              </h3>
              <p className="text-xs text-slate-500 mb-4">
                These are the immutable rules snapshot frozen at the time of application submission under Scheme Version {data.scheme_version || '1.0'}.
              </p>
              <pre className="bg-slate-900 text-slate-100 p-4 rounded-lg font-mono text-xs overflow-auto max-h-96">
                {JSON.stringify(data.eligibility_rules || {}, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>

      {/* Sticky Bottom Action Bar */}
      <ApplicationDecisionBar
        documents={data.documents}
        requiredDocConfigs={data.required_documents_config}
        currentStatus={data.status}
        isSubmitting={isSubmitting}
        onSubmitDecision={handleSubmitApplicationDecision}
      />
    </div>
  );
};
