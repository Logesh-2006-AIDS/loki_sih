import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { Application, DocumentItem, FormSchema, RequiredDocumentConfig } from '../../types/application';
import { SchemeDetail as SchemeDetailType, SchemeVersion } from '../../types/scheme';
import { applicationService } from '../../services/applicationService';
import { schemeService } from '../../services/schemeService';
import { DynamicForm } from '../../components/DynamicForm';
import { DocumentUploadManager } from '../../components/DocumentUploadManager';
import { ApplicationReview } from '../../components/ApplicationReview';
import { ApplicationTracker } from '../../components/ApplicationTracker';

export const ApplicationWizard: React.FC = () => {
  const { applicationId } = useParams<{ applicationId: string }>();
  const navigate = useNavigate();

  const [application, setApplication] = useState<Application | null>(null);
  const [scheme, setScheme] = useState<SchemeDetailType | null>(null);
  const [version, setVersion] = useState<SchemeVersion | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [activeStep, setActiveStep] = useState<'form' | 'documents' | 'review'>('form');

  useEffect(() => {
    if (applicationId) {
      loadApplicationData(applicationId);
    }
  }, [applicationId]);

  const loadApplicationData = async (id: string) => {
    try {
      setLoading(true);
      const app = await applicationService.getApplication(id);
      setApplication(app);
      setFormData(app.form_data || {});

      // Load Scheme and Version
      const schemeData = await schemeService.getScheme(app.scheme_id);
      setScheme(schemeData);

      let targetVersion: SchemeVersion | null = null;
      if (app.scheme_version_id) {
        const versions = await schemeService.getSchemeVersions(app.scheme_id);
        targetVersion = versions.find((v) => v.id === app.scheme_version_id) || null;
      }
      if (!targetVersion) {
        targetVersion = schemeData.active_version || null;
      }
      setVersion(targetVersion);

      // Load Documents
      const docs = await applicationService.listDocuments(id);
      setDocuments(docs);
    } catch (err: any) {
      console.error('Failed to load application wizard', err);
      alert(err.response?.data?.error || 'Unable to access application.');
      navigate('/applicant/dashboard');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveDraft = async () => {
    if (!application) return;
    try {
      const updated = await applicationService.updateDraft(application.id, formData);
      setApplication(updated);
    } catch (err: any) {
      console.error('Failed to auto-save draft', err);
      throw err;
    }
  };

  const handleRefreshDocuments = async () => {
    if (!application) return;
    const docs = await applicationService.listDocuments(application.id);
    setDocuments(docs);
  };

  const handleSubmitApplication = async () => {
    if (!application) return;
    try {
      setSubmitting(true);
      // Ensure latest form data is saved before submit
      await applicationService.updateDraft(application.id, formData);
      const submitted = await applicationService.submitApplication(application.id);
      setApplication(submitted);
      // Reload documents to get latest statuses
      await handleRefreshDocuments();
    } catch (err: any) {
      console.error('Failed to submit application', err);
      throw err;
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="inline-block w-8 h-8 border-4 border-teal-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="mt-3 text-xs text-slate-500">Loading application wizard...</p>
        </div>
      </div>
    );
  }

  if (!application || !scheme) {
    return null;
  }

  const isDraft = application.status === 'DRAFT';
  const rawFormSchema: FormSchema = (version?.form_schema || scheme.form_schema || { sections: [] }) as FormSchema;
  const rawRequiredDocs = (version?.required_documents?.documents ||
    scheme.required_documents?.documents ||
    []) as RequiredDocumentConfig[];

  const schemeVersionLabel = version?.scheme_version || scheme.scheme_version || '1.0';

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Navigation Bar */}
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={() => navigate('/applicant/dashboard')}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </button>

          <span className="text-xs text-slate-500 font-mono">
            Dossier: {application.reference_id}
          </span>
        </div>

        {/* If Application is Submitted or Under AI Verification: Render Tracker & Read-Only Review */}
        {!isDraft ? (
          <div className="space-y-6">
            <ApplicationTracker
              status={application.status}
              submittedAt={application.submitted_at}
              referenceId={application.reference_id}
            />

            <div className="border-t border-slate-200 pt-6">
              <ApplicationReview
                application={application}
                schemeName={scheme.name}
                schemeCode={scheme.scheme_code}
                schemeVersion={schemeVersionLabel}
                formSchema={rawFormSchema}
                requiredDocsConfig={rawRequiredDocs}
                uploadedDocuments={documents}
                onBackToEdit={() => {}}
                onSubmit={async () => {}}
                isSubmitting={false}
              />
            </div>
          </div>
        ) : (
          /* Application is in DRAFT: Render Interactive 3-Phase Stepper */
          <div className="space-y-6">
            {/* 3-Step Wizard Navigation Stepper */}
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between gap-2 overflow-x-auto">
              <button
                type="button"
                onClick={() => setActiveStep('form')}
                className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-xs font-bold transition-all ${
                  activeStep === 'form'
                    ? 'bg-teal-700 text-white shadow-sm'
                    : 'bg-slate-50 text-slate-600 hover:bg-slate-100'
                }`}
              >
                <span className="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center text-[10px]">
                  1
                </span>
                <span>Dynamic Application Form</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveStep('documents')}
                className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-xs font-bold transition-all ${
                  activeStep === 'documents'
                    ? 'bg-teal-700 text-white shadow-sm'
                    : 'bg-slate-50 text-slate-600 hover:bg-slate-100'
                }`}
              >
                <span className="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center text-[10px]">
                  2
                </span>
                <span>Upload Documents ({documents.length}/{rawRequiredDocs.length})</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveStep('review')}
                className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-xs font-bold transition-all ${
                  activeStep === 'review'
                    ? 'bg-teal-700 text-white shadow-sm'
                    : 'bg-slate-50 text-slate-600 hover:bg-slate-100'
                }`}
              >
                <span className="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center text-[10px]">
                  3
                </span>
                <span>Review & Submit</span>
              </button>
            </div>

            {/* Step 1: Dynamic Form Engine */}
            {activeStep === 'form' && (
              <div className="space-y-6">
                <DynamicForm
                  schema={rawFormSchema}
                  formData={formData}
                  onChange={(updated) => setFormData(updated)}
                  onSaveDraft={handleSaveDraft}
                  isReadOnly={false}
                />

                <div className="flex items-center justify-end pt-2">
                  <button
                    type="button"
                    onClick={async () => {
                      await handleSaveDraft();
                      setActiveStep('documents');
                    }}
                    className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-teal-700 hover:bg-teal-800 text-white text-xs font-bold shadow-sm transition-all"
                  >
                    <span>Proceed to Document Upload</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* Step 2: Document Ingestion */}
            {activeStep === 'documents' && (
              <div className="space-y-6">
                <DocumentUploadManager
                  applicationId={application.id}
                  requiredDocsConfig={rawRequiredDocs}
                  uploadedDocuments={documents}
                  onRefresh={handleRefreshDocuments}
                  isReadOnly={false}
                />

                <div className="flex items-center justify-between pt-2">
                  <button
                    type="button"
                    onClick={() => setActiveStep('form')}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-white transition-colors"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    Back to Form
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveStep('review')}
                    className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-teal-700 hover:bg-teal-800 text-white text-xs font-bold shadow-sm transition-all"
                  >
                    <span>Proceed to Final Review</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* Step 3: Pre-Submission Review */}
            {activeStep === 'review' && (
              <ApplicationReview
                application={{ ...application, form_data: formData }}
                schemeName={scheme.name}
                schemeCode={scheme.scheme_code}
                schemeVersion={schemeVersionLabel}
                formSchema={rawFormSchema}
                requiredDocsConfig={rawRequiredDocs}
                uploadedDocuments={documents}
                onBackToEdit={() => setActiveStep('form')}
                onSubmit={handleSubmitApplication}
                isSubmitting={submitting}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
};
