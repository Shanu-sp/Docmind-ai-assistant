import React, { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '../context/AuthContext';
import { Bot, FileText, Lock, Mail, Key, User, ArrowRight, Eye, EyeOff, Loader2 } from 'lucide-react';

export default function LoginModal() {
  const { loginWithGoogleToken, loginWithEmail, registerWithEmail } = useAuth();
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
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

  const handleEmailSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!email.trim() || !password.trim()) {
      setError('Please fill in all required fields.');
      return;
    }

    if (isSignUp && password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    setLoading(true);
    let result;
    if (isSignUp) {
      result = await registerWithEmail(email.trim(), password, name.trim());
    } else {
      result = await loginWithEmail(email.trim(), password);
    }
    setLoading(false);

    if (!result.success) {
      setError(result.error);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/90 backdrop-blur-md p-4 animate-fade-in">
      <div className="w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-2xl p-7 shadow-2xl space-y-5 text-zinc-100 animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header Icon & Title */}
        <div className="text-center space-y-1.5">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 text-indigo-400 mb-1 shadow-inner">
            <Bot className="w-6 h-6" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Welcome to DocMind</h2>
          <p className="text-xs text-zinc-400 max-w-xs mx-auto">
            Your Private AI Document Workspace. Sign in or create an account to access your personal vault.
          </p>
        </div>

        {/* Auth Mode Toggle Tabs */}
        <div className="flex bg-zinc-950/70 p-1 rounded-xl border border-zinc-800/80 text-xs font-medium">
          <button
            type="button"
            onClick={() => { setIsSignUp(false); setError(''); }}
            className={`flex-1 py-1.5 rounded-lg transition-all ${
              !isSignUp ? 'bg-zinc-800 text-zinc-100 shadow-sm' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setIsSignUp(true); setError(''); }}
            className={`flex-1 py-1.5 rounded-lg transition-all ${
              isSignUp ? 'bg-zinc-800 text-zinc-100 shadow-sm' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            Create Account
          </button>
        </div>

        {/* Feature Pills */}
        <div className="grid grid-cols-2 gap-2 text-[11px] text-zinc-400">
          <div className="flex items-center gap-2 p-2 rounded-lg bg-zinc-950/50 border border-zinc-800/80">
            <Lock className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
            <span>Strict Data Isolation</span>
          </div>
          <div className="flex items-center gap-2 p-2 rounded-lg bg-zinc-950/50 border border-zinc-800/80">
            <FileText className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
            <span>Private Document Vault</span>
          </div>
        </div>

        {error && (
          <div className="p-3 rounded-xl bg-rose-950/50 border border-rose-800/80 text-rose-300 text-xs text-center">
            {error}
          </div>
        )}

        {/* Google SSO */}
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

        {/* Divider */}
        <div className="relative flex items-center justify-center">
          <div className="w-full border-t border-zinc-800" />
          <span className="absolute px-3 bg-zinc-900 text-[10px] uppercase font-semibold text-zinc-500 tracking-wider">
            or continue with email
          </span>
        </div>

        {/* Email & Password Form */}
        <form onSubmit={handleEmailSubmit} className="space-y-3">
          {isSignUp && (
            <div className="space-y-1">
              <label className="text-[11px] font-medium text-zinc-300">Full Name</label>
              <div className="relative flex items-center">
                <User className="w-4 h-4 text-zinc-500 absolute left-3 pointer-events-none" />
                <input
                  type="text"
                  placeholder="e.g. Sarah Connor"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            </div>
          )}

          <div className="space-y-1">
            <label className="text-[11px] font-medium text-zinc-300">Email Address</label>
            <div className="relative flex items-center">
              <Mail className="w-4 h-4 text-zinc-500 absolute left-3 pointer-events-none" />
              <input
                type="email"
                required
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-9 pr-3 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-medium text-zinc-300">Password</label>
            <div className="relative flex items-center">
              <Key className="w-4 h-4 text-zinc-500 absolute left-3 pointer-events-none" />
              <input
                type={showPassword ? 'text' : 'password'}
                required
                placeholder={isSignUp ? 'At least 6 characters' : 'Enter your password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-9 pr-10 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 text-zinc-500 hover:text-zinc-300"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 flex items-center justify-center gap-2 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-indigo-600/20 transition-all disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <span>{isSignUp ? 'Create DocMind Account' : 'Sign In with Email'}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </form>

        <div className="text-center pt-1">
          <p className="text-[10px] text-zinc-500">
            By signing in, your uploaded documents and chat histories remain strictly confidential to your account.
          </p>
        </div>

      </div>
    </div>
  );
}
