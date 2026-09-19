import React, { useState } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ArrowLeft,
  ShieldCheck,
  Send,
  AlertCircle,
} from 'lucide-react';
import {
  Application,
  FormSchema,
  RequiredDocumentConfig,
  DocumentItem,
} from '../types/application';

interface Props {
  application: Application;
  schemeName: string;
  schemeCode: string;
  schemeVersion: string;
  formSchema: FormSchema;
  requiredDocsConfig: RequiredDocumentConfig[];
  uploadedDocuments: DocumentItem[];
  onBackToEdit: () => void;
  onSubmit: () => Promise<void>;
  isSubmitting: boolean;
}

export const ApplicationReview: React.FC<Props> = ({
  application,
  schemeName,
  schemeCode,
  schemeVersion,
  formSchema,
  requiredDocsConfig,
  uploadedDocuments,
  onBackToEdit,
  onSubmit,
  isSubmitting,
}) => {
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const sections = formSchema.sections || [];
  const formData = application.form_data || {};
  const uploadedCodes = new Set(uploadedDocuments.map((d) => d.document_type));

  // Compute missing required fields
  const missingFields: string[] = [];
  sections.forEach((sec) => {
    (sec.fields || []).forEach((field) => {
      if (field.required) {
        let val = formData[field.name];
        if (val === undefined || val === null && sec.id) {
          val = formData[sec.id]?.[field.name];
        }
        if (
          val === undefined ||
          val === null ||
          (typeof val === 'string' && !val.trim()) ||
          (typeof val === 'boolean' && !val)
        ) {
          missingFields.push(field.label);
        }
      }
    });
  });

  // Compute missing required documents
  const missingDocs = requiredDocsConfig
    .filter((doc) => doc.required && !uploadedCodes.has(doc.code || doc.type || ''))
    .map((d) => d.name || d.label || d.code);

  const canSubmit = missingFields.length === 0 && missingDocs.length === 0;

  const handleConfirmSubmit = async () => {
    try {
      setSubmitError(null);
      await onSubmit();
      setShowConfirmModal(false);
    } catch (err: any) {
      console.error('Submission failed', err);
      setSubmitError(
        err.response?.data?.error ||
          'Failed to submit application. Please verify all requirements.'
      );
    }
  };

  return (
    <div className="space-y-6">
      {/* Dossier Header */}
      <div className="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-teal-50 text-teal-800 border border-teal-200 uppercase tracking-wider">
                {schemeCode} v{schemeVersion}
              </span>
              <span className="text-xs text-slate-500 font-mono">
                Ref: {application.reference_id}
              </span>
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900 mt-1">
              Final Pre-Submission Review: {schemeName}
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Please inspect all entered information and uploaded documents before formal submission.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onBackToEdit}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back & Edit
            </button>
            <button
              type="button"
              disabled={!canSubmit || isSubmitting}
              onClick={() => setShowConfirmModal(true)}
              className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-teal-700 hover:bg-teal-800 disabled:bg-slate-300 text-white text-xs font-bold transition-all shadow-sm disabled:cursor-not-allowed"
            >
              <Send className="w-4 h-4" />
              Submit Application
            </button>
          </div>
        </div>

        {/* Validation Issues Alert */}
        {!canSubmit && (
          <div className="mt-6 p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-950 text-xs space-y-2">
            <div className="flex items-center gap-2 font-bold text-amber-900">
              <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0" />
              <span>Submission Blocked — Mandatory Information Missing:</span>
            </div>
            {missingFields.length > 0 && (
              <p className="text-[11px] text-amber-800">
                • <strong className="font-semibold">Missing Form Fields:</strong> {missingFields.join(', ')}
              </p>
            )}
            {missingDocs.length > 0 && (
              <p className="text-[11px] text-amber-800">
                • <strong className="font-semibold">Missing Mandatory Documents:</strong> {missingDocs.join(', ')}
              </p>
            )}
          </div>
        )}

        {submitError && (
          <div className="mt-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-800 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
            <span>{submitError}</span>
          </div>
        )}
      </div>

      {/* Grouped Form Data Sections */}
      <div className="space-y-6">
        {sections.map((section) => (
          <div
            key={section.id}
            className="bg-white p-6 sm:p-7 rounded-2xl border border-slate-200 shadow-sm space-y-4"
          >
            <div className="border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900">
                {section.title}
              </h3>
              {section.description && (
                <p className="text-xs text-slate-400 mt-0.5">
                  {section.description}
                </p>
              )}
            </div>

            <div className="grid sm:grid-cols-2 gap-4 text-xs">
              {(section.fields || []).map((field) => {
                let val = formData[field.name];
                if (val === undefined && section.id) {
                  val = formData[section.id]?.[field.name];
                }

                let displayVal = val;
                if (val === true) displayVal = 'Yes (Confirmed)';
                if (val === false) displayVal = 'No';
                if (val === undefined || val === null || val === '') {
                  displayVal = (
                    <span className="text-amber-600 font-semibold italic">
                      {field.required ? 'Missing (Required)' : 'Not provided'}
                    </span>
                  );
                }

                return (
                  <div
                    key={field.name}
                    className="p-3 rounded-xl bg-slate-50 border border-slate-100"
                  >
                    <span className="text-[11px] font-semibold text-slate-500 block mb-0.5">
                      {field.label}
                    </span>
                    <span className="text-xs font-bold text-slate-900 break-words">
                      {displayVal}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}

        {/* Uploaded Documents Summary */}
        <div className="bg-white p-6 sm:p-7 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-sm font-bold text-slate-900">
              Uploaded Supporting Documents ({uploadedDocuments.length})
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Verified against mandatory document checklist.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 gap-3">
            {requiredDocsConfig.map((docCfg) => {
              const code = docCfg.code || docCfg.type || '';
              const label = docCfg.name || docCfg.label || code;
              const uploaded = uploadedDocuments.find((d) => d.document_type === code);

              return (
                <div
                  key={code}
                  className={`p-3.5 rounded-xl border flex items-center justify-between gap-3 text-xs ${
                    uploaded
                      ? 'bg-emerald-50/30 border-emerald-200'
                      : 'bg-red-50/30 border-red-200'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    {uploaded ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
                    )}
                    <div>
                      <p className="font-bold text-slate-900">{label}</p>
                      {uploaded ? (
                        <p className="text-[11px] text-slate-500 font-mono">
                          {uploaded.original_filename}
                        </p>
                      ) : (
                        <p className="text-[11px] text-red-700 font-semibold">
                          Document not uploaded yet
                        </p>
                      )}
                    </div>
                  </div>

                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      uploaded
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-red-100 text-red-800'
                    }`}
                  >
                    {uploaded ? 'UPLOADED' : 'REQUIRED'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6 border border-slate-200 space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="w-12 h-12 rounded-xl bg-teal-100 text-teal-800 flex items-center justify-center mx-auto">
              <ShieldCheck className="w-6 h-6" />
            </div>

            <div className="text-center">
              <h3 className="text-base font-bold text-slate-900">
                Confirm Formal Application Submission
              </h3>
              <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                Once submitted, your application will be bound to scheme version{' '}
                <strong className="text-slate-800">v{schemeVersion}</strong> with frozen eligibility rules.
                You will no longer be able to modify the application data or replace documents.
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-blue-50 border border-blue-200 text-[11px] text-blue-900">
              <strong>Workflow Progression:</strong> Your application status will advance to{' '}
              <span className="font-mono font-bold">UNDER_AI_VERIFICATION</span> for automated screening.
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowConfirmModal(false)}
                disabled={isSubmitting}
                className="px-4 py-2 rounded-lg border border-slate-300 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmSubmit}
                disabled={isSubmitting}
                className="inline-flex items-center gap-1.5 px-5 py-2 rounded-lg bg-teal-700 hover:bg-teal-800 text-white text-xs font-bold shadow-sm transition-all"
              >
                {isSubmitting ? 'Submitting...' : 'Confirm & Submit'}
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
