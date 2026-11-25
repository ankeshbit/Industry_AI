import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  CheckCircle2, 
  Circle, 
  ArrowRight, 
  BookOpen, 
  ChevronDown, 
  ChevronUp, 
  X,
  UploadCloud,
  FileCheck,
  Play,
  BarChart2,
  Download
} from 'lucide-react';
import { NavSection } from './Sidebar';

interface OnboardingChecklistProps {
  stats: {
    totalDatasets: number;
    totalAnalyses: number;
    totalMachines: number;
  };
  onStartUpload: () => void;
  onOpenHowItWorks: () => void;
  onNavigateToSection: (section: NavSection) => void;
}

export const OnboardingChecklist: React.FC<OnboardingChecklistProps> = ({
  stats,
  onStartUpload,
  onOpenHowItWorks,
  onNavigateToSection,
}) => {
  const [isDismissed, setIsDismissed] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [welcomeReviewed, setWelcomeReviewed] = useState(false);

  useEffect(() => {
    const dismissed = localStorage.getItem('industria_onboarding_dismissed');
    if (dismissed === 'true') {
      setIsDismissed(true);
    }
    const welcomed = localStorage.getItem('industria_welcome_reviewed');
    if (welcomed === 'true') {
      setWelcomeReviewed(true);
    }
  }, []);

  const handleDismiss = () => {
    setIsDismissed(true);
    localStorage.setItem('industria_onboarding_dismissed', 'true');
  };

  const handleMarkWelcome = () => {
    setWelcomeReviewed(true);
    localStorage.setItem('industria_welcome_reviewed', 'true');
    onOpenHowItWorks();
  };

  // 6 Core Guided Steps
  const step1Done = welcomeReviewed || stats.totalDatasets > 0;
  const step2Done = stats.totalDatasets > 0;
  const step3Done = stats.totalDatasets > 0; // Ingestion enforces schema validation
  const step4Done = stats.totalAnalyses > 0;
  const step5Done = stats.totalAnalyses > 0; // Predictions generated & readable
  const step6Done = stats.totalAnalyses > 0; // Downloadable reports available

  const stepsCompleted = [step1Done, step2Done, step3Done, step4Done, step5Done, step6Done].filter(Boolean).length;
  const percentComplete = Math.round((stepsCompleted / 6) * 100);

  if (isDismissed && stepsCompleted === 6) {
    return null;
  }

  if (isDismissed) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl px-4 py-2.5 shadow-xs flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs">
          <Sparkles className="w-4 h-4 text-sky-600" />
          <span className="font-semibold text-slate-800">Quick-Start Guide:</span>
          <span className="text-slate-500">{stepsCompleted} of 6 steps completed ({percentComplete}%)</span>
        </div>
        <button
          onClick={() => {
            setIsDismissed(false);
            localStorage.removeItem('industria_onboarding_dismissed');
          }}
          className="text-xs font-semibold text-sky-600 hover:text-sky-700"
        >
          Resume Guide
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white border border-sky-100 rounded-2xl p-5 shadow-xs space-y-4">
      {/* Top Banner Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div className="flex items-start gap-3.5">
          <img src="/logo.png" alt="Industry AI" className="w-10 h-10 object-contain shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-sky-100 text-sky-800 border border-sky-200 uppercase tracking-wider flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-sky-600" />
                First-Time Setup Guide
              </span>
              <span className="text-xs font-semibold text-slate-500">
                {stepsCompleted} of 6 completed ({percentComplete}%)
              </span>
            </div>
            <h2 className="text-base font-bold text-slate-900 tracking-tight">
              Get Started with Predictive Maintenance
            </h2>
            <p className="text-xs text-slate-600 max-w-2xl leading-relaxed">
              Upload machine operating datasets to evaluate equipment failure risks, understand key contributing factors, and download executive reports.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-start">
          <button
            onClick={handleMarkWelcome}
            className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 transition-colors flex items-center gap-1.5 shadow-xs"
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
            title="Dismiss Guide"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
        <div 
          className="bg-sky-600 h-full rounded-full transition-all duration-500"
          style={{ width: `${percentComplete}%` }}
        />
      </div>

      {/* 6 Step Cards */}
      {!isCollapsed && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-2.5 pt-1">
          {/* Step 1 */}
          <div 
            onClick={handleMarkWelcome}
            className={`p-3 rounded-xl border transition-all cursor-pointer ${
              step1Done 
                ? 'bg-slate-50/70 border-emerald-200 hover:border-emerald-300' 
                : 'bg-sky-50/50 border-sky-300 hover:border-sky-500 shadow-xs'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Step 1</span>
              {step1Done ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <Circle className="w-4 h-4 text-sky-500 animate-pulse" />}
            </div>
            <div className="text-xs font-bold text-slate-900">1. Welcome</div>
            <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">
              Learn the 3-step platform workflow.
            </p>
            {!step1Done && (
              <span className="text-[10px] font-semibold text-sky-600 flex items-center gap-1 mt-2">
                Learn Flow <ArrowRight className="w-3 h-3" />
              </span>
            )}
          </div>

          {/* Step 2 */}
          <div 
            onClick={!step2Done ? onStartUpload : () => onNavigateToSection('datasets')}
            className={`p-3 rounded-xl border transition-all cursor-pointer ${
              step2Done 
                ? 'bg-slate-50/70 border-emerald-200 hover:border-emerald-300' 
                : step1Done ? 'bg-sky-50/50 border-sky-300 hover:border-sky-500 shadow-xs' : 'bg-white border-slate-200 opacity-80'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Step 2</span>
              {step2Done ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <Circle className="w-4 h-4 text-slate-300" />}
            </div>
            <div className="text-xs font-bold text-slate-900">2. Upload Dataset</div>
            <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">
              Ingest operating CSV records for equipment.
            </p>
            {!step2Done && (
              <span className="text-[10px] font-semibold text-sky-600 flex items-center gap-1 mt-2">
                Upload CSV <ArrowRight className="w-3 h-3" />
              </span>
            )}
          </div>

          {/* Step 3 */}
          <div 
            onClick={() => onNavigateToSection('datasets')}
            className={`p-3 rounded-xl border transition-all cursor-pointer ${
              step3Done 
                ? 'bg-slate-50/70 border-emerald-200 hover:border-emerald-300' 
                : 'bg-white border-slate-200 opacity-80'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Step 3</span>
              {step3Done ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <Circle className="w-4 h-4 text-slate-300" />}
            </div>
            <div className="text-xs font-bold text-slate-900">3. Validate Data</div>
            <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">
              Check column ranges and compatibility.
            </p>
            {step3Done ? (
              <span className="text-[10px] font-semibold text-emerald-700 flex items-center gap-1 mt-2">
                Verified ✓
              </span>
            ) : step2Done && (
              <span className="text-[10px] font-semibold text-sky-600 flex items-center gap-1 mt-2">
                View Check <ArrowRight className="w-3 h-3" />
              </span>
            )}
          </div>

          {/* Step 4 */}
          <div 
            onClick={() => onNavigateToSection('analysis')}
            className={`p-3 rounded-xl border transition-all cursor-pointer ${
              step4Done 
                ? 'bg-slate-50/70 border-emerald-200 hover:border-emerald-300' 
                : step2Done ? 'bg-sky-50/50 border-sky-300 hover:border-sky-500 shadow-xs' : 'bg-white border-slate-200 opacity-80'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Step 4</span>
              {step4Done ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <Circle className="w-4 h-4 text-slate-300" />}
            </div>
            <div className="text-xs font-bold text-slate-900">4. Run Analysis</div>
            <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">
              Calculate estimated failure probabilities.
            </p>
            {!step4Done && step2Done && (
              <span className="text-[10px] font-semibold text-sky-600 flex items-center gap-1 mt-2">
                Run Now <ArrowRight className="w-3 h-3" />
              </span>
            )}
          </div>

          {/* Step 5 */}
          <div 
            onClick={() => onNavigateToSection('analysis')}
            className={`p-3 rounded-xl border transition-all cursor-pointer ${
              step5Done 
                ? 'bg-slate-50/70 border-emerald-200 hover:border-emerald-300' 
                : 'bg-white border-slate-200 opacity-80'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Step 5</span>
              {step5Done ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <Circle className="w-4 h-4 text-slate-300" />}
            </div>
            <div className="text-xs font-bold text-slate-900">5. See Results</div>
            <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">
              Review risk bands & contributing factors.
            </p>
            {step5Done && (
              <span className="text-[10px] font-semibold text-emerald-700 flex items-center gap-1 mt-2">
                Reviewed ✓
              </span>
            )}
          </div>

          {/* Step 6 */}
          <div 
            onClick={() => onNavigateToSection('reports')}
            className={`p-3 rounded-xl border transition-all cursor-pointer ${
              step6Done 
                ? 'bg-slate-50/70 border-emerald-200 hover:border-emerald-300' 
                : 'bg-white border-slate-200 opacity-80'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Step 6</span>
              {step6Done ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <Circle className="w-4 h-4 text-slate-300" />}
            </div>
            <div className="text-xs font-bold text-slate-900">6. Get Report</div>
            <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">
              Export summary for maintenance planning.
            </p>
            {step6Done && (
              <span className="text-[10px] font-semibold text-emerald-700 flex items-center gap-1 mt-2">
                Available ✓
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default OnboardingChecklist;
