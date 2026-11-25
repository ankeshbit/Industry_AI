import React, { useState, useEffect } from 'react';
import {
  api,
  Machine,
  AnalysisResult,
  DatasetItem,
} from '../api';
import {
  UploadCloud,
  Database,
  Activity,
  FileText,
  Clock,
  ArrowRight,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Download,
  BookOpen,
} from 'lucide-react';
import { OnboardingChecklist } from './OnboardingChecklist';
import { NavSection } from './Sidebar';

interface DashboardViewProps {
  onNavigate: (section: NavSection) => void;
  onOpenUpload: (machineId?: string) => void;
  onOpenMachineModal: () => void;
  onSelectAnalysis: (resultId: string) => void;
  onOpenHowItWorks?: () => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  onNavigate,
  onOpenUpload,
  onSelectAnalysis,
  onOpenHowItWorks,
}) => {
  const [loading, setLoading] = useState(true);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [allDatasets, setAllDatasets] = useState<Array<DatasetItem & { machine_name?: string }>>([]);
  const [recentAnalyses, setRecentAnalyses] = useState<AnalysisResult[]>([]);
  const [downloadingSample, setDownloadingSample] = useState(false);

  const fetchOverviewData = async () => {
    setLoading(true);
    try {
      const machList = await api.machines.list();
      setMachines(machList);

      const datasetsAccum: Array<DatasetItem & { machine_name?: string }> = [];
      const analysesAccum: AnalysisResult[] = [];

      for (const m of machList) {
        try {
          const mDatasets = await api.datasets.listForMachine(m.id);
          mDatasets.forEach((ds) => datasetsAccum.push({ ...ds, machine_name: m.name }));
        } catch {
          // ignore
        }
        try {
          const mAnalyses = await api.analyses.getMachineAnalyses(m.id);
          analysesAccum.push(...mAnalyses);
        } catch {
          // ignore
        }
      }

      setAllDatasets(datasetsAccum);
      analysesAccum.sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
      setRecentAnalyses(analysesAccum);
    } catch (err) {
      console.error('Failed to load overview data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverviewData();
  }, []);

  const handleDownloadSample = async () => {
    setDownloadingSample(true);
    try {
      const csv = await api.models.getTemplate('AI4I_2020_PREDICTIVE_MAINTENANCE');
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'sample_operating_dataset.csv';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch {
      alert('Unable to download sample dataset.');
    } finally {
      setDownloadingSample(false);
    }
  };

  const hasData = allDatasets.length > 0 || recentAnalyses.length > 0;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* 1. Welcome & Primary Action Header */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 sm:p-8 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-semibold text-sky-700">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Predictive Maintenance Workspace
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
            Welcome to INDUSTRIA AI
          </h1>
          <p className="text-sm text-slate-600 max-w-xl leading-relaxed">
            Upload machine operating datasets to evaluate equipment health, identify potential failure risks, and understand key contributing factors.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
          <button
            onClick={() => onOpenUpload()}
            className="bg-sky-600 hover:bg-sky-700 text-white font-semibold px-5 py-3 rounded-xl text-sm transition-all shadow-sm flex items-center justify-center gap-2 hover:shadow-md"
          >
            <UploadCloud className="w-4 h-4 text-white" />
            Upload Dataset
          </button>
          <button
            onClick={handleDownloadSample}
            disabled={downloadingSample}
            className="border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 font-medium px-4 py-3 rounded-xl text-xs transition-colors flex items-center justify-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5 text-slate-500" />
            {downloadingSample ? 'Downloading...' : 'Sample CSV'}
          </button>
        </div>
      </div>

      {/* 2. First-Time Guided Journey */}
      <OnboardingChecklist
        stats={{
          totalDatasets: allDatasets.length,
          totalAnalyses: recentAnalyses.length,
          totalMachines: machines.length,
        }}
        onStartUpload={() => onOpenUpload()}
        onOpenHowItWorks={() => onOpenHowItWorks && onOpenHowItWorks()}
        onNavigateToSection={onNavigate}
      />

      {/* 3. Key Metrics (Calm, 3 Numbers Only) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-sky-50 border border-sky-100 flex items-center justify-center text-sky-600 shrink-0">
            <Database className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900">
              {loading ? '...' : allDatasets.length}
            </div>
            <div className="text-xs font-medium text-slate-500">Uploaded Datasets</div>
          </div>
        </div>

        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600 shrink-0">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900">
              {loading ? '...' : recentAnalyses.length}
            </div>
            <div className="text-xs font-medium text-slate-500">Completed Analyses</div>
          </div>
        </div>

        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-600 shrink-0">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900">
              {loading ? '...' : machines.length}
            </div>
            <div className="text-xs font-medium text-slate-500">Monitored Machines</div>
          </div>
        </div>
      </div>

      {/* 4. Simple Explanation of Platform Workflow */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <h2 className="text-base font-bold text-slate-900">How It Works</h2>
            <p className="text-xs text-slate-500">Three simple steps to predict potential machine failures</p>
          </div>
          {onOpenHowItWorks && (
            <button
              onClick={onOpenHowItWorks}
              className="text-xs font-semibold text-sky-600 hover:text-sky-700 flex items-center gap-1"
            >
              <BookOpen className="w-3.5 h-3.5" />
              Detailed Walkthrough
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
          <div className="p-4 rounded-xl bg-slate-50/80 border border-slate-200/80 space-y-2">
            <div className="w-7 h-7 rounded-lg bg-sky-100 text-sky-700 font-bold text-xs flex items-center justify-center">
              1
            </div>
            <div className="text-sm font-bold text-slate-900">Upload Dataset</div>
            <p className="text-xs text-slate-600 leading-relaxed">
              Upload a CSV file containing machine operating readings (temperatures, speed, torque, tool wear).
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50/80 border border-slate-200/80 space-y-2">
            <div className="w-7 h-7 rounded-lg bg-sky-100 text-sky-700 font-bold text-xs flex items-center justify-center">
              2
            </div>
            <div className="text-sm font-bold text-slate-900">Run Analysis</div>
            <p className="text-xs text-slate-600 leading-relaxed">
              Our pre-calibrated AI model evaluates every operating point and flags records at high risk of failure.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50/80 border border-slate-200/80 space-y-2">
            <div className="w-7 h-7 rounded-lg bg-sky-100 text-sky-700 font-bold text-xs flex items-center justify-center">
              3
            </div>
            <div className="text-sm font-bold text-slate-900">Review Insights & Reports</div>
            <p className="text-xs text-slate-600 leading-relaxed">
              Inspect root factors influencing high-risk predictions and export verified reports for maintenance planning.
            </p>
          </div>
        </div>
      </div>

      {/* 5. Recent Activity or Welcoming Empty State */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <h2 className="text-base font-bold text-slate-900">Recent Activity</h2>
          {hasData && (
            <button
              onClick={() => onNavigate('datasets')}
              className="text-xs font-semibold text-sky-600 hover:text-sky-700 flex items-center gap-1"
            >
              View All Datasets <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {loading ? (
          <div className="py-8 text-center text-xs text-slate-500">Loading recent activity...</div>
        ) : !hasData ? (
          /* Welcoming Empty State */
          <div className="py-10 text-center space-y-3">
            <div className="w-14 h-14 rounded-2xl bg-sky-50 border border-sky-100 flex items-center justify-center text-sky-600 mx-auto">
              <UploadCloud className="w-7 h-7" />
            </div>
            <h3 className="text-base font-bold text-slate-900">No Datasets Uploaded Yet</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
              Upload your first machine operating dataset or use our sample dataset to see failure predictions in action.
            </p>
            <div className="pt-2 flex items-center justify-center gap-3">
              <button
                onClick={() => onOpenUpload()}
                className="bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-colors shadow-xs"
              >
                Upload Your First Dataset
              </button>
              <button
                onClick={handleDownloadSample}
                className="border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-medium px-3.5 py-2 rounded-xl transition-colors"
              >
                Download Sample Data
              </button>
            </div>
          </div>
        ) : (
          /* Activity Feed Table */
          <div className="divide-y divide-slate-100">
            {recentAnalyses.slice(0, 5).map((a) => (
              <div key={a.id} className="py-3.5 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-9 h-9 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
                    <Activity className="w-4 h-4" />
                  </div>
                  <div className="truncate">
                    <div className="text-xs font-bold text-slate-900 truncate">
                      Analysis Completed ({((a.summary?.total_rows ?? 0)).toLocaleString()} records evaluated)
                    </div>
                    <div className="text-[11px] text-slate-500 flex items-center gap-2 mt-0.5">
                      <Clock className="w-3 h-3 text-slate-400" />
                      <span>{new Date(a.created_at).toLocaleDateString()} at {new Date(a.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      <span className="text-slate-300">•</span>
                      <span className="text-rose-600 font-semibold">{a.summary?.risk_distribution?.HIGH ?? 0} High Risk</span>
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => {
                    onSelectAnalysis(a.id);
                    onNavigate('analysis');
                  }}
                  className="px-3 py-1.5 rounded-lg border border-slate-200 hover:border-sky-500 hover:bg-sky-50 text-sky-700 text-xs font-semibold transition-all shrink-0 flex items-center gap-1"
                >
                  View Results <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}

            {allDatasets.slice(0, 3).map((ds) => (
              <div key={ds.id} className="py-3.5 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-9 h-9 rounded-lg bg-sky-50 text-sky-600 flex items-center justify-center shrink-0">
                    <Database className="w-4 h-4" />
                  </div>
                  <div className="truncate">
                    <div className="text-xs font-bold text-slate-900 truncate">
                      Dataset: {ds.name}
                    </div>
                    <div className="text-[11px] text-slate-500 flex items-center gap-2 mt-0.5">
                      <Clock className="w-3 h-3 text-slate-400" />
                      <span>{new Date(ds.created_at).toLocaleDateString()}</span>
                      {ds.machine_name && (
                        <>
                          <span className="text-slate-300">•</span>
                          <span>Machine: {ds.machine_name}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => onNavigate('datasets')}
                  className="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium transition-all shrink-0"
                >
                  Inspect Dataset
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default DashboardView;
