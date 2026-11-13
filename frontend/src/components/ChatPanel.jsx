import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Loader2, Sparkles, Copy, BookOpen, ExternalLink } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function ChatPanel({
  activeSession,
  messages = [],
  onSendMessage,
  onCitationClick,
  sending = false,
  initialPrompt = '',
  documentTitle = ''
}) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (initialPrompt) {
      setInput(initialPrompt);
    }
  }, [initialPrompt]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!input.trim() || sending) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Converts in-text citation patterns like [Source 1 (Page 2)] into markdown links
  // which will be rendered as interactive clickable citation pill badges.
  const formatMessageContentWithCitations = (content) => {
    if (!content) return '';
    return content
      .replace(/\[Source\s+(\d+)\s*\((?:Page\s*)?(\d+)\)\]/gi, '[$1 · p.$2](#jump-page-$2)')
      .replace(/\[Source\s+(\d+)\]/gi, '[$1](#jump-source-$1)');
  };

  return (
    <div className="w-full lg:w-[380px] xl:w-[420px] bg-zinc-950 flex flex-col h-full lg:h-screen lg:border-l border-zinc-800/80">
      {/* Chat Session Header */}
      <div className="h-16 border-b border-zinc-800/80 px-4 sm:px-5 flex items-center justify-between bg-zinc-900/40 backdrop-blur-md flex-shrink-0">
        <div className="flex items-center gap-2.5 min-w-0">
          <img
            src="/logo.png"
            alt="DocMind Logo"
            className="w-8 h-8 rounded-xl object-cover border border-zinc-700/60 shadow-sm flex-shrink-0"
          />
          <div className="min-w-0">
            <h2 className="text-xs font-semibold text-zinc-100 truncate">
              {activeSession ? activeSession.title : 'DocMind AI Assistant'}
            </h2>
            <p className="text-[10px] text-zinc-400 truncate">
              {documentTitle ? `Context: ${documentTitle}` : 'Context-aware Q&A'}
            </p>
          </div>
        </div>
      </div>

      {/* Message History Stream */}
      <div className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-zinc-500 space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center">
              <Sparkles className="w-6 h-6" />
            </div>
            <h4 className="text-sm font-medium text-zinc-300">Ask DocMind Anything</h4>
            <p className="text-xs text-zinc-500 max-w-xs leading-relaxed">
              Ask questions about key findings, request summaries, or clarify technical terms from your document.
            </p>
            <div className="flex flex-col gap-2 pt-2 w-full max-w-xs">
              <button
                onClick={() => onSendMessage && onSendMessage("Summarize the key points of this document.")}
                className="text-xs text-left p-2.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 rounded-xl text-zinc-300 transition-colors flex items-center gap-2"
              >
                <Sparkles className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
                <span>Summarize key points</span>
              </button>
              <button
                onClick={() => onSendMessage && onSendMessage("What are the main action items or recommendations?")}
                className="text-xs text-left p-2.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 rounded-xl text-zinc-300 transition-colors flex items-center gap-2"
              >
                <Sparkles className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
                <span>List main action items</span>
              </button>
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => {
            const isUser = msg.sender === 'user';
            return (
              <div
                key={idx}
                className={`flex gap-3 text-xs ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
              >
                <div
                  className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 text-white ${
                    isUser
                      ? 'bg-zinc-800 text-zinc-300 border border-zinc-700'
                      : 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
                  }`}
                >
                  {isUser ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
                </div>

                <div
                  className={`relative group rounded-2xl p-3.5 max-w-[85%] leading-relaxed ${
                    isUser
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/10'
                      : 'bg-zinc-900 border border-zinc-800 text-zinc-200 shadow-sm'
                  }`}
                >
                  {isUser ? (
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  ) : (
                    <>
                      <div className="prose prose-invert prose-xs max-w-none space-y-2 select-text">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            a: ({ href, children, ...props }) => {
                              if (href && href.startsWith('#jump-page-')) {
                                const pageNum = parseInt(href.replace('#jump-page-', ''), 10);
                                return (
                                  <button
                                    type="button"
                                    onClick={(e) => {
                                      e.preventDefault();
                                      onCitationClick && onCitationClick({ page: pageNum });
                                    }}
                                    className="inline-flex items-center gap-1 px-1.5 py-0.5 mx-0.5 text-[11px] font-semibold text-emerald-300 bg-emerald-950/80 hover:bg-emerald-900 border border-emerald-700/60 rounded cursor-pointer transition-all active:scale-95 shadow-sm align-baseline"
                                    title={`Click to jump to Page ${pageNum}`}
                                  >
                                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                                    <span>{children}</span>
                                  </button>
                                );
                              }
                              return (
                                <a
                                  href={href}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-indigo-400 hover:underline"
                                  {...props}
                                >
                                  {children}
                                </a>
                              );
                            }
                          }}
                        >
                          {formatMessageContentWithCitations(msg.content)}
                        </ReactMarkdown>
                      </div>

                      {/* Referenced Sources Pill Bar */}
                      {msg.citations && Array.isArray(msg.citations) && msg.citations.length > 0 && (
                        <div className="mt-3 pt-2.5 border-t border-zinc-800/80">
                          <div className="flex items-center justify-between gap-1 mb-2">
                            <div className="flex items-center gap-1.5 text-[11px] font-medium text-zinc-400">
                              <BookOpen className="w-3.5 h-3.5 text-emerald-400" />
                              <span>Referenced Sources ({msg.citations.length})</span>
                            </div>
                          </div>
                          <div className="flex flex-wrap gap-1.5">
                            {msg.citations.map((citation, cIdx) => (
                              <button
                                key={cIdx}
                                type="button"
                                onClick={() =>
                                  onCitationClick &&
                                  onCitationClick({
                                    page: citation.page_number,
                                    sourceId: citation.source_id,
                                    chunkId: citation.chunk_id
                                  })
                                }
                                className="group/pill inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium text-emerald-300 bg-emerald-950/40 hover:bg-emerald-900/70 border border-emerald-800/50 hover:border-emerald-600/70 rounded-lg transition-all text-left cursor-pointer active:scale-95 shadow-sm"
                                title={
                                  citation.snippet
                                    ? `Page ${citation.page_number || 'N/A'}: ${citation.snippet}`
                                    : `Source ${citation.source_id}`
                                }
                              >
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 group-hover/pill:scale-125 transition-transform flex-shrink-0" />
                                <span className="font-semibold text-emerald-200">
                                  {citation.page_number ? `p. ${citation.page_number}` : `Source ${citation.source_id}`}
                                </span>
                                {citation.snippet && (
                                  <span className="text-[10px] text-zinc-400 truncate max-w-[130px] group-hover/pill:text-zinc-200">
                                    {citation.snippet.replace(/\n+/g, ' ')}
                                  </span>
                                )}
                                <ExternalLink className="w-2.5 h-2.5 text-emerald-500/70 group-hover/pill:text-emerald-300 flex-shrink-0 ml-0.5" />
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      <button
                        onClick={() => navigator.clipboard.writeText(msg.content)}
                        className="opacity-0 group-hover:opacity-100 absolute top-2 right-2 p-1 text-zinc-400 hover:text-indigo-400 bg-zinc-950/80 rounded-md border border-zinc-800 transition-opacity"
                        title="Copy message"
                      >
                        <Copy className="w-3 h-3" />
                      </button>
                    </>
                  )}
                </div>
              </div>
            );
          })
        )}

        {sending && (
          <div className="flex gap-3 text-xs">
            <div className="w-7 h-7 rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center flex-shrink-0">
              <Bot className="w-3.5 h-3.5" />
            </div>
            <div className="bg-zinc-900 border border-zinc-800 text-zinc-400 rounded-2xl px-4 py-3 flex items-center gap-2">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400" />
              <span>DocMind is thinking...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <div className="p-3 sm:p-4 border-t border-zinc-800/80 bg-zinc-950 flex-shrink-0">
        <form onSubmit={handleSubmit} className="relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={sending || !activeSession}
            placeholder={
              !activeSession
                ? 'Select or upload a document to chat...'
                : 'Ask anything about your document...'
            }
            className="w-full bg-zinc-900/90 border border-zinc-800 rounded-xl py-3 pl-4 pr-11 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500/80 transition-all disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || sending || !activeSession}
            className="absolute right-2.5 p-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-all disabled:opacity-40 disabled:hover:bg-indigo-600 shadow-sm"
          >
            {sending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
          </button>
        </form>
      </div>
    </div>
  );
}
