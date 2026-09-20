import React, { useState } from 'react';
import {
  FileText,
  Eye,
  CheckCircle,
  AlertTriangle,
  XCircle,
  ChevronDown,
  ChevronUp,
  UserCheck,
  ShieldAlert,
} from 'lucide-react';
import { OfficerDocumentScrutinyItem } from '../../types/officer';
import { FieldComparisonGrid } from './FieldComparisonGrid';
import { AIFlagsBanner } from './AIFlagsBanner';
import { DocumentPreviewModal } from './DocumentPreviewModal';
import { AIOverrideModal } from './AIOverrideModal';

interface DocumentScrutinyCardProps {
  document: OfficerDocumentScrutinyItem;
  onSaveDecision: (
    documentId: string,
    decision: 'VERIFIED' | 'RESUBMISSION_REQUIRED' | 'REJECTED',
    remarks?: string,
    aiOverride?: boolean,
    overrideReason?: string
  ) => Promise<void>;
}

export const DocumentScrutinyCard: React.FC<DocumentScrutinyCardProps> = ({
  document,
  onSaveDecision,
}) => {
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [isOverrideModalOpen, setIsOverrideModalOpen] = useState(false);
  const [showOcrText, setShowOcrText] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [historyPreviewDoc, setHistoryPreviewDoc] = useState<{
    id: string;
    original_filename: string;
    mime_type: string;
  } | null>(null);

  // Decision form state
  const [selectedDecision, setSelectedDecision] = useState<
    'VERIFIED' | 'RESUBMISSION_REQUIRED' | 'REJECTED' | ''
  >(document.officer_decision || '');
  const [remarks, setRemarks] = useState(document.officer_remarks || '');
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const hasAiFlags = document.flags && document.flags.length > 0;

  const handleDecisionClick = (decision: 'VERIFIED' | 'RESUBMISSION_REQUIRED' | 'REJECTED') => {
    setSelectedDecision(decision);
    setErrorMessage(null);

    // If officer chooses to verify a document that has AI flags, trigger the override modal
    if (decision === 'VERIFIED' && hasAiFlags) {
      setIsOverrideModalOpen(true);
    }
  };

  const handleConfirmOverride = async (reason: string) => {
    setIsOverrideModalOpen(false);
    setIsSaving(true);
    try {
      await onSaveDecision(document.id, 'VERIFIED', remarks, true, reason);
      setSelectedDecision('VERIFIED');
    } catch (err: any) {
      setErrorMessage(err.response?.data?.error || 'Failed to save document decision');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveStandardDecision = async () => {
    if (!selectedDecision) {
      setErrorMessage('Please select a decision (Verify, Flag Deficient, or Reject).');
      return;
    }

    if (selectedDecision === 'VERIFIED' && hasAiFlags) {
      setIsOverrideModalOpen(true);
      return;
    }

    if ((selectedDecision === 'RESUBMISSION_REQUIRED' || selectedDecision === 'REJECTED') && !remarks.trim()) {
      setErrorMessage(`Remarks are mandatory when marking a document as ${selectedDecision}.`);
      return;
    }

    setIsSaving(true);
    setErrorMessage(null);
    try {
      await onSaveDecision(document.id, selectedDecision, remarks.trim(), false, undefined);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.error || 'Failed to save document decision');
    } finally {
      setIsSaving(false);
    }
  };

  // Determine current badge for document status
  const getDocStatusBadge = () => {
    if (document.officer_decision === 'VERIFIED') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
          <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
          Human Verified
        </span>
      );
    }
    if (document.officer_decision === 'RESUBMISSION_REQUIRED') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-orange-100 text-orange-800 border border-orange-300">
          <AlertTriangle className="w-3.5 h-3.5 text-orange-600" />
          Flagged Deficient
        </span>
      );
    }
    if (document.officer_decision === 'REJECTED') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300">
          <XCircle className="w-3.5 h-3.5 text-rose-600" />
          Document Rejected
        </span>
      );
    }
    if (document.status === 'VERIFIED') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-teal-50 text-teal-800 border border-teal-200">
          AI Verified (Awaiting Scrutiny)
        </span>
      );
    }
    if (document.status === 'FLAGGED') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200">
          AI Flagged (Awaiting Scrutiny)
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
        {document.status}
      </span>
    );
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden mb-6">
      {/* Card Top Header */}
      <div className="bg-slate-50 border-b border-slate-200 p-4 sm:px-6 sm:py-3.5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-teal-800 text-white flex items-center justify-center shadow-xs">
            <FileText className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-bold text-slate-900 text-sm sm:text-base capitalize">
                {document.document_type.replace(/_/g, ' ')}
              </h3>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-200 text-slate-800">
                v{document.version || 1}
              </span>
              {document.version && document.version > 1 && (
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-200">
                  Replacement
                </span>
              )}
              {getDocStatusBadge()}
            </div>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              {document.original_filename} ({(document.file_size / 1024).toFixed(1)} KB)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsPreviewOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 shadow-xs transition-colors"
          >
            <Eye className="w-3.5 h-3.5 text-teal-700" />
            Preview Original
          </button>
          <DocumentPreviewModal
            documentId={document.id}
            originalFilename={document.original_filename}
            mimeType={document.mime_type}
            isOpen={isPreviewOpen}
            onClose={() => setIsPreviewOpen(false)}
          />
        </div>
      </div>

      <div className="p-4 sm:p-6 space-y-5">
        {/* Existing Human Decision Metadata Banner */}
        {document.verified_by_name && (
          <div className="rounded-lg bg-slate-50 border border-slate-200 p-3 flex flex-wrap items-center justify-between text-xs text-slate-600 gap-2">
            <div className="flex items-center gap-1.5">
              <UserCheck className="w-4 h-4 text-teal-700" />
              <span>
                Scrutinized by <strong>{document.verified_by_name}</strong> on{' '}
                {document.verified_at ? new Date(document.verified_at).toLocaleString('en-IN') : ''}
              </span>
            </div>
            {document.ai_override && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-900 border border-amber-300">
                <ShieldAlert className="w-3 h-3 text-amber-700" />
                AI Flag Overridden: {document.override_reason}
              </span>
            )}
          </div>
        )}

        {/* AI Flags Warning (if any) */}
        <AIFlagsBanner flags={document.flags} overallConfidence={document.overall_confidence} />

        {/* OCR Field Match Matrix */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Field-Level Verification Matrix (Form vs. Document Evidence)
            </h4>
            {document.ocr_text && (
              <button
                onClick={() => setShowOcrText(!showOcrText)}
                className="text-xs text-teal-700 hover:text-teal-900 font-semibold inline-flex items-center gap-1"
              >
                {showOcrText ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                {showOcrText ? 'Hide Raw OCR Text' : 'View Raw OCR Extraction'}
              </button>
            )}
          </div>

          <FieldComparisonGrid
            comparisonResults={document.comparison_results || {}}
            extractedFields={document.extracted_fields || {}}
            fieldConfidences={document.field_confidences || {}}
          />

          {showOcrText && document.ocr_text && (
            <div className="mt-3 p-3 bg-slate-900 text-slate-200 font-mono text-[11px] rounded-lg max-h-48 overflow-y-auto border border-slate-700">
              <div className="text-[10px] text-slate-400 uppercase font-sans mb-1 font-bold">
                Raw Extracted OCR Stream:
              </div>
              <pre className="whitespace-pre-wrap">{document.ocr_text}</pre>
            </div>
          )}
        </div>

        {/* Document Revision History (Phase 5 Lineage) */}
        {document.history && document.history.length > 0 && (
          <div className="rounded-lg border border-purple-200 bg-purple-50/50 p-3.5">
            <button
              type="button"
              onClick={() => setShowHistory(!showHistory)}
              className="w-full flex items-center justify-between text-xs font-bold text-purple-950 hover:text-purple-800"
            >
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-purple-200 text-purple-900">
                  {document.history.length} Prior Version{document.history.length > 1 ? 's' : ''}
                </span>
                <span>Document Revision History & Superseded Audits</span>
              </div>
              {showHistory ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>

            {showHistory && (
              <div className="mt-3 space-y-2 pt-2 border-t border-purple-200">
                {document.history.map((hist) => (
                  <div
                    key={hist.id}
                    className="p-3 bg-white rounded-lg border border-purple-100 text-xs text-slate-700 flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-2xs"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-900">v{hist.version}</span>
                        <span className="font-mono text-slate-500">{hist.original_filename}</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">
                          {hist.status}
                        </span>
                      </div>
                      <div className="mt-1 text-[11px] text-slate-500">
                        Uploaded on {new Date(hist.uploaded_at).toLocaleString('en-IN')}
                        {hist.officer_remarks && (
                          <span className="ml-2 font-medium text-rose-700">
                            • Officer note: "{hist.officer_remarks}"
                          </span>
                        )}
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() =>
                        setHistoryPreviewDoc({
                          id: hist.id,
                          original_filename: hist.original_filename,
                          mime_type: hist.mime_type,
                        })
                      }
                      className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold text-purple-800 hover:text-purple-950 bg-purple-100/70 hover:bg-purple-200 rounded transition-colors self-start sm:self-center"
                    >
                      <Eye className="w-3 h-3" />
                      View Archival Doc
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Officer Human Decision Section */}
        <div className="pt-4 border-t border-slate-200">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 mb-2.5">
            Record Officer Scrutiny Determination
          </h4>

          {/* Decision Buttons */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 mb-3">
            <button
              type="button"
              onClick={() => handleDecisionClick('VERIFIED')}
              className={`p-2.5 rounded-lg border text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
                selectedDecision === 'VERIFIED'
                  ? 'bg-emerald-600 text-white border-emerald-600 shadow-xs'
                  : 'bg-white text-slate-700 border-slate-300 hover:bg-emerald-50 hover:text-emerald-800 hover:border-emerald-300'
              }`}
            >
              <CheckCircle className="w-4 h-4" />
              Verify Document
            </button>

            <button
              type="button"
              onClick={() => handleDecisionClick('RESUBMISSION_REQUIRED')}
              className={`p-2.5 rounded-lg border text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
                selectedDecision === 'RESUBMISSION_REQUIRED'
                  ? 'bg-orange-600 text-white border-orange-600 shadow-xs'
                  : 'bg-white text-slate-700 border-slate-300 hover:bg-orange-50 hover:text-orange-800 hover:border-orange-300'
              }`}
            >
              <AlertTriangle className="w-4 h-4" />
              Flag Deficient (Resubmit)
            </button>

            <button
              type="button"
              onClick={() => handleDecisionClick('REJECTED')}
              className={`p-2.5 rounded-lg border text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
                selectedDecision === 'REJECTED'
                  ? 'bg-rose-600 text-white border-rose-600 shadow-xs'
                  : 'bg-white text-slate-700 border-slate-300 hover:bg-rose-50 hover:text-rose-800 hover:border-rose-300'
              }`}
            >
              <XCircle className="w-4 h-4" />
              Reject Document
            </button>
          </div>

          {/* Remarks Input */}
          <div className="space-y-2">
            <label className="block text-xs font-medium text-slate-600">
              Officer Remarks / Observations{' '}
              {selectedDecision in ['RESUBMISSION_REQUIRED', 'REJECTED'] && (
                <span className="text-rose-600 font-bold">*</span>
              )}
            </label>
            <input
              type="text"
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              placeholder="e.g. Caste certificate verified with district portal roll number."
              className="w-full text-xs rounded-lg border border-slate-300 p-2 text-slate-900 focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
            />
            {errorMessage && <p className="text-xs text-rose-600">{errorMessage}</p>}
          </div>

          <div className="mt-3 flex justify-end">
            <button
              type="button"
              disabled={isSaving || !selectedDecision}
              onClick={handleSaveStandardDecision}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-semibold bg-teal-800 hover:bg-teal-900 text-white shadow-xs transition-colors disabled:opacity-50"
            >
              {isSaving ? 'Saving Decision...' : 'Save Document Scrutiny'}
            </button>
          </div>
        </div>
      </div>

      {/* AI Override Confirmation Modal */}
      <AIOverrideModal
        isOpen={isOverrideModalOpen}
        documentType={document.document_type}
        flags={document.flags}
        onConfirm={handleConfirmOverride}
        onCancel={() => setIsOverrideModalOpen(false)}
      />

      {/* Archival / Revision Document Preview Modal */}
      {historyPreviewDoc && (
        <DocumentPreviewModal
          documentId={historyPreviewDoc.id}
          originalFilename={historyPreviewDoc.original_filename}
          mimeType={historyPreviewDoc.mime_type}
          isOpen={!!historyPreviewDoc}
          onClose={() => setHistoryPreviewDoc(null)}
        />
      )}
    </div>
  );
};
