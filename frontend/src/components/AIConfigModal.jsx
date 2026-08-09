import React, { useState } from 'react';
import { X, Key, CheckCircle2, AlertCircle, Loader2, Sparkles } from 'lucide-react';
import { updateAIConfig } from '../services/api';

export default function AIConfigModal({ isOpen, onClose, currentConfig, onConfigUpdated }) {
  const [apiKey, setApiKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!apiKey.trim()) return;

    setLoading(true);
    setErrorMsg('');
    setSuccessMsg('');

    try {
      await updateAIConfig(apiKey.trim());
      setSuccessMsg('API Key successfully validated and configured for Gemini 2.5 Flash!');
      setTimeout(() => {
        setLoading(false);
        if (onConfigUpdated) onConfigUpdated();
        onClose();
      }, 1000);
    } catch (err) {
      console.error(err);
      setErrorMsg(err.response?.data?.error || 'Failed to update API key. Please check key validity.');
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-2xl">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-zinc-400 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded-xl">
            <Key className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-zinc-100">Gemini API Key Configuration</h3>
            <p className="text-xs text-zinc-400">Configure your Google Gemini API Key for live AI operations.</p>
          </div>
        </div>

        <div className="mb-4 p-3 bg-zinc-950/80 rounded-xl border border-zinc-800/80 text-xs text-zinc-400 space-y-1">
          <div className="flex justify-between">
            <span>Status:</span>
            <span className={currentConfig?.has_api_key ? "text-emerald-400 font-semibold" : "text-amber-400 font-semibold"}>
              {currentConfig?.has_api_key ? "Active (Live Key Configured)" : "Demo Mode (Mock Answers)"}
            </span>
          </div>
          {currentConfig?.masked_key && (
            <div className="flex justify-between">
              <span>Active Key:</span>
              <span className="font-mono text-zinc-300">{currentConfig.masked_key}</span>
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1.5">Enter Gemini API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="AIzaSy..."
              className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3.5 py-2.5 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-indigo-500 transition-colors font-mono"
            />
            <p className="text-[11px] text-zinc-500 mt-1">
              Get a free API key at <a href="https://aistudio.google.com/" target="_blank" rel="noreferrer" className="text-indigo-400 underline">aistudio.google.com</a>
            </p>
          </div>

          {errorMsg && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl flex items-center gap-2 text-rose-300 text-xs">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl flex items-center gap-2 text-emerald-300 text-xs">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-xl text-xs font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !apiKey.trim()}
              className="flex-1 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-medium transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
              <span>Save API Key</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
