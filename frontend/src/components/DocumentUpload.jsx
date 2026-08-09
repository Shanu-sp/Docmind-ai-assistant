import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, CheckCircle2, AlertCircle, Loader2, FileCode, FileSpreadsheet } from 'lucide-react';
import { uploadDocument } from '../services/api';

export default function DocumentUpload({ onUploadSuccess }) {
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileChange = async (file) => {
    if (!file) return;

    // Extension Check
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['pdf', 'docx', 'txt'].includes(ext)) {
      setError(`Unsupported file type '.${ext}'. Please upload a PDF, DOCX, or TXT document.`);
      return;
    }

    // Size check (25MB)
    if (file.size > 25 * 1024 * 1024) {
      setError("File size exceeds maximum limit of 25MB.");
      return;
    }

    setError(null);
    setLoading(true);
    setStatusMessage('Uploading document & extracting text...');

    try {
      const newDoc = await uploadDocument(file);
      setStatusMessage('Document uploaded and AI insights generated!');
      setTimeout(() => {
        setLoading(false);
        if (onUploadSuccess) onUploadSuccess(newDoc);
      }, 500);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || err.response?.data?.file?.[0] || 'Failed to upload document.');
      setLoading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="w-full max-w-xl mx-auto p-6 bg-zinc-900/60 border border-zinc-800 rounded-2xl backdrop-blur-md shadow-xl">
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`relative flex flex-col items-center justify-center p-8 border-2 border-dashed rounded-xl cursor-pointer transition-all duration-200 ${
          isDragging
            ? 'border-indigo-500 bg-indigo-500/10 scale-[1.01]'
            : 'border-zinc-700 hover:border-indigo-400 bg-zinc-950/40 hover:bg-zinc-900/40'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleFileChange(e.target.files[0])}
        />

        {loading ? (
          <div className="flex flex-col items-center space-y-3">
            <Loader2 className="w-10 h-10 text-indigo-400 animate-spin" />
            <p className="text-sm font-medium text-zinc-200">{statusMessage}</p>
            <p className="text-xs text-zinc-400">Parsing document structure and running Gemini AI extraction...</p>
          </div>
        ) : (
          <div className="flex flex-col items-center text-center space-y-3">
            <div className="p-4 bg-indigo-500/10 text-indigo-400 rounded-full border border-indigo-500/20">
              <UploadCloud className="w-8 h-8" />
            </div>
            <div>
              <p className="text-base font-semibold text-zinc-100">
                Click to upload or drag & drop
              </p>
              <p className="text-xs text-zinc-400 mt-1">
                Supports PDF, DOCX, and TXT files (Max 25MB)
              </p>
            </div>
            <div className="flex items-center gap-3 pt-2">
              <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2.5 py-1 bg-zinc-800 text-zinc-300 rounded-md">
                <FileText className="w-3.5 h-3.5 text-rose-400" /> PDF
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2.5 py-1 bg-zinc-800 text-zinc-300 rounded-md">
                <FileSpreadsheet className="w-3.5 h-3.5 text-blue-400" /> DOCX
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2.5 py-1 bg-zinc-800 text-zinc-300 rounded-md">
                <FileCode className="w-3.5 h-3.5 text-emerald-400" /> TXT
              </span>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-4 p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg flex items-center gap-2 text-rose-300 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
