import React, { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '../context/AuthContext';
import { Bot, Shield, Sparkles, FileText, Lock, UserCheck } from 'lucide-react';

export default function LoginModal() {
  const { loginWithGoogleToken } = useAuth();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleGoogleSuccess = async (credentialResponse) => {
    setError('');
    setLoading(true);
    const result = await loginWithGoogleToken(credentialResponse.credential);
    setLoading(false);
    if (!result.success) {
      setError(result.error);
    }
  };

  const handleGoogleError = () => {
    setError('Google Sign-In prompt was closed or failed.');
  };

  // Demo Login Handler for instant developer / offline demo testing
  const handleDemoLogin = async (demoEmail, demoName) => {
    setError('');
    setLoading(true);
    // Create an unverified mock JWT for demo mode
    const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
    const payload = btoa(JSON.stringify({ email: demoEmail, name: demoName, given_name: demoName }));
    const mockToken = `${header}.${payload}.mockSignature`;

    const result = await loginWithGoogleToken(mockToken);
    setLoading(false);
    if (!result.success) {
      setError(result.error);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/90 backdrop-blur-md p-4">
      <div className="w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-2xl p-8 shadow-2xl space-y-6 text-zinc-100 animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header Icon & Title */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-zinc-800 border border-zinc-700 text-emerald-400 mb-2 shadow-inner">
            <Bot className="w-7 h-7" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Welcome to DocMind</h2>
          <p className="text-xs text-zinc-400 max-w-xs mx-auto">
            Your Private AI Document Workspace. Sign in to access your personal document collection.
          </p>
        </div>

        {/* Feature Pills */}
        <div className="grid grid-cols-2 gap-2 text-xs text-zinc-400 py-1">
          <div className="flex items-center gap-2 p-2 rounded-lg bg-zinc-950/50 border border-zinc-800/80">
            <Lock className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>Strict User Data Isolation</span>
          </div>
          <div className="flex items-center gap-2 p-2 rounded-lg bg-zinc-950/50 border border-zinc-800/80">
            <FileText className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>Private Document Vault</span>
          </div>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-red-950/50 border border-red-800 text-red-300 text-xs text-center">
            {error}
          </div>
        )}

        {/* Google SSO Container */}
        <div className="space-y-4 pt-2">
          <div className="flex justify-center">
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={handleGoogleError}
              theme="filled_black"
              shape="pill"
              size="large"
              text="continue_with"
              width="100%"
            />
          </div>

          <div className="relative flex py-2 items-center">
            <div className="flex-grow border-t border-zinc-800"></div>
            <span className="flex-shrink mx-4 text-[11px] text-zinc-500 uppercase tracking-wider font-semibold">Or Quick Demo Sign-In</span>
            <div className="flex-grow border-t border-zinc-800"></div>
          </div>

          {/* Quick Demo Accounts */}
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => handleDemoLogin("alice@example.com", "Alice Smith")}
              disabled={loading}
              className="flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-zinc-800/80 hover:bg-zinc-700/80 border border-zinc-700 text-xs font-medium text-zinc-200 transition-colors disabled:opacity-50"
            >
              <UserCheck className="w-3.5 h-3.5 text-blue-400" />
              <span>Demo Account 1</span>
            </button>
            <button
              onClick={() => handleDemoLogin("bob@example.com", "Bob Johnson")}
              disabled={loading}
              className="flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-zinc-800/80 hover:bg-zinc-700/80 border border-zinc-700 text-xs font-medium text-zinc-200 transition-colors disabled:opacity-50"
            >
              <UserCheck className="w-3.5 h-3.5 text-purple-400" />
              <span>Demo Account 2</span>
            </button>
          </div>
        </div>

        <div className="text-center pt-2">
          <p className="text-[10px] text-zinc-500">
            By signing in, your uploaded documents and chat histories remain strictly confidential to your account.
          </p>
        </div>

      </div>
    </div>
  );
}
