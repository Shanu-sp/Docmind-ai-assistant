import React from 'react';
import { FileText, Plus, MessageSquare, Trash2, Sparkles, FileCode, FileSpreadsheet } from 'lucide-react';

export default function Sidebar({
  documents = [],
  activeDocument = null,
  onSelectDocument,
  onNewDocumentClick,
  chatSessions = [],
  activeSession = null,
  onSelectSession,
  onDeleteDocument,
  onDeleteSession,
  aiConfig = null,
  onOpenConfigModal
}) {
  const getFileIcon = (fileType) => {
    const ext = (fileType || '').toLowerCase();
    if (ext === 'pdf') return <FileText className="w-4 h-4 text-rose-400 flex-shrink-0" />;
    if (ext === 'docx') return <FileSpreadsheet className="w-4 h-4 text-blue-400 flex-shrink-0" />;
    return <FileCode className="w-4 h-4 text-emerald-400 flex-shrink-0" />;
  };

  return (
    <aside className="w-72 bg-zinc-950 border-r border-zinc-800/80 flex flex-col h-screen select-none">
      {/* Brand Header */}
      <div className="p-4 border-b border-zinc-800/80 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white font-bold text-sm shadow-md shadow-indigo-500/20">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="font-semibold text-zinc-100 tracking-tight leading-none text-base">DocMind</h1>
            <span className="text-[10px] text-indigo-400 font-medium tracking-wide">AI DOCUMENT WORKSPACE</span>
          </div>
        </div>
      </div>

      {/* New Document Button */}
      <div className="p-3">
        <button
          onClick={onNewDocumentClick}
          className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium py-2.5 px-4 rounded-xl transition-all shadow-lg shadow-indigo-600/20 active:scale-[0.98]"
        >
          <Plus className="w-4 h-4" />
          <span>Upload Document</span>
        </button>
      </div>

      {/* Documents & Sessions Scroll Area */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-6">
        {/* Documents Section */}
        <div>
          <div className="text-[11px] font-semibold text-zinc-400 px-2 pb-2 uppercase tracking-wider flex items-center justify-between">
            <span>Documents ({documents.length})</span>
          </div>

          {documents.length === 0 ? (
            <p className="text-xs text-zinc-400 px-2 py-3 italic">No documents uploaded yet.</p>
          ) : (
            <div className="space-y-1">
              {documents.map((doc) => {
                const isActive = activeDocument && activeDocument.id === doc.id;
                return (
                  <div
                    key={doc.id}
                    onClick={() => onSelectDocument(doc)}
                    className={`group flex items-center justify-between px-2.5 py-2 text-xs rounded-xl cursor-pointer transition-all ${
                      isActive
                        ? 'bg-zinc-800/90 text-zinc-100 font-medium border border-zinc-700/60 shadow-sm'
                        : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/80'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0 pr-2">
                      {getFileIcon(doc.file_type)}
                      <span className="truncate">{doc.title}</span>
                    </div>

                    {onDeleteDocument && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteDocument(doc.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1 hover:text-rose-400 text-zinc-400 transition-opacity rounded-md hover:bg-zinc-700/50"
                        title="Delete Document"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Chat Sessions Section */}
        <div>
          <div className="text-[11px] font-semibold text-zinc-400 px-2 pb-2 uppercase tracking-wider">
            <span>Chat Sessions ({chatSessions.length})</span>
          </div>

          {chatSessions.length === 0 ? (
            <p className="text-xs text-zinc-400 px-2 py-3 italic">No active conversations.</p>
          ) : (
            <div className="space-y-1">
              {chatSessions.map((session) => {
                const isActive = activeSession && activeSession.id === session.id;
                return (
                  <div
                    key={session.id}
                    onClick={() => onSelectSession(session)}
                    className={`group flex items-center justify-between px-2.5 py-2 text-xs rounded-xl cursor-pointer transition-all ${
                      isActive
                        ? 'bg-indigo-600/15 text-indigo-300 font-medium border border-indigo-500/30'
                        : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/80'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0 pr-2">
                      <MessageSquare className={`w-3.5 h-3.5 flex-shrink-0 ${isActive ? 'text-indigo-400' : 'text-zinc-400'}`} />
                      <span className="truncate">{session.title}</span>
                    </div>

                    {onDeleteSession && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteSession(session.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1 hover:text-rose-400 text-zinc-400 transition-opacity rounded-md hover:bg-zinc-700/50"
                        title="Delete Chat Session"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* AI Key Status Footer */}
      <div className="p-3 border-t border-zinc-800/80 bg-zinc-950">
        <button
          onClick={onOpenConfigModal}
          className="w-full flex items-center justify-between p-2.5 bg-zinc-900/80 hover:bg-zinc-800/80 border border-zinc-800 rounded-xl text-xs transition-colors"
        >
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${aiConfig?.has_api_key ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
            <span className="text-zinc-300 font-medium">{aiConfig?.has_api_key ? 'Gemini 2.5 Flash' : 'Demo Mode'}</span>
          </div>
          <span className="text-[10px] text-indigo-400 font-medium">Config Key</span>
        </button>
      </div>
    </aside>
  );
}

