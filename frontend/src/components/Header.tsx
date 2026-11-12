import React from 'react';
import { Menu, ChevronRight, Database, Cpu, UploadCloud, CheckCircle2 } from 'lucide-react';
import { NavSection } from './Sidebar';

interface HeaderProps {
  activeSection: NavSection;
  subTitle?: string;
  onOpenMobile: () => void;
  onQuickUpload: () => void;
}

const SECTION_TITLES: Record<NavSection, string> = {
  dashboard: 'Dashboard',
  datasets: 'Dataset Management',
  pipeline: 'ML Execution Pipeline',
  predictions: 'Predictions & Analytics',
  explainability: 'Explainability & Feature Attribution',
  reports: 'Reports & Model Governance',
  settings: 'Settings & Machinery Registry',
};

export const Header: React.FC<HeaderProps> = ({
  activeSection,
  subTitle,
  onOpenMobile,
  onQuickUpload,
}) => {
  return (
    <header className="h-16 bg-white border-b border-slate-200 sticky top-0 z-30 flex items-center justify-between px-4 sm:px-6">
      {/* Left: Mobile Toggle & Breadcrumbs */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobile}
          className="lg:hidden p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg"
          aria-label="Open Navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        <nav className="flex items-center gap-1.5 text-xs text-slate-500 font-medium overflow-hidden">
          <span className="text-slate-400 hover:text-slate-600 transition-colors hidden sm:inline">
            Workspace
          </span>
          <ChevronRight className="w-3.5 h-3.5 text-slate-300 hidden sm:inline" />
          <span className="font-semibold text-slate-800">
            {SECTION_TITLES[activeSection]}
          </span>
          {subTitle && (
            <>
              <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
              <span className="text-sky-700 font-medium truncate max-w-[200px] sm:max-w-none">
                {subTitle}
              </span>
            </>
          )}
        </nav>
      </div>

      {/* Right: Environment Status & Quick Actions */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Neon DB Status */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-50 border border-emerald-200/80 text-[11px] font-medium text-emerald-800">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <Database className="w-3 h-3 text-emerald-600" />
          <span>Neon PostgreSQL</span>
        </div>

        {/* Model Engine Badge */}
        <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-sky-50 border border-sky-200/80 text-[11px] font-medium text-sky-800">
          <Cpu className="w-3 h-3 text-sky-600" />
          <span>M2 XGBoost v3.0.0</span>
        </div>

        {/* Quick Upload Action */}
        <button
          onClick={onQuickUpload}
          className="bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold px-3 py-1.5 rounded-lg flex items-center gap-1.5 shadow-xs transition-colors"
        >
          <UploadCloud className="w-3.5 h-3.5 text-sky-400" />
          <span className="hidden sm:inline">Upload Telemetry</span>
          <span className="sm:hidden">Upload</span>
        </button>
      </div>
    </header>
  );
};
