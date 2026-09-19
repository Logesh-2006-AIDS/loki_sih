import React, { useState } from 'react';
import {
  FileCheck2,
  AlertCircle,
  Trash2,
  Download,
  UploadCloud,
  CheckCircle2,
  FileText,
  AlertTriangle,
} from 'lucide-react';
import { RequiredDocumentConfig, DocumentItem } from '../types/application';
import { applicationService } from '../services/applicationService';

interface Props {
  applicationId: string;
  requiredDocsConfig: RequiredDocumentConfig[];
  uploadedDocuments: DocumentItem[];
  onRefresh: () => Promise<void>;
  isReadOnly?: boolean;
}

export const DocumentUploadManager: React.FC<Props> = ({
  applicationId,
  requiredDocsConfig,
  uploadedDocuments,
  onRefresh,
  isReadOnly = false,
}) => {
  const [uploadingCode, setUploadingCode] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [errorMap, setErrorMap] = useState<Record<string, string>>({});

  const formatFileSize = (bytes: number): string => {
    if (!bytes) return '0 KB';
    const mb = bytes / (1024 * 1024);
    if (mb >= 1) return `${mb.toFixed(2)} MB`;
    return `${(bytes / 1024).toFixed(1)} KB`;
  };

  const handleFileUpload = async (
    docCode: string,
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Reset error for this document
    setErrorMap((prev) => ({ ...prev, [docCode]: '' }));

    // Client-side quick check
    if (file.size > 5 * 1024 * 1024) {
      setErrorMap((prev) => ({
        ...prev,
        [docCode]: 'File exceeds maximum allowed size of 5 MB.',
      }));
      e.target.value = '';
      return;
    }

    try {
      setUploadingCode(docCode);
      await applicationService.uploadDocument(applicationId, docCode, file);
      await onRefresh();
    } catch (err: any) {
      console.error('Document upload failed', err);
      setErrorMap((prev) => ({
        ...prev,
        [docCode]:
          err.response?.data?.error ||
          'Failed to upload document. Please check file format and signature.',
      }));
    } finally {
      setUploadingCode(null);
      e.target.value = '';
    }
  };

  const handleDelete = async (docId: string) => {
    if (isReadOnly) return;
    if (!window.confirm('Are you sure you want to remove this uploaded document?')) {
      return;
    }

    try {
      setDeletingId(docId);
      await applicationService.deleteDocument(docId);
      await onRefresh();
    } catch (err: any) {
      console.error('Delete failed', err);
      alert(err.response?.data?.error || 'Failed to delete document.');
    } finally {
      setDeletingId(null);
    }
  };

  const handleDownload = async (doc: DocumentItem) => {
    try {
      await applicationService.downloadDocument(doc.id, doc.original_filename);
    } catch (err) {
      console.error('Download failed', err);
      alert('Unable to download file from storage.');
    }
  };

  const uploadedCodes = new Set(uploadedDocuments.map((d) => d.document_type));
  const uploadedCount = requiredDocsConfig.filter((d) =>
    uploadedCodes.has(d.code || d.type || '')
  ).length;

  return (
    <div className="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-sm space-y-6">
      {/* Header & Status */}
      <div className="border-b border-slate-100 pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-teal-700 bg-teal-50 px-2 py-0.5 rounded">
              Document Checklist
            </span>
            <span className="text-xs text-slate-500">
              {uploadedCount} of {requiredDocsConfig.length} uploaded
            </span>
          </div>
          <h3 className="text-base font-bold text-slate-900 mt-1">
            Mandatory & Supporting Document Ingestion
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Uploaded files are stored securely and validated against genuine magic-byte signatures.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {uploadedCount === requiredDocsConfig.length ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-800 text-xs font-bold border border-emerald-200">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              Checklist Complete
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-50 text-amber-900 text-xs font-semibold border border-amber-200">
              <AlertTriangle className="w-4 h-4 text-amber-700" />
              {requiredDocsConfig.length - uploadedCount} Document(s) Pending
            </span>
          )}
        </div>
      </div>

      {/* Document Items List */}
      <div className="space-y-4">
        {requiredDocsConfig.map((config) => {
          const docCode = config.code || config.type || '';
          const docLabel = config.name || config.label || docCode;
          const uploadedDoc = uploadedDocuments.find(
            (d) => d.document_type === docCode
          );
          const isUploading = uploadingCode === docCode;
          const errorMessage = errorMap[docCode];

          return (
            <div
              key={docCode}
              className={`p-4 sm:p-5 rounded-xl border transition-all ${
                uploadedDoc
                  ? 'bg-emerald-50/20 border-emerald-200'
                  : 'bg-slate-50/60 border-slate-200'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div
                    className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 font-bold ${
                      uploadedDoc
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-slate-200 text-slate-600'
                    }`}
                  >
                    {uploadedDoc ? (
                      <FileCheck2 className="w-5 h-5 text-emerald-700" />
                    ) : (
                      <FileText className="w-5 h-5 text-slate-500" />
                    )}
                  </div>

                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <h4 className="text-xs sm:text-sm font-bold text-slate-900">
                        {docLabel}
                      </h4>
                      {config.required ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">
                          REQUIRED
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-200 text-slate-600">
                          OPTIONAL
                        </span>
                      )}
                      <span className="text-[10px] font-mono text-slate-400">
                        ({docCode})
                      </span>
                    </div>

                    {uploadedDoc ? (
                      <div className="text-[11px] text-slate-500 mt-1 flex items-center gap-3 flex-wrap">
                        <span className="font-semibold text-slate-700">
                          {uploadedDoc.original_filename}
                        </span>
                        <span>Size: {formatFileSize(uploadedDoc.file_size)}</span>
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-100 text-emerald-800">
                          {uploadedDoc.status}
                        </span>
                      </div>
                    ) : (
                      <p className="text-[11px] text-slate-400 mt-1">
                        Allowed formats: {(config.allowed_extensions || ['.pdf', '.jpg', '.png']).join(', ')} • Max: 5 MB
                      </p>
                    )}

                    {errorMessage && (
                      <div className="mt-2 text-[11px] text-red-700 bg-red-50 p-2 rounded-lg border border-red-200 flex items-center gap-1.5">
                        <AlertCircle className="w-3.5 h-3.5 shrink-0 text-red-600" />
                        <span>{errorMessage}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                  {uploadedDoc ? (
                    <>
                      <button
                        type="button"
                        onClick={() => handleDownload(uploadedDoc)}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-white transition-colors shadow-sm"
                      >
                        <Download className="w-3.5 h-3.5 text-slate-500" />
                        Download
                      </button>

                      {!isReadOnly && (
                        <button
                          type="button"
                          onClick={() => handleDelete(uploadedDoc.id)}
                          disabled={deletingId === uploadedDoc.id}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-red-200 bg-red-50 text-xs font-semibold text-red-700 hover:bg-red-100 transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          {deletingId === uploadedDoc.id ? 'Deleting...' : 'Delete'}
                        </button>
                      )}
                    </>
                  ) : (
                    !isReadOnly && (
                      <label className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-teal-700 hover:bg-teal-800 text-white text-xs font-bold transition-all cursor-pointer shadow-sm">
                        <UploadCloud className="w-4 h-4" />
                        <span>{isUploading ? 'Uploading...' : 'Upload File'}</span>
                        <input
                          type="file"
                          disabled={isUploading}
                          accept={(config.allowed_extensions || ['.pdf', '.jpg', '.jpeg', '.png']).join(',')}
                          onChange={(e) => handleFileUpload(docCode, e)}
                          className="hidden"
                        />
                      </label>
                    )
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
