import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Loader2, Sparkles, MessageSquare } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function ChatPanel({
  activeSession,
  messages = [],
  onSendMessage,
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

  return (
    <div className="w-[420px] bg-zinc-950 flex flex-col h-screen border-l border-zinc-800/80">
      {/* Chat Session Header */}
      <div className="h-16 border-b border-zinc-800/80 px-5 flex items-center justify-between bg-zinc-900/40 backdrop-blur-md">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center flex-shrink-0">
            <Bot className="w-4.5 h-4.5" />
          </div>
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
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
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
                  className={`rounded-2xl p-3.5 max-w-[85%] leading-relaxed ${
                    isUser
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/10'
                      : 'bg-zinc-900 border border-zinc-800 text-zinc-200 shadow-sm'
                  }`}
                >
                  {isUser ? (
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  ) : (
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      className="prose prose-invert prose-xs max-w-none space-y-2"
                    >
                      {msg.content}
                    </ReactMarkdown>
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
      <div className="p-4 border-t border-zinc-800/80 bg-zinc-950">
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
