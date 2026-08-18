import React, { useState } from 'react';
import { FileText, Sparkles, HelpCircle, Eye, AlignLeft, HardDrive, RotateCw, Loader2, Send } from 'lucide-react';

export default function DocumentViewer({ document: doc, onPromptChipClick, onReanalyzeDocument }) {
  const [activeTab, setActiveTab] = useState('summary'); // 'summary' | 'text' | 'preview'
  const [focusInput, setFocusInput] = useState('');
  const [showFocusInput, setShowFocusInput] = useState(false);
  const [reanalyzing, setReanalyzing] = useState(false);

  if (!doc) {
    return (
      <div className="flex-1 bg-zinc-950 flex flex-col items-center justify-center p-8 text-center border-r border-zinc-800/80">
        <div className="w-16 h-16 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center mb-4 text-zinc-500 shadow-inner">
          <FileText className="w-8 h-8 text-indigo-400/80" />
        </div>
        <h3 className="text-lg font-semibold text-zinc-200 mb-1">No Document Selected</h3>
        <p className="text-xs text-zinc-500 max-w-sm">
          Select an uploaded document from the sidebar or upload a new file to analyze text, view summaries, and chat with AI.
        </p>
      </div>
    );
  }

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const getMediaUrl = (filePath) => {
    if (!filePath) return '';
    const baseApi = import.meta.env.VITE_API_BASE_URL || 'https://docmind-ai-assistant-backend.onrender.com/api';
    const baseUrl = baseApi.replace(/\/api\/?$/, '');
    return `${baseUrl}${filePath}`;
  };

  const handleReanalyzeSubmit = async (e) => {
    e?.preventDefault();
    if (reanalyzing || !onReanalyzeDocument) return;
    setReanalyzing(true);
    try {
      await onReanalyzeDocument(doc.id, focusInput.trim() || null);
      setShowFocusInput(false);
      setFocusInput('');
    } catch (err) {
      console.error(err);
    } finally {
      setReanalyzing(false);
    }
  };

  return (
    <div className="flex-1 bg-zinc-950 flex flex-col h-screen border-r border-zinc-800/80 overflow-hidden">
      {/* Header Bar */}
      <div className="h-16 border-b border-zinc-800/80 px-6 flex items-center justify-between bg-zinc-900/40 backdrop-blur-md">
        <div className="flex items-center gap-3 min-w-0 pr-4">
          <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <FileText className="w-5 h-5 flex-shrink-0" />
          </div>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-zinc-100 truncate">{doc.title}</h2>
            <div className="flex items-center gap-2 text-[11px] text-zinc-400 mt-0.5">
              <span className="uppercase font-semibold text-indigo-400 px-1.5 py-0.2 bg-indigo-500/10 rounded">
                {doc.file_type}
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <HardDrive className="w-3 h-3 text-zinc-400" />
                {formatFileSize(doc.file_size)}
              </span>
            </div>
          </div>
        </div>

        {/* View Tabs & Action */}
        <div className="flex items-center gap-2">
          <div className="flex bg-zinc-900 p-1 rounded-xl border border-zinc-800 text-xs font-medium">
            <button
              onClick={() => setActiveTab('summary')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                activeTab === 'summary'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>AI Insights</span>
            </button>
            <button
              onClick={() => setActiveTab('text')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                activeTab === 'text'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <AlignLeft className="w-3.5 h-3.5" />
              <span>Extracted Text</span>
            </button>
            {doc.file_type === 'pdf' && (
              <button
                onClick={() => setActiveTab('preview')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                  activeTab === 'preview'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                <Eye className="w-3.5 h-3.5" />
                <span>PDF Preview</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Content Body */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {activeTab === 'summary' && (
          <div className="space-y-6 max-w-3xl">
            {/* Executive Summary Card */}
            <div className="p-5 bg-gradient-to-b from-zinc-900/90 to-zinc-900/40 border border-zinc-800 rounded-2xl shadow-lg">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-indigo-400">
                  <Sparkles className="w-4 h-4 text-indigo-400" />
                  <span>Executive Summary</span>
                </div>

                <button
                  onClick={() => setShowFocusInput(!showFocusInput)}
                  className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-indigo-300 bg-zinc-800/80 px-2.5 py-1 rounded-lg border border-zinc-700/60 transition-colors"
                >
                  <RotateCw className="w-3 h-3" />
                  <span>Custom Summary Focus</span>
                </button>
              </div>

              {showFocusInput && (
                <form onSubmit={handleReanalyzeSubmit} className="mb-4 flex gap-2">
                  <input
                    type="text"
                    value={focusInput}
                    onChange={(e) => setFocusInput(e.target.value)}
                    placeholder="E.g., financial metrics, risks, key dates..."
                    className="flex-1 bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-1.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
                  />
                  <button
                    type="submit"
                    disabled={reanalyzing}
                    className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-medium transition-colors flex items-center gap-1"
                  >
                    {reanalyzing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
                    <span>Generate</span>
                  </button>
                </form>
              )}

              {reanalyzing ? (
                <div className="py-8 flex flex-col items-center justify-center space-y-2 text-zinc-400">
                  <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
                  <p className="text-xs">Regenerating summary insights with Gemini AI...</p>
                </div>
              ) : doc.executive_summary && doc.executive_summary.length > 0 ? (
                <ul className="space-y-3">
                  {doc.executive_summary.map((point, index) => (
                    <li key={index} className="flex items-start gap-3 text-sm text-zinc-300 leading-relaxed">
                      <span className="flex-shrink-0 w-5 h-5 rounded-full bg-indigo-500/10 text-indigo-400 text-xs font-semibold flex items-center justify-center border border-indigo-500/20 mt-0.5">
                        {index + 1}
                      </span>
                      <span>{point}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-zinc-500 italic">No summary generated for this document yet.</p>
              )}
            </div>

            {/* Dynamic Suggested Action Chips */}
            {doc.suggested_questions && doc.suggested_questions.length > 0 && (
              <div className="p-5 bg-zinc-900/50 border border-zinc-800 rounded-2xl">
                <div className="flex items-center gap-2 mb-3 text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  <HelpCircle className="w-4 h-4 text-indigo-400" />
                  <span>Suggested Prompts to Ask</span>
                </div>

                <div className="flex flex-wrap gap-2">
                  {doc.suggested_questions.map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() => onPromptChipClick && onPromptChipClick(q)}
                      className="px-3.5 py-2 text-xs text-left bg-zinc-800/80 hover:bg-indigo-600/20 hover:text-indigo-300 hover:border-indigo-500/40 border border-zinc-700/60 rounded-xl text-zinc-300 transition-all active:scale-[0.98] shadow-sm flex items-center gap-2"
                    >
                      <Sparkles className="w-3 h-3 text-indigo-400 flex-shrink-0" />
                      <span>{q}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'text' && (
          <div className="p-5 bg-zinc-900/60 border border-zinc-800 rounded-2xl max-w-3xl">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-3">Extracted Plain Text</h3>
            <pre className="text-xs text-zinc-300 leading-relaxed whitespace-pre-wrap font-mono bg-zinc-950/60 p-4 rounded-xl border border-zinc-800 max-h-[600px] overflow-y-auto">
              {doc.extracted_text || 'No text extracted.'}
            </pre>
          </div>
        )}

        {activeTab === 'preview' && doc.file_type === 'pdf' && (
          <div className="w-full h-[650px] bg-zinc-900 rounded-2xl overflow-hidden border border-zinc-800 flex flex-col">
            <iframe
              src={getMediaUrl(doc.file)}
              title="PDF Preview"
              className="w-full h-full border-none"
            />
          </div>
        )}
      </div>
    </div>
  );
}
