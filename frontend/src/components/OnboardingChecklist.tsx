import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  CheckCircle2, 
  Circle, 
  ArrowRight, 
  UploadCloud, 
  FileSpreadsheet, 
  BookOpen, 
  ChevronDown, 
  ChevronUp, 
  X,
  ShieldCheck,
  Activity,
  BarChart2,
  FileText
} from 'lucide-react';

interface OnboardingChecklistProps {
  stats: {
    totalDatasets: number;
    totalAnalyses: number;
    totalMachines: number;
  };
  onStartUpload: () => void;
  onOpenHowItWorks: () => void;
  onNavigateToSection: (section: 'dashboard' | 'datasets' | 'pipeline' | 'predictions' | 'explainability' | 'reports' | 'settings') => void;
}

export const OnboardingChecklist: React.FC<OnboardingChecklistProps> = ({
  stats,
  onStartUpload,
  onOpenHowItWorks,
  onNavigateToSection,
}) => {
  const [isDismissed, setIsDismissed] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    const dismissed = localStorage.getItem('industria_onboarding_dismissed');
    if (dismissed === 'true') {
      setIsDismissed(true);
    }
  }, []);

  const handleDismiss = () => {
    setIsDismissed(true);
    localStorage.setItem('industria_onboarding_dismissed', 'true');
  };

  // Determine actual state from props
  const step1Done = stats.totalDatasets > 0;
  const step2Done = stats.totalDatasets > 0; // Ingestion validates schema & compatibility
  const step3Done = stats.totalAnalyses > 0;
  const step4Done = stats.totalAnalyses > 0;
  const step5Done = stats.totalAnalyses > 0; // Report generation available

  const stepsCompleted = [step1Done, step2Done, step3Done, step4Done, step5Done].filter(Boolean).length;
  const percentComplete = Math.round((stepsCompleted / 5) * 100);

  if (isDismissed && stepsCompleted === 5) {
    return null; // completely hidden if dismissed and 100% complete
  }

  if (isDismissed) {
    // Show a small persistent reactivation banner
    return (
      <div className="bg-white border border-slate-200 rounded-xl px-4 py-2.5 shadow-sm flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs">
          <Sparkles className="w-4 h-4 text-sky-600" />
          <span className="font-semibold text-slate-800">Onboarding Checklist:</span>
          <span className="text-slate-500">{stepsCompleted} of 5 steps completed ({percentComplete}%)</span>
        </div>
        <button
          onClick={() => {
            setIsDismissed(false);
            localStorage.removeItem('industria_onboarding_dismissed');
          }}
          className="text-xs font-semibold text-sky-600 hover:text-sky-700"
        >
          Resume Checklist
        </button>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-r from-sky-50 via-white to-slate-50 border border-sky-100 rounded-2xl p-5 shadow-sm space-y-4">
      {/* Top Banner Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div className="flex items-start gap-3.5">
          <img src="/logo.png" alt="Industry AI" className="w-11 h-11 object-contain shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-sky-100 text-sky-800 border border-sky-200 uppercase tracking-wider flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-sky-600" />
                Getting Started
              </span>
              <span className="text-xs font-semibold text-slate-500">
                {stepsCompleted} of 5 completed ({percentComplete}%)
              </span>
            </div>
            <h2 className="text-base font-bold text-slate-900 tracking-tight">
              Welcome to INDUSTRIA AI
            </h2>
            <p className="text-xs text-slate-600 max-w-2xl leading-relaxed">
              INDUSTRIA AI helps you analyze industrial operating datasets, estimate machine failure risk, and understand model predictions with calibrated TreeSHAP attributions.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-start">
          <button
            onClick={onOpenHowItWorks}
            className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <BookOpen className="w-3.5 h-3.5 text-sky-600" />
            How It Works
          </button>
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
            title={isCollapsed ? "Expand Checklist" : "Collapse Checklist"}
          >
            {isCollapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
          </button>
          <button
            onClick={handleDismiss}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
            title="Dismiss Onboarding"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-slate-200/80 rounded-full h-1.5 overflow-hidden">
        <div 
          className="bg-sky-600 h-full rounded-full transition-all duration-500"
          style={{ width: `${percentComplete}%` }}
        />
      </div>

      {/* Checklist Grid */}
      {!isCollapsed && (
        <div className="grid grid-cols-1 sm:grid-cols-5 gap-2.5 pt-1">
          {/* Step 1 */}
          <div 
            onClick={!step1Done ? onStartUpload : () => onNavigateToSection('datasets')}
            className={`p-3 rounded-xl border transition-all cursor-pointer ${
              step1Done 
                ? 'bg-white border-emerald-200 hover:border-emerald-300' 
                : 'bg-white border-sky-300 shadow-sm hover:border-sky-500'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Step 1</span>
              {step1Done ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              ) : (
                <Circle className="w-4 h-4 text-sky-500 animate-pulse" />
              )}
            </div>
            <div className="text-xs font-bold text-slate-900">Upload Dataset</div>
            <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">
              Ingest operating CSV telemetry with canonical physical units.
            </p>
            {!step1Done && (
              <span className="text-[10px] font-semibold text-sky-600 flex items-center gap-1 mt-2">
                Upload CSV <ArrowRight className="w-3 h-3" />
              </span>
            )}
          </div>

          {/* Step 2 */}
          <div 
            onClick={() => onNavigateToSection('datasets')}
            className={`p-3 rounded-xl border transition-all cursor-pointer ${
              step2Done 
                ? 'bg-white border-emerald-200 hover:border-emerald-300' 
                : 'bg-white/80 border-slate-200 hover:border-slate-300 opacity-90'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Step 2</span>
              {step2Done ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              ) : (
                <Circle className="w-4 h-4 text-slate-300" />
              )}
            </div>
            <div className="text-xs font-bold text-slate-900">Validate Compatibility</div>
            <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">
              Verify schema alignment and sensor operational ranges.
            </p>
            {step2Done && (
              <span className="text-[10px] font-semibold text-emerald-700 flex items-center gap-1 mt-2">
                Validated ✓
              </span>
            )}
          </div>

          {/* Step 3 */}
          <div 
            onClick={() => onNavigateToSection('pipeline')}
            className={`p-3 rounded-xl border transition-all cursor-pointer ${
              step3Done 
                ? 'bg-white border-emerald-200 hover:border-emerald-300' 
                : 'bg-white/80 border-slate-200 hover:border-slate-300 opacity-90'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Step 3</span>
              {step3Done ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              ) : (
                <Circle className="w-4 h-4 text-slate-300" />
              )}
            </div>
            <div className="text-xs font-bold text-slate-900">Run Inference</div>
            <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">
              Execute M2 XGBoost model with Platt probability scaling.
            </p>
            {step3Done ? (
              <span className="text-[10px] font-semibold text-emerald-700 flex items-center gap-1 mt-2">
                Executed ✓
              </span>
            ) : step1Done && (
              <span className="text-[10px] font-semibold text-sky-600 flex items-center gap-1 mt-2">
                Run Queue <ArrowRight className="w-3 h-3" />
              </span>
            )}
          </div>

          {/* Step 4 */}
          <div 
            onClick={() => onNavigateToSection('predictions')}
            className={`p-3 rounded-xl border transition-all cursor-pointer ${
              step4Done 
                ? 'bg-white border-emerald-200 hover:border-emerald-300' 
                : 'bg-white/80 border-slate-200 hover:border-slate-300 opacity-90'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Step 4</span>
              {step4Done ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              ) : (
                <Circle className="w-4 h-4 text-slate-300" />
              )}
            </div>
            <div className="text-xs font-bold text-slate-900">Explore Predictions</div>
            <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">
              Inspect failure probabilities, risk categories, and OOD flags.
            </p>
            {step4Done && (
              <span className="text-[10px] font-semibold text-sky-600 flex items-center gap-1 mt-2">
                View Rows <ArrowRight className="w-3 h-3" />
              </span>
            )}
          </div>

          {/* Step 5 */}
          <div 
            onClick={() => onNavigateToSection('reports')}
            className={`p-3 rounded-xl border transition-all cursor-pointer ${
              step5Done 
                ? 'bg-white border-emerald-200 hover:border-emerald-300' 
                : 'bg-white/80 border-slate-200 hover:border-slate-300 opacity-90'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Step 5</span>
              {step5Done ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              ) : (
                <Circle className="w-4 h-4 text-slate-300" />
              )}
            </div>
            <div className="text-xs font-bold text-slate-900">Export Report</div>
            <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">
              Audit benchmarks, threshold optimization, and JSON findings.
            </p>
            {step5Done && (
              <span className="text-[10px] font-semibold text-sky-600 flex items-center gap-1 mt-2">
                Download <ArrowRight className="w-3 h-3" />
              </span>
            )}
          </div>
        </div>
      )}

      {/* Quick Action Footer */}
      {!isCollapsed && !step1Done && (
        <div className="flex flex-wrap items-center justify-between gap-3 pt-1 border-t border-sky-100 text-xs">
          <div className="flex items-center gap-2 text-slate-600">
            <span className="font-semibold text-slate-800">Quick Start:</span>
            <span>Don't have a dataset? Use our canonical AI4I benchmark sample.</span>
          </div>
          <div className="flex items-center gap-2">
            <a
              href="/sample_ai4i_dataset.csv"
              download="sample_ai4i_dataset.csv"
              className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 font-semibold text-slate-700 transition-colors inline-flex items-center gap-1.5 shadow-sm"
            >
              <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
              Download Sample CSV
            </a>
            <button
              onClick={onStartUpload}
              className="px-4 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-700 font-semibold text-white transition-colors inline-flex items-center gap-1.5 shadow-sm"
            >
              <UploadCloud className="w-3.5 h-3.5" />
              Upload Your First Dataset
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
export default OnboardingChecklist;

