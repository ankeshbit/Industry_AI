import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { Lock, Eye, EyeOff, CheckCircle2, AlertCircle, Shield, ArrowRight, RotateCcw } from 'lucide-react';

interface ResetPasswordProps {
  token: string;
  onSuccess: () => void;
  onRequestNewLink: () => void;
  onCancel: () => void;
}

export const ResetPasswordModal: React.FC<ResetPasswordProps> = ({
  token,
  onSuccess,
  onRequestNewLink,
  onCancel,
}) => {
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Token validation state
  const [verifyingToken, setVerifyingToken] = useState(true);
  const [tokenError, setTokenError] = useState<string | null>(null);

  // Form submission state
  const [loading, setLoading] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [resetCompleted, setResetCompleted] = useState(false);

  // Pre-validate token on mount
  useEffect(() => {
    let isMounted = true;
    async function checkToken() {
      if (!token) {
        if (isMounted) {
          setTokenError('No password reset token was provided in the URL.');
          setVerifyingToken(false);
        }
        return;
      }

      // If token is special 'supabase' token from Supabase Auth hash redirect
      if (token === 'supabase') {
        if (isMounted) setVerifyingToken(false);
        return;
      }

      try {
        await api.auth.verifyResetToken(token);
        if (isMounted) {
          setTokenError(null);
          setVerifyingToken(false);
        }
      } catch (err: any) {
        if (isMounted) {
          if (err?.code === 'EXPIRED_TOKEN') {
            setTokenError('This password reset link has expired. Reset links are valid for 20 minutes.');
          } else {
            setTokenError(err?.message || 'This password reset link is invalid or has already been used.');
          }
          setVerifyingToken(false);
        }
      }
    }

    checkToken();
    return () => {
      isMounted = false;
    };
  }, [token]);

  const passwordsMatch = newPassword.length > 0 && newPassword === confirmPassword;
  const isLengthValid = newPassword.length >= 12;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    if (!isLengthValid) {
      setSubmitError('Password must be at least 12 characters long.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setSubmitError('Password confirmation does not match.');
      return;
    }

    setLoading(true);

    try {
      await api.auth.resetPassword(token, newPassword);
      setResetCompleted(true);
      // Clean recovery parameters and hash from browser address bar
      try {
        const url = new URL(window.location.href);
        url.searchParams.delete('reset_token');
        url.searchParams.delete('token');
        url.searchParams.delete('code');
        url.searchParams.delete('type');
        url.hash = '';
        window.history.replaceState({}, '', url.pathname + (url.search ? url.search : ''));
      } catch {
        // ignore
      }
    } catch (err: any) {
      if (err?.code === 'EXPIRED_TOKEN') {
        setTokenError('This password reset link has expired. Please request a new one.');
      } else if (err?.code === 'INVALID_OR_CONSUMED_TOKEN') {
        setTokenError('This reset link has already been used or is invalid. Please request a new link.');
      } else {
        setSubmitError(err?.message || 'Failed to update password. Please verify requirements.');
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
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">Set new password</h2>
          <p className="text-xs text-slate-500 mt-1 max-w-xs mx-auto leading-relaxed">
            Create a new password to secure your INDUSTRIA AI engineering account.
          </p>
        </div>

        {/* Verifying Token Spinner */}
        {verifyingToken ? (
          <div className="py-10 text-center space-y-3">
            <div className="w-8 h-8 border-3 border-sky-600 border-t-transparent rounded-full animate-spin mx-auto" />
            <div className="text-xs text-slate-600 font-medium">Validating security token...</div>
          </div>
        ) : tokenError ? (
          /* Invalid / Expired Token State */
          <div className="space-y-5">
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl space-y-2 text-xs">
              <div className="flex items-center gap-2 font-bold text-rose-800">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                <span>Invalid or Expired Link</span>
              </div>
              <p className="text-rose-700 leading-relaxed text-[11px]">
                {tokenError}
              </p>
            </div>

            <button
              type="button"
              onClick={onRequestNewLink}
              className="w-full bg-sky-600 hover:bg-sky-700 text-white font-semibold py-2.5 rounded-lg text-sm transition-colors shadow-xs flex items-center justify-center gap-2"
            >
              <RotateCcw className="w-4 h-4" />
              Request New Reset Link
            </button>

            <button
              type="button"
              onClick={onCancel}
              className="w-full bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold py-2.5 rounded-lg text-xs transition-colors"
            >
              Return to Sign In
            </button>
          </div>
        ) : resetCompleted ? (
          /* Success State */
          <div className="space-y-5">
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl space-y-2 text-xs">
              <div className="flex items-center gap-2 font-bold text-emerald-900">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>Password Reset Complete</span>
              </div>
              <p className="text-emerald-800 leading-relaxed text-[11px]">
                Your password has been updated successfully. All existing active sessions have been invalidated for security. You can now log in with your new password.
              </p>
            </div>

            <button
              type="button"
              onClick={onSuccess}
              className="w-full bg-sky-600 hover:bg-sky-700 text-white font-semibold py-2.5 rounded-lg text-sm transition-colors shadow-xs flex items-center justify-center gap-2"
            >
              Sign In to Workspace
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        ) : (
          /* Form State */
          <form onSubmit={handleSubmit} className="space-y-4">
            {submitError && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-500" />
                <span>{submitError}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                New Password <span className="text-slate-500 font-normal">(min 12 characters)</span>
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  autoFocus
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg pl-9 pr-10 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-sky-500 focus:bg-white"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 p-0.5"
                  title={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Confirm New Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
                <input
                  type={showConfirmPassword ? 'text' : 'password'}
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg pl-9 pr-10 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-sky-500 focus:bg-white"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 p-0.5"
                  title={showConfirmPassword ? 'Hide password' : 'Show password'}
                >
                  {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Validation Checklist */}
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1.5">
              <div className={`flex items-center gap-1.5 ${isLengthValid ? 'text-emerald-700' : 'text-slate-500'}`}>
                <CheckCircle2 className={`w-3.5 h-3.5 ${isLengthValid ? 'text-emerald-600' : 'text-slate-300'}`} />
                <span>At least 12 characters ({newPassword.length}/12)</span>
              </div>
              <div className={`flex items-center gap-1.5 ${passwordsMatch ? 'text-emerald-700' : 'text-slate-500'}`}>
                <CheckCircle2 className={`w-3.5 h-3.5 ${passwordsMatch ? 'text-emerald-600' : 'text-slate-300'}`} />
                <span>Passwords match</span>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !isLengthValid || !passwordsMatch}
              className="w-full bg-sky-600 hover:bg-sky-700 text-white font-semibold py-2.5 rounded-lg text-sm transition-colors shadow-xs disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Updating Password...
                </>
              ) : (
                'Update Password'
              )}
            </button>

            <div className="text-center pt-2">
              <button
                type="button"
                onClick={onCancel}
                className="text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
              >
                Cancel and return to Sign In
              </button>
            </div>
          </form>
        )}

        <div className="pt-2 border-t border-slate-100 flex items-center justify-center gap-1.5 text-[11px] text-slate-500">
          <Shield className="w-3.5 h-3.5 text-slate-400" />
          <span>Argon2id cryptographic password security</span>
        </div>
      </div>
    </div>
  );
};

export default ResetPasswordModal;

