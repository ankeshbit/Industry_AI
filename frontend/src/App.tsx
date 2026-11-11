import React, { useState, useEffect } from 'react';
import { api, User, CompatibilityCheck, AnalysisResult } from './api';
import { AuthModal } from './components/AuthModal';
import { MachineRegistry } from './components/MachineRegistry';
import { DatasetUploadWizard } from './components/DatasetUploadWizard';
import { CompatibilityModal } from './components/CompatibilityModal';
import { AnalysisView } from './components/AnalysisView';
import { Shield, Building, LogOut, Terminal, Activity } from 'lucide-react';

export function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  // Workflow State
  const [activeMachineForUpload, setActiveMachineForUpload] = useState<string | null>(null);
  const [activeCheck, setActiveCheck] = useState<CompatibilityCheck | null>(null);
  const [activeAnalysisId, setActiveAnalysisId] = useState<string | null>(null);

  useEffect(() => {
    async function checkAuth() {
      const token = localStorage.getItem('access_token');
      if (token) {
        try {
          const user = await api.auth.getMe();
          setCurrentUser(user);
        } catch (e) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
        }
      }
      setAuthChecked(true);
    }
    checkAuth();
  }, []);

  const handleLogout = () => {
    api.auth.logout();
    setCurrentUser(null);
    setActiveAnalysisId(null);
    setActiveCheck(null);
    setActiveMachineForUpload(null);
  };

  if (!authChecked) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400 text-sm">
        Initializing INDUSTRIA AI workspace...
      </div>
    );
  }

  if (!currentUser) {
    return <AuthModal onSuccess={(user) => setCurrentUser(user)} />;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Navigation Bar */}
      <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-sky-600 flex items-center justify-center shadow-lg shadow-sky-600/30">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-base tracking-tight text-white">INDUSTRIA AI</span>
                <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-slate-800 text-sky-400 border border-slate-700">
                  MS1: Core AI4I
                </span>
              </div>
              <div className="text-[11px] text-slate-400 font-mono">Predictive Maintenance Modular Monolith</div>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60">
              <Building className="w-3.5 h-3.5 text-slate-400" />
              <span className="font-medium text-slate-300">{currentUser.organisation.name}</span>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-slate-400">{currentUser.email}</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20 font-mono">
                {currentUser.role}
              </span>
            </div>

            <button
              onClick={handleLogout}
              className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Workspace Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeAnalysisId ? (
          <AnalysisView
            resultId={activeAnalysisId}
            onBack={() => setActiveAnalysisId(null)}
          />
        ) : (
          <MachineRegistry
            onSelectUpload={(mId) => setActiveMachineForUpload(mId)}
            onViewAnalysis={(resId) => setActiveAnalysisId(resId)}
          />
        )}
      </main>

      {/* Modals & Wizards */}
      {activeMachineForUpload && (
        <DatasetUploadWizard
          machineId={activeMachineForUpload}
          onCancel={() => setActiveMachineForUpload(null)}
          onComplete={(check) => {
            setActiveMachineForUpload(null);
            setActiveCheck(check);
          }}
        />
      )}

      {activeCheck && (
        <CompatibilityModal
          check={activeCheck}
          onClose={() => setActiveCheck(null)}
          onAnalysisStarted={(result) => {
            setActiveCheck(null);
            setActiveAnalysisId(result.id);
          }}
        />
      )}

      {/* Footer */}
      <footer className="border-t border-slate-800/80 py-4 text-center text-xs text-slate-500 font-mono">
        INDUSTRIA AI • Authoritative PRD v1.2 Implementation • Pure Software Modular Monolith
      </footer>
    </div>
  );
}

export default App;

