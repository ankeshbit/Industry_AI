import React, { useState, useEffect } from 'react';
import { api, User } from '../api';
import { isSupabaseConfigured } from '../lib/supabase';
import { Lock, Building2, User as UserIcon, Mail, AlertCircle, Shield, CheckCircle2, Zap } from 'lucide-react';

interface AuthModalProps {
  onSuccess: (user: User) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ onSuccess }) => {
  const [tab, setTab] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [orgName, setOrgName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [successInfo, setSuccessInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [supabaseActive, setSupabaseActive] = useState(isSupabaseConfigured());

  useEffect(() => {
    // Check backend auth config as well to detect server-side Supabase configuration
    api.auth.getConfig()
      .then((cfg) => {
        if (cfg.auth_provider === 'supabase' || isSupabaseConfigured()) {
          setSupabaseActive(true);
        }
      })
      .catch(() => undefined);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessInfo(null);
    setLoading(true);

    try {
      if (tab === 'register') {
        if (password.length < 12) {
          throw { message: 'Password must be at least 12 characters long.' };
        }
        const regRes = await api.auth.register({
          organisation_name: orgName,
          email,
          full_name: fullName,
          password,
        });

        // If email confirmation is required by Supabase project
        if (regRes.message && regRes.message.includes('verify your email')) {
          setSuccessInfo(regRes.message);
          setTab('login');
          return;
        }

        const loginData = await api.auth.login({ email, password });
        onSuccess(loginData.user);
      } else {
        const loginData = await api.auth.login({ email, password });
        onSuccess(loginData.user);
      }
    } catch (err: any) {
      if (err.code === 'MULTI_ORG_DISABLED') {
        setError('Multi-organisation registration is disabled in single-organisation mode (MS1). An organisation already exists.');
      } else if (err.code === 'ACCOUNT_LOCKED') {
        setError(err.message || 'Account locked for 15 minutes due to repeated failed logins.');
      } else {
        setError(err.message || 'Authentication failed. Please verify credentials.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-white border border-slate-200 rounded-2xl max-w-md w-full p-8 shadow-2xl space-y-6">
        <div className="text-center">
          <div className="w-16 h-16 flex items-center justify-center mx-auto mb-3">
            <img src="/logo.png" alt="Industry AI Logo" className="w-16 h-16 object-contain" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">INDUSTRIA AI</h2>
          <p className="text-xs text-slate-500 mt-1 uppercase tracking-wider font-medium">
            Industrial Predictive Maintenance • PRD v1.2
          </p>
          <div className="mt-2.5 flex items-center justify-center gap-1.5">
            {supabaseActive ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                <Zap className="w-3 h-3 text-emerald-600" />
                Supabase Auth Active
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-600 border border-slate-200">
                <Shield className="w-3 h-3 text-slate-500" />
                Local Dev Auth Mode
              </span>
            )}
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="flex border-b border-slate-200">
          <button
            onClick={() => { setTab('login'); setError(null); setSuccessInfo(null); }}
            className={`flex-1 pb-3 text-sm font-medium transition-colors border-b-2 ${
              tab === 'login' 
                ? 'border-sky-600 text-sky-600 font-semibold' 
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            Sign In
          </button>
          <button
            onClick={() => { setTab('register'); setError(null); setSuccessInfo(null); }}
            className={`flex-1 pb-3 text-sm font-medium transition-colors border-b-2 ${
              tab === 'register' 
                ? 'border-sky-600 text-sky-600 font-semibold' 
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            Register Plant
          </button>
        </div>

        {/* Success Alert */}
        {successInfo && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800 flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-emerald-600" />
            <span>{successInfo}</span>
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-500" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {tab === 'register' && (
            <>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Organisation Name</label>
                <div className="relative">
                  <Building2 className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
                  <input
                    type="text"
                    required
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    placeholder="Acme Machining Corp"
                    className="w-full bg-slate-50 border border-slate-300 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-sky-500 focus:bg-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Lead Engineer Name</label>
                <div className="relative">
                  <UserIcon className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Jane Doe"
                    className="w-full bg-slate-50 border border-slate-300 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-sky-500 focus:bg-white"
                  />
                </div>
              </div>
            </>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Corporate Email</label>
            <div className="relative">
              <Mail className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="operator@plant.com"
                className="w-full bg-slate-50 border border-slate-300 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-sky-500 focus:bg-white"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Password {tab === 'register' && <span className="text-slate-500 font-normal">(min 12 characters)</span>}
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full bg-slate-50 border border-slate-300 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-sky-500 focus:bg-white"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-sky-600 hover:bg-sky-700 text-white font-semibold py-2.5 rounded-lg text-sm transition-colors shadow-sm disabled:opacity-50 mt-2"
          >
            {loading ? 'Authenticating...' : tab === 'login' ? 'Sign In to Workspace' : 'Create Initial Organisation'}
          </button>
        </form>

        <p className="text-[11px] text-slate-500 text-center">
          Single-tenant production monolith with Neon PostgreSQL serverless database.
        </p>
      </div>
    </div>
  );
};
export default AuthModal;
