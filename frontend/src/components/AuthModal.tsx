import React, { useState } from 'react';
import { api, User } from '../api';
import { Lock, Building2, User as UserIcon, Mail, AlertCircle } from 'lucide-react';

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
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (tab === 'register') {
        if (password.length < 12) {
          throw { message: 'Password must be at least 12 characters long.' };
        }
        await api.auth.register({
          organisation_name: orgName,
          email,
          full_name: fullName,
          password,
        });
        // Auto-login after registration
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
    <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-md w-full p-6 shadow-2xl">
        <div className="text-center mb-6">
          <h2 className="text-2xl font-bold tracking-tight text-white">INDUSTRIA AI</h2>
          <p className="text-xs text-slate-400 mt-1 uppercase tracking-widest font-mono">
            Industrial Predictive Maintenance SaaS • PRD v1.2
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex border-b border-slate-800 mb-6">
          <button
            onClick={() => { setTab('login'); setError(null); }}
            className={`flex-1 pb-3 text-sm font-medium transition-colors border-b-2 ${
              tab === 'login' ? 'border-sky-500 text-sky-400 font-semibold' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Sign In
          </button>
          <button
            onClick={() => { setTab('register'); setError(null); }}
            className={`flex-1 pb-3 text-sm font-medium transition-colors border-b-2 ${
              tab === 'register' ? 'border-sky-500 text-sky-400 font-semibold' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Register Organisation
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-4 p-3 bg-rose-950/30 border border-rose-500/30 rounded-lg text-xs text-rose-300 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {tab === 'register' && (
            <>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Organisation Name</label>
                <div className="relative">
                  <Building2 className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
                  <input
                    type="text"
                    required
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    placeholder="Acme Machining Corp"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Full Name</label>
                <div className="relative">
                  <UserIcon className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Jane Doe"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500"
                  />
                </div>
              </div>
            </>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Corporate Email</label>
            <div className="relative">
              <Mail className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="operator@plant.com"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Password {tab === 'register' && <span className="text-slate-500">(min 12 characters)</span>}
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-sky-600 hover:bg-sky-500 text-white font-medium py-2.5 rounded-lg text-sm transition-colors shadow-lg shadow-sky-600/20 disabled:opacity-50 mt-2"
          >
            {loading ? 'Processing...' : tab === 'login' ? 'Sign In to Workspace' : 'Create Initial Organisation'}
          </button>
        </form>

        {tab === 'register' && (
          <p className="text-xs text-slate-500 text-center mt-4">
            Single-organisation deployment mode: Creates Org Admin account and binds default plant.
          </p>
        )}
      </div>
    </div>
  );
};

