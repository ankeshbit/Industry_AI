import React from 'react';
import {
  LayoutDashboard,
  Database,
  GitBranch,
  Activity,
  Sparkles,
  FileText,
  Settings,
  Shield,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Building,
  User as UserIcon,
} from 'lucide-react';
import { User } from '../api';

export type NavSection =
  | 'dashboard'
  | 'datasets'
  | 'pipeline'
  | 'predictions'
  | 'explainability'
  | 'reports'
  | 'settings';

interface SidebarProps {
  activeSection: NavSection;
  onSelectSection: (section: NavSection) => void;
  currentUser: User;
  onLogout: () => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  isMobileOpen: boolean;
  onCloseMobile: () => void;
}

interface NavItem {
  id: NavSection;
  label: string;
  icon: React.ElementType;
  badge?: string;
  description: string;
}

const NAV_ITEMS: NavItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: LayoutDashboard,
    description: 'Fleet health & workspace telemetry overview',
  },
  {
    id: 'datasets',
    label: 'Datasets',
    icon: Database,
    description: 'Telemetry uploads, schemas & validation',
  },
  {
    id: 'pipeline',
    label: 'ML Pipeline',
    icon: GitBranch,
    description: 'Lifecycle stages, model registry & jobs',
  },
  {
    id: 'predictions',
    label: 'Predictions & Analytics',
    icon: Activity,
    description: 'Calibrated failure risk & evaluation curves',
  },
  {
    id: 'explainability',
    label: 'Explainability',
    icon: Sparkles,
    description: 'TreeSHAP margin attributions & feature impact',
  },
  {
    id: 'reports',
    label: 'Reports & Governance',
    icon: FileText,
    description: 'Model cards, benchmark audits & provenance',
  },
  {
    id: 'settings',
    label: 'Settings & Machinery',
    icon: Settings,
    description: 'Equipment registry & workspace configuration',
  },
];

export const Sidebar: React.FC<SidebarProps> = ({
  activeSection,
  onSelectSection,
  currentUser,
  onLogout,
  isCollapsed,
  onToggleCollapse,
  isMobileOpen,
  onCloseMobile,
}) => {
  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-40 lg:hidden"
          onClick={onCloseMobile}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed lg:static top-0 bottom-0 left-0 z-50 flex flex-col bg-white border-r border-slate-200 transition-all duration-300 ease-in-out ${
          isMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        } ${isCollapsed ? 'w-[72px]' : 'w-64'}`}
      >
        {/* Brand Header */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-slate-200 bg-white">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-9 h-9 rounded-lg bg-slate-900 flex items-center justify-center text-white shrink-0 shadow-sm">
              <Shield className="w-5 h-5 text-sky-400" />
            </div>
            {!isCollapsed && (
              <div className="flex flex-col truncate">
                <div className="flex items-center gap-1.5">
                  <span className="font-bold text-sm tracking-tight text-slate-900 font-sans">
                    INDUSTRIA AI
                  </span>
                  <span className="px-1.5 py-0.2 text-[9px] font-semibold bg-sky-100 text-sky-800 rounded">
                    v3.0
                  </span>
                </div>
                <span className="text-[10px] text-slate-500 font-medium truncate">
                  Predictive Maintenance
                </span>
              </div>
            )}
          </div>

          <button
            onClick={onToggleCollapse}
            className="hidden lg:flex p-1.5 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
            title={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          >
            {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Organization / Tenant Pill */}
        {!isCollapsed && (
          <div className="px-3 pt-3 pb-1">
            <div className="px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-lg flex items-center gap-2">
              <Building className="w-4 h-4 text-slate-500 shrink-0" />
              <div className="truncate flex-1">
                <div className="text-[11px] font-semibold text-slate-800 truncate">
                  {currentUser.organisation.name}
                </div>
                <div className="text-[9px] text-slate-500 font-mono truncate">
                  Tenant: {currentUser.organisation.slug}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Navigation Items */}
        <nav className="flex-1 px-3 py-3 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.id;

            return (
              <button
                key={item.id}
                onClick={() => {
                  onSelectSection(item.id);
                  onCloseMobile();
                }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all group relative ${
                  isActive
                    ? 'bg-sky-50 text-sky-900 font-semibold border-l-4 border-sky-600 shadow-xs'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                } ${isCollapsed ? 'justify-center px-0' : ''}`}
                title={isCollapsed ? item.label : undefined}
              >
                <Icon
                  className={`w-4 h-4 shrink-0 transition-colors ${
                    isActive ? 'text-sky-600' : 'text-slate-400 group-hover:text-slate-600'
                  }`}
                />
                {!isCollapsed && (
                  <span className="truncate text-left flex-1">{item.label}</span>
                )}
                {!isCollapsed && item.badge && (
                  <span className="px-1.5 py-0.5 text-[9px] font-bold rounded-full bg-slate-200 text-slate-700">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* User Profile & Sign Out Footer */}
        <div className="p-3 border-t border-slate-200 bg-slate-50/70">
          {!isCollapsed ? (
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-slate-700 shrink-0 font-bold text-xs">
                  <UserIcon className="w-4 h-4 text-slate-500" />
                </div>
                <div className="truncate">
                  <div className="text-xs font-semibold text-slate-900 truncate">
                    {currentUser.full_name || currentUser.email}
                  </div>
                  <div className="text-[10px] text-slate-500 font-mono truncate flex items-center gap-1">
                    <span className="px-1 py-0.2 rounded bg-amber-100 text-amber-800 text-[9px] font-semibold">
                      {currentUser.role}
                    </span>
                  </div>
                </div>
              </div>
              <button
                onClick={onLogout}
                className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                title="Sign Out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="flex justify-center">
              <button
                onClick={onLogout}
                className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                title="Sign Out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </aside>
    </>
  );
};
