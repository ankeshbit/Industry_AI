import React from 'react';
import { Menu, ChevronRight, Database, Cpu, UploadCloud, CheckCircle2, HelpCircle } from 'lucide-react';
import { NavSection } from './Sidebar';

interface HeaderProps {
  activeSection: NavSection;
  subTitle?: string;
  onOpenMobile: () => void;
  onQuickUpload: () => void;
  onOpenHowItWorks?: () => void;
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
  onOpenHowItWorks,
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

        <div className="flex items-center gap-2 lg:hidden">
          <img src="/logo.png" alt="Industry AI Logo" className="w-6 h-6 object-contain" />
          <span className="font-bold text-xs text-slate-900 tracking-tight">INDUSTRIA AI</span>
        </div>

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

      {/* Right: How It Works & Quick Actions */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* How It Works Guide Trigger */}
        {onOpenHowItWorks && (
          <button
            onClick={onOpenHowItWorks}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 transition-colors shadow-xs"
            title="Open 3-Step Predictive Maintenance Architecture Guide"
          >
            <HelpCircle className="w-3.5 h-3.5 text-sky-600" />
            <span className="hidden sm:inline">How It Works</span>
          </button>
        )}

        {/* Quick Upload Action */}
        <button
          onClick={onQuickUpload}
          className="bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg flex items-center gap-1.5 shadow-xs transition-colors"
        >
          <UploadCloud className="w-3.5 h-3.5 text-white" />
          <span className="hidden sm:inline">Upload Dataset</span>
          <span className="sm:hidden">Upload</span>
        </button>
      </div>
    </header>
  );
};
export default Header;
