import React, { useState, useEffect } from 'react';
import { api, User, CompatibilityCheck, AnalysisResult, Machine } from './api';
import { AuthModal } from './components/AuthModal';
import { Sidebar, NavSection } from './components/Sidebar';
import { Header } from './components/Header';
import { DashboardView } from './components/DashboardView';
import { DatasetsView } from './components/DatasetsView';
import { PipelineView } from './components/PipelineView';
import { PredictionsView } from './components/PredictionsView';
import { ExplainabilityView } from './components/ExplainabilityView';
import { ReportsView } from './components/ReportsView';
import { SettingsView } from './components/SettingsView';
import { DatasetUploadWizard } from './components/DatasetUploadWizard';
import { CompatibilityModal } from './components/CompatibilityModal';
import { HowItWorksModal } from './components/HowItWorksModal';
import { Cpu, UploadCloud, Plus, X, ArrowRight } from 'lucide-react';

export function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  // Navigation & Shell State
  const [currentSection, setCurrentSection] = useState<NavSection>('dashboard');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const [showHowItWorksModal, setShowHowItWorksModal] = useState(false);

  // Workflow & Interactive Inter-View State
  const [activeMachineForUpload, setActiveMachineForUpload] = useState<string | null>(null);
  const [activeCheck, setActiveCheck] = useState<CompatibilityCheck | null>(null);
  const [targetAnalysisId, setTargetAnalysisId] = useState<string | null>(null);
  const [selectedExplainabilityRow, setSelectedExplainabilityRow] = useState<any | null>(null);

  // Quick Ingest Target Picker Modal
  const [showMachinePickerModal, setShowMachinePickerModal] = useState(false);
  const [availableMachines, setAvailableMachines] = useState<Machine[]>([]);
  const [loadingMachines, setLoadingMachines] = useState(false);

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
    setCurrentSection('dashboard');
    setActiveCheck(null);
    setActiveMachineForUpload(null);
    setTargetAnalysisId(null);
    setSelectedExplainabilityRow(null);
  };

  // Open Quick Upload
  const handleOpenQuickUpload = async (preselectedMachineId?: string) => {
    if (preselectedMachineId) {
      setActiveMachineForUpload(preselectedMachineId);
      return;
    }

    try {
      setLoadingMachines(true);
      setShowMachinePickerModal(true);
      const machs = await api.machines.list();
      setAvailableMachines(machs.filter((m) => !m.archived_at));
    } catch (err) {
      console.error('Failed to load machines for quick upload:', err);
    } finally {
      setLoadingMachines(false);
    }
  };

  if (!authChecked) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center text-slate-500 text-sm font-medium">
        <div className="w-8 h-8 border-3 border-sky-600 border-t-transparent rounded-full animate-spin mb-3"></div>
        Initializing INDUSTRIA AI workspace & Neon DB connection...
      </div>
    );
  }

  if (!currentUser) {
    return <AuthModal onSuccess={(user) => setCurrentUser(user)} />;
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex antialiased">
      {/* Collapsible Left Sidebar */}
      <Sidebar
        activeSection={currentSection}
        onSelectSection={(sec) => {
          setCurrentSection(sec);
          setIsMobileNavOpen(false);
        }}
        currentUser={currentUser}
        onLogout={handleLogout}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        isMobileOpen={isMobileNavOpen}
        onCloseMobile={() => setIsMobileNavOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        {/* Sticky Header with Dynamic Breadcrumbs */}
        <Header
          activeSection={currentSection}
          onOpenMobile={() => setIsMobileNavOpen(true)}
          onQuickUpload={() => handleOpenQuickUpload()}
          onOpenHowItWorks={() => setShowHowItWorksModal(true)}
        />

        {/* Viewport Content */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          {currentSection === 'dashboard' && (
            <DashboardView
              onNavigate={(sec) => setCurrentSection(sec)}
              onOpenUpload={(mId) => handleOpenQuickUpload(mId)}
              onOpenMachineModal={() => setCurrentSection('settings')}
              onSelectAnalysis={(resId) => {
                setTargetAnalysisId(resId);
                setCurrentSection('predictions');
              }}
              onOpenHowItWorks={() => setShowHowItWorksModal(true)}
            />
          )}

          {currentSection === 'datasets' && (
            <DatasetsView
              onStartUpload={(mId) => handleOpenQuickUpload(mId)}
              onSelectMachineUpload={(mId) => handleOpenQuickUpload(mId)}
            />
          )}

          {currentSection === 'pipeline' && (
            <PipelineView
              onNavigateToPredictions={() => setCurrentSection('predictions')}
            />
          )}

          {currentSection === 'predictions' && (
            <PredictionsView
              initialResultId={targetAnalysisId}
              onSelectExplainabilityRow={(row) => {
                setSelectedExplainabilityRow(row);
                setCurrentSection('explainability');
              }}
              onNavigateToExplainability={() => setCurrentSection('explainability')}
            />
          )}

          {currentSection === 'explainability' && (
            <ExplainabilityView
              selectedRow={selectedExplainabilityRow}
              onClearSelectedRow={() => setSelectedExplainabilityRow(null)}
              onNavigateToPredictions={() => setCurrentSection('predictions')}
            />
          )}

          {currentSection === 'reports' && (
            <ReportsView />
          )}

          {currentSection === 'settings' && (
            <SettingsView
              currentUser={currentUser}
              onSelectMachineForUpload={(mId) => handleOpenQuickUpload(mId)}
            />
          )}
        </main>

        {/* Minimal Footer */}
        <footer className="border-t border-slate-200/80 bg-white/60 py-3.5 px-6 text-center sm:text-left flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 font-mono">
          <div className="flex items-center gap-2">
            <img src="/logo.png" alt="Industry AI" className="w-4 h-4 object-contain" />
            <span>INDUSTRIA AI • Predictive Maintenance Platform • Authoritative PRD v1.2</span>
          </div>
          <span className="mt-1 sm:mt-0 text-[11px] text-slate-400">Stage 3 Validated • Pure Software Modular Monolith</span>
        </footer>
      </div>

      {/* MODAL 1: Target Machine Picker for Quick Upload */}
      {showMachinePickerModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white border border-slate-200 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <UploadCloud className="w-4 h-4 text-sky-600" />
                Select Destination Machinery Asset
              </h3>
              <button
                onClick={() => setShowMachinePickerModal(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-600">
              Choose the physical machine tool that produced this sensor dataset. Active machines only (AC-MM-2).
            </p>

            {loadingMachines ? (
              <div className="py-8 text-center text-xs text-slate-500">
                Loading machinery catalog...
              </div>
            ) : availableMachines.length === 0 ? (
              <div className="py-6 text-center space-y-3">
                <p className="text-xs text-slate-500">No active machines found in your plant organization.</p>
                <button
                  onClick={() => {
                    setShowMachinePickerModal(false);
                    setCurrentSection('settings');
                  }}
                  className="bg-sky-600 text-white text-xs px-3 py-1.5 rounded-lg font-medium inline-flex items-center gap-1.5"
                >
                  <Plus className="w-3.5 h-3.5" /> Register a Machine First
                </button>
              </div>
            ) : (
              <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                {availableMachines.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => {
                      setShowMachinePickerModal(false);
                      setActiveMachineForUpload(m.id);
                    }}
                    className="w-full text-left p-3 rounded-xl border border-slate-200 hover:border-sky-500 hover:bg-sky-50/50 transition-all flex items-center justify-between group"
                  >
                    <div>
                      <div className="font-mono text-xs font-bold text-sky-700">{m.asset_tag}</div>
                      <div className="text-xs font-semibold text-slate-900">{m.name}</div>
                      <div className="text-[11px] text-slate-500">{m.category_code}</div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-sky-600 group-hover:translate-x-0.5 transition-all" />
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* MODAL 2: Dataset Upload & Schema Wizard */}
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

      {/* MODAL 3: Pre-Execution Compatibility & Gate Verification */}
      {activeCheck && (
        <CompatibilityModal
          check={activeCheck}
          onClose={() => setActiveCheck(null)}
          onAnalysisStarted={(result) => {
            setActiveCheck(null);
            setTargetAnalysisId(result.id);
            setCurrentSection('predictions');
          }}
        />
      )}

      {/* MODAL 4: How It Works Educational Walkthrough */}
      <HowItWorksModal
        isOpen={showHowItWorksModal}
        onClose={() => setShowHowItWorksModal(false)}
        onStartUpload={() => handleOpenQuickUpload()}
      />
    </div>
  );
}

export default App;
