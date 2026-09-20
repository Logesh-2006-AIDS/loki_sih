import React, { useState, useRef } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Upload,
  FileText,
  Clock,
  MessageSquare,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import { PublicDeficiencyItem } from '../../types/deficiency';

interface DeficiencyCardProps {
  deficiency: PublicDeficiencyItem;
  onUploadReplacement: (deficiencyId: string, file: File, remarks?: string) => Promise<void>;
}

export const DeficiencyCard: React.FC<DeficiencyCardProps> = ({
  deficiency,
  onUploadReplacement,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [remarks, setRemarks] = useState(deficiency.applicant_remarks || '');
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isUploaded = deficiency.status === 'REPLACEMENT_UPLOADED';
  const isUnderReview = deficiency.status === 'UNDER_REVIEW';
  const isResolved = deficiency.status === 'RESOLVED';

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.size > 5 * 1024 * 1024) {
        setErrorMessage('File size exceeds maximum allowed 5 MB.');
        return;
      }
      setSelectedFile(file);
      setErrorMessage(null);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setErrorMessage('Please select a file to upload.');
      return;
    }

    setIsUploading(true);
    setErrorMessage(null);
    try {
      await onUploadReplacement(deficiency.id, selectedFile, remarks.trim() || undefined);
      setSelectedFile(null);
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? ((err as { response: { data: { error?: string } } }).response.data?.error || 'Failed to upload replacement.')
          : 'Failed to upload replacement.';
      setErrorMessage(msg);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div
      className={`rounded-xl border p-5 sm:p-6 transition-all backdrop-blur-sm ${
        isResolved
          ? 'bg-emerald-950/20 border-emerald-500/30'
          : isUploaded
          ? 'bg-blue-950/20 border-blue-500/40'
          : isUnderReview
          ? 'bg-purple-950/20 border-purple-500/30'
          : 'bg-slate-900/60 border-amber-500/30 shadow-lg shadow-amber-500/5'
      }`}
    >
      {/* Header with Document Label & Status Badge */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div
            className={`p-2.5 rounded-lg ${
              isResolved
                ? 'bg-emerald-500/20 text-emerald-400'
                : isUploaded
                ? 'bg-blue-500/20 text-blue-400'
                : 'bg-amber-500/20 text-amber-400'
            }`}
          >
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base sm:text-lg font-semibold text-white">
                {deficiency.document_name}
              </h3>
              {deficiency.cycle > 1 && (
                <span className="px-2 py-0.5 text-xs font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded-full">
                  Cycle {deficiency.cycle}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Target Document Code:{' '}
              <span className="font-mono text-slate-300">{deficiency.document_type}</span>
            </p>
          </div>
        </div>

        {/* State Badge */}
        <div>
          {isResolved ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-xs font-medium rounded-full">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Verified & Resolved
            </span>
          ) : isUnderReview ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-purple-500/20 text-purple-300 border border-purple-500/40 text-xs font-medium rounded-full">
              <Clock className="w-3.5 h-3.5" />
              Under Scrutiny Review
            </span>
          ) : isUploaded ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-500/20 text-blue-300 border border-blue-500/40 text-xs font-medium rounded-full">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Replacement Ready
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-amber-500/20 text-amber-300 border border-amber-500/40 text-xs font-medium rounded-full">
              <AlertCircle className="w-3.5 h-3.5" />
              Action Required
            </span>
          )}
        </div>
      </div>

      {/* Officer Remarks & Instructions */}
      <div className="mt-4 p-4 rounded-lg bg-slate-800/60 border border-slate-700/60">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="text-xs uppercase tracking-wider font-semibold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
            {deficiency.reason.replace(/_/g, ' ')}
          </span>
          <span className="text-xs text-slate-400">Officer Instructions</span>
        </div>
        <p className="text-sm text-slate-200 leading-relaxed font-sans mt-2">
          {deficiency.applicant_message}
        </p>
      </div>

      {/* Upload Form or Uploaded Status Banner */}
      <div className="mt-5">
        {isUploaded ? (
          <div className="bg-blue-950/30 border border-blue-500/30 rounded-lg p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-500/20 rounded-md text-blue-300">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <p className="text-sm font-medium text-blue-200">
                  Replacement Document Uploaded
                </p>
                <p className="text-xs text-slate-400 mt-0.5">
                  Uploaded on{' '}
                  {deficiency.replacement_uploaded_at
                    ? new Date(deficiency.replacement_uploaded_at).toLocaleString()
                    : 'recently'}
                  {deficiency.applicant_remarks && (
                    <span className="block italic mt-0.5 text-slate-300">
                      &ldquo;{deficiency.applicant_remarks}&rdquo;
                    </span>
                  )}
                </p>
              </div>
            </div>

            {/* Allow Re-upload prior to resubmission */}
            <button
              type="button"
              onClick={() => setSelectedFile(null)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition-colors border border-slate-700"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Re-upload another file
            </button>
          </div>
        ) : isUnderReview || isResolved ? (
          <div className="text-xs text-slate-400 italic">
            This deficiency is currently being evaluated during scrutiny.
          </div>
        ) : null}

        {/* Upload Form (Shown if OPEN or if applicant wants to supersede replacement) */}
        {(!isUploaded || selectedFile) && !isUnderReview && !isResolved && (
          <form onSubmit={handleUploadSubmit} className="mt-4 space-y-4">
            {/* File Dropzone */}
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-slate-700 hover:border-amber-500/60 rounded-xl p-6 text-center cursor-pointer bg-slate-950/40 hover:bg-slate-900/60 transition-all group"
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept=".pdf,.png,.jpg,.jpeg"
                className="hidden"
              />
              <div className="w-10 h-10 mx-auto rounded-full bg-slate-800 group-hover:bg-amber-500/20 flex items-center justify-center text-slate-400 group-hover:text-amber-400 transition-colors">
                <Upload className="w-5 h-5" />
              </div>
              <div className="mt-3">
                {selectedFile ? (
                  <div className="flex items-center justify-center gap-2 text-sm font-medium text-amber-300">
                    <FileText className="w-4 h-4" />
                    {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                  </div>
                ) : (
                  <>
                    <p className="text-sm font-medium text-slate-200">
                      Click to choose replacement file or drag &amp; drop
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      Allowed: PDF, JPG, PNG (Max size: 5 MB)
                    </p>
                  </>
                )}
              </div>
            </div>

            {/* Applicant Remarks Input */}
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1 flex items-center gap-1.5">
                <MessageSquare className="w-3.5 h-3.5 text-slate-400" />
                Applicant Remarks / Explanation (Optional)
              </label>
              <textarea
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                placeholder="Explain the changes made in this replacement (e.g. Attached FY 2023-24 income certificate with legible official seal)..."
                rows={2}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-amber-500/60 placeholder:text-slate-600 resize-none"
              />
            </div>

            {errorMessage && (
              <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-xs text-red-300 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
                <span>{errorMessage}</span>
              </div>
            )}

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={!selectedFile || isUploading}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-amber-500 hover:bg-amber-400 disabled:opacity-50 disabled:cursor-not-allowed text-slate-950 font-semibold text-sm rounded-lg transition-colors shadow-md shadow-amber-500/20"
              >
                {isUploading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Uploading Replacement...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    Save Replacement Document
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
