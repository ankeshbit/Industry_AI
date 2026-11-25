import React, { useState } from 'react';
import { api } from '../api';
import { Mail, ArrowLeft, CheckCircle2, AlertCircle, Shield, Send } from 'lucide-react';

interface ForgotPasswordProps {
  onBackToSignIn: () => void;
}

export const ForgotPasswordModal: React.FC<ForgotPasswordProps> = ({ onBackToSignIn }) => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setError(null);
    setLoading(true);

    try {
      await api.auth.forgotPassword(email);
      // Always show generic success state to prevent email enumeration
      setSubmitted(true);
    } catch (err: any) {
      if (err?.code === 'RATE_LIMIT_EXCEEDED') {
        setError(err.message || 'Too many reset requests. Please wait a few minutes before trying again.');
      } else {
        // Even for unexpected errors, show clean user-facing error message
        setError(err?.message || 'Unable to submit reset request. Please check network connection.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-white border border-slate-200 rounded-2xl max-w-md w-full p-8 shadow-2xl space-y-6">
        {/* Header */}
        <div className="text-center">
          <div className="w-16 h-16 flex items-center justify-center mx-auto mb-3">
            <img src="/logo.png" alt="Industry AI Logo" className="w-16 h-16 object-contain" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">Reset your password</h2>
          <p className="text-xs text-slate-500 mt-1 max-w-xs mx-auto leading-relaxed">
            Enter your corporate email address and we'll send you a single-use link to reset your account password.
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-500" />
            <span>{error}</span>
          </div>
        )}

        {submitted ? (
          /* Generic Confirmation State (Enumeration Resistant) */
          <div className="space-y-5">
            <div className="p-4 bg-emerald-50/70 border border-emerald-200 rounded-xl space-y-2 text-xs">
              <div className="flex items-center gap-2 font-bold text-emerald-900">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>Reset Link Dispatched</span>
              </div>
              <p className="text-emerald-800 leading-relaxed text-[11px]">
                If that email address is registered in our platform, a password reset link has been sent. Please check your inbox and follow the instructions to set a new password.
              </p>
              <div className="text-[10px] text-emerald-700 font-medium pt-1 border-t border-emerald-200/60">
                • Link valid for 20 minutes • Single-use security token
              </div>
            </div>

            <button
              type="button"
              onClick={onBackToSignIn}
              className="w-full bg-sky-600 hover:bg-sky-700 text-white font-semibold py-2.5 rounded-lg text-sm transition-colors shadow-xs flex items-center justify-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              Return to Sign In
            </button>
          </div>
        ) : (
          /* Form State */
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Corporate Email Address</label>
              <div className="relative">
                <Mail className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
                <input
                  type="email"
                  required
                  autoFocus
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="operator@plant.com"
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-sky-500 focus:bg-white"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !email}
              className="w-full bg-sky-600 hover:bg-sky-700 text-white font-semibold py-2.5 rounded-lg text-sm transition-colors shadow-xs disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Sending Reset Link...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  Send Reset Link
                </>
              )}
            </button>

            <div className="text-center pt-2">
              <button
                type="button"
                onClick={onBackToSignIn}
                className="text-xs font-semibold text-slate-600 hover:text-slate-900 inline-flex items-center gap-1.5 transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Back to Sign In
              </button>
            </div>
          </form>
        )}

        <div className="pt-2 border-t border-slate-100 flex items-center justify-center gap-1.5 text-[11px] text-slate-500">
          <Shield className="w-3.5 h-3.5 text-slate-400" />
          <span>Encrypted token authentication with strict rate limiting</span>
        </div>
      </div>
    </div>
  );
};

export default ForgotPasswordModal;

