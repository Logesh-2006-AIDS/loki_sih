import React, { useState, useEffect } from 'react';
import { X, Download, Loader2 } from 'lucide-react';
import { officerService } from '../../services/officerService';

interface DocumentPreviewModalProps {
  documentId: string;
  originalFilename: string;
  mimeType: string;
  isOpen: boolean;
  onClose: () => void;
}

export const DocumentPreviewModal: React.FC<DocumentPreviewModalProps> = ({
  documentId,
  originalFilename,
  mimeType,
  isOpen,
  onClose,
}) => {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && documentId) {
      setLoading(true);
      setError(null);
      officerService
        .getDocumentPreviewUrl(documentId)
        .then((url) => {
          setBlobUrl(url);
          setLoading(false);
        })
        .catch((err) => {
          console.error('Failed to load document preview', err);
          setError('Failed to load document preview. You can still download the file directly.');
          setLoading(false);
        });
    }

    return () => {
      if (blobUrl) {
        window.URL.revokeObjectURL(blobUrl);
      }
    };
  }, [isOpen, documentId]);

  if (!isOpen) return null;

  const handleDownload = () => {
    officerService.downloadDocument(documentId, originalFilename);
  };

  const isPdf = mimeType.includes('pdf');
  const isImage = mimeType.includes('image');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/75 backdrop-blur-xs p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-5xl h-[90vh] flex flex-col overflow-hidden border border-slate-300 animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="bg-slate-900 text-white px-5 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-2.5 truncate">
            <h3 className="font-semibold text-sm truncate" title={originalFilename}>
              Preview: {originalFilename}
            </h3>
            <span className="text-xs text-slate-400 font-mono hidden sm:inline">
              ({mimeType})
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleDownload}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-teal-600 hover:bg-teal-500 text-white transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              Download Original
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 bg-slate-100 relative overflow-hidden flex items-center justify-center">
          {loading && (
            <div className="flex flex-col items-center gap-2 text-slate-600">
              <Loader2 className="w-8 h-8 animate-spin text-teal-600" />
              <p className="text-sm font-medium">Fetching original document stream...</p>
            </div>
          )}

          {error && (
            <div className="p-6 text-center max-w-md">
              <p className="text-sm text-rose-600 mb-4">{error}</p>
              <button
                onClick={handleDownload}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-teal-700 text-white hover:bg-teal-800"
              >
                Download File
              </button>
            </div>
          )}

          {!loading && !error && blobUrl && (
            <>
              {isPdf ? (
                <iframe
                  src={blobUrl}
                  title={originalFilename}
                  className="w-full h-full border-0"
                />
              ) : isImage ? (
                <div className="overflow-auto max-h-full p-4 flex items-center justify-center">
                  <img
                    src={blobUrl}
                    alt={originalFilename}
                    className="max-h-[80vh] object-contain rounded shadow"
                  />
                </div>
              ) : (
                <div className="p-8 text-center">
                  <p className="text-sm text-slate-600 mb-3">
                    Browser preview not available for MIME type <strong>{mimeType}</strong>.
                  </p>
                  <button
                    onClick={handleDownload}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-teal-700 text-white hover:bg-teal-800"
                  >
                    <Download className="w-4 h-4" /> Download to View
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};
