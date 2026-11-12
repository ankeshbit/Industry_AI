import React, { useState, useEffect } from 'react';
import {
  api,
  Machine,
  Job,
  ModelInfo,
  AnalysisResult,
} from '../api';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Cpu,
  Database,
  Layers,
  Play,
  Plus,
  RefreshCw,
  TrendingUp,
  UploadCloud,
  Wrench,
  XCircle,
  FileText,
  AlertOctagon,
  ArrowRight,
} from 'lucide-react';

interface DashboardViewProps {
  onNavigate: (section: 'dashboard' | 'datasets' | 'pipeline' | 'predictions' | 'explainability' | 'reports' | 'settings') => void;
  onOpenUpload: (machineId?: string) => void;
  onOpenMachineModal: () => void;
  onSelectAnalysis: (resultId: string) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  onNavigate,
  onOpenUpload,
  onOpenMachineModal,
  onSelectAnalysis,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Live Real API State
  const [machines, setMachines] = useState<Machine[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [recentAnalyses, setRecentAnalyses] = useState<AnalysisResult[]>([]);
  const [totalDatasetsCount, setTotalDatasetsCount] = useState<number>(0);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch machines, jobs, and models in parallel
      const [machList, jobsList, modelsList] = await Promise.all([
        api.machines.list(),
        api.jobs.list().catch(() => [] as Job[]),
        api.models.list().catch(() => [] as ModelInfo[]),
      ]);

      setMachines(machList);
      setJobs(jobsList);
      setModels(modelsList);

      // 2. Aggregate datasets count and recent analyses across machines
      let dsCount = 0;
      const analysesAccum: AnalysisResult[] = [];

      for (const m of machList) {
        try {
          const mDatasets = await api.datasets.listForMachine(m.id);
          dsCount += mDatasets.length;
        } catch {
          // Continue if machine has no datasets
        }

        try {
          const mAnalyses = await api.analyses.getMachineAnalyses(m.id);
          analysesAccum.push(...mAnalyses);
        } catch {
          // Continue if machine has no analyses
        }
      }

      setTotalDatasetsCount(dsCount);
      // Sort analyses by created_at DESC
      analysesAccum.sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
      setRecentAnalyses(analysesAccum);
    } catch (err: any) {
      console.error('Failed to load dashboard data:', err);
      setError(err?.message || 'Failed to load workspace data. Please check your connection.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  // Compute Job Metrics
  const succeededJobs = jobs.filter((j) => j.status === 'SUCCEEDED').length;
  const failedJobs = jobs.filter((j) => j.status === 'FAILED').length;
  const runningJobs = jobs.filter((j) => j.status === 'RUNNING' || j.status === 'QUEUED').length;

  // Compute Risk Distribution across latest completed analyses
  let totalPredictedRows = 0;
  let totalPredictedFailures = 0;
  let highRiskCount = 0;
  let mediumRiskCount = 0;
  let lowRiskCount = 0;

  recentAnalyses.forEach((a) => {
    if (a.summary) {
      totalPredictedRows += a.summary.total_rows || 0;
      totalPredictedFailures += a.summary.predicted_failures || 0;
      highRiskCount += a.summary.risk_distribution?.HIGH || 0;
      mediumRiskCount += a.summary.risk_distribution?.MEDIUM || 0;
      lowRiskCount += a.summary.risk_distribution?.LOW || 0;
    }
  });

  const aggregateFailureRate =
    totalPredictedRows > 0 ? (totalPredictedFailures / totalPredictedRows) * 100 : 0;

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-64 bg-slate-200 animate-pulse rounded-lg" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 bg-white border border-slate-200 rounded-xl p-5 shadow-xs animate-pulse">
              <div className="h-4 w-24 bg-slate-200 rounded mb-3" />
              <div className="h-8 w-16 bg-slate-200 rounded" />
            </div>
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 h-72 bg-white border border-slate-200 rounded-xl animate-pulse" />
          <div className="h-72 bg-white border border-slate-200 rounded-xl animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Title & Quick Actions */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-1 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Industrial Overview</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time fleet health, asynchronous processing status, and calibrated ML metrics
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchDashboardData}
            className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg border border-slate-200 transition-colors"
            title="Refresh Metrics"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => onOpenUpload()}
            className="bg-sky-600 hover:bg-sky-700 text-white font-medium px-3.5 py-2 rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-xs"
          >
            <UploadCloud className="w-4 h-4" /> Upload Telemetry
          </button>
          <button
            onClick={onOpenMachineModal}
            className="bg-white hover:bg-slate-50 text-slate-800 border border-slate-300 font-medium px-3.5 py-2 rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-xs"
          >
            <Plus className="w-4 h-4 text-slate-500" /> Add Machine
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertOctagon className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={fetchDashboardData} className="font-semibold underline hover:text-rose-900">
            Retry
          </button>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Machines */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Machinery Assets</span>
            <div className="p-1.5 rounded-md bg-slate-100 text-slate-700">
              <Wrench className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900">{machines.length}</div>
          <div className="text-xs text-slate-500 mt-1 flex items-center justify-between">
            <span>Active registered units</span>
            <button
              onClick={() => onNavigate('settings')}
              className="text-sky-600 hover:text-sky-700 font-medium flex items-center gap-0.5"
            >
              View <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* Total Telemetry Batches */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Telemetry Datasets</span>
            <div className="p-1.5 rounded-md bg-sky-50 text-sky-700">
              <Database className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900">{totalDatasetsCount}</div>
          <div className="text-xs text-slate-500 mt-1 flex items-center justify-between">
            <span>Operating CSV batches</span>
            <button
              onClick={() => onNavigate('datasets')}
              className="text-sky-600 hover:text-sky-700 font-medium flex items-center gap-0.5"
            >
              Manage <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* Pipeline Runs: Success / Failed */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Pipeline Executions</span>
            <div className="p-1.5 rounded-md bg-emerald-50 text-emerald-700">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-3">
            <div className="text-2xl font-bold text-emerald-700">{succeededJobs}</div>
            <div className="text-xs font-semibold text-slate-400">/</div>
            <div className="text-lg font-bold text-rose-600">{failedJobs} failed</div>
          </div>
          <div className="text-xs text-slate-500 mt-1 flex items-center justify-between">
            <span>{runningJobs > 0 ? `${runningJobs} running/queued` : 'All tasks settled'}</span>
            <button
              onClick={() => onNavigate('pipeline')}
              className="text-sky-600 hover:text-sky-700 font-medium flex items-center gap-0.5"
            >
              Pipeline <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* Calibrated Model Version */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Production Models</span>
            <div className="p-1.5 rounded-md bg-indigo-50 text-indigo-700">
              <Cpu className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900">{models.length}</div>
          <div className="text-xs text-slate-500 mt-1 flex items-center justify-between">
            <span className="font-mono text-indigo-700 font-medium">M2 XGBoost v3.0</span>
            <button
              onClick={() => onNavigate('reports')}
              className="text-sky-600 hover:text-sky-700 font-medium flex items-center gap-0.5"
            >
              Audits <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Fleet Health & Recent Activity */}
        <div className="lg:col-span-2 space-y-6">
          {/* Recent Prediction Jobs */}
          <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-slate-500" />
                <h2 className="text-sm font-bold text-slate-800">Recent Queue Activity</h2>
              </div>
              <button
                onClick={() => onNavigate('pipeline')}
                className="text-xs text-sky-600 hover:text-sky-700 font-medium"
              >
                View All
              </button>
            </div>

            <div className="divide-y divide-slate-100">
              {jobs.length === 0 ? (
                <div className="p-8 text-center text-slate-400 text-xs">
                  No background queue jobs recorded. Running analysis or uploads will populate this log.
                </div>
              ) : (
                jobs.slice(0, 5).map((job) => {
                  const isDone = job.status === 'SUCCEEDED';
                  const isFail = job.status === 'FAILED';
                  const isRun = job.status === 'RUNNING' || job.status === 'QUEUED';

                  return (
                    <div key={job.id} className="px-5 py-3 flex items-center justify-between text-xs">
                      <div className="flex items-center gap-3 min-w-0">
                        <span
                          className={`w-2 h-2 rounded-full shrink-0 ${
                            isDone ? 'bg-emerald-500' : isFail ? 'bg-rose-500' : 'bg-sky-500 animate-ping'
                          }`}
                        />
                        <div className="truncate">
                          <span className="font-semibold text-slate-800">{job.job_type}</span>
                          <span className="text-slate-400 font-mono text-[11px] ml-2 truncate">
                            ID: {job.id.slice(0, 8)}
                          </span>
                          <div className="text-[11px] text-slate-500 truncate mt-0.5">
                            {job.current_step || 'Execution complete'}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 shrink-0">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold tracking-wide ${
                            isDone
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : isFail
                              ? 'bg-rose-50 text-rose-700 border border-rose-200'
                              : 'bg-sky-50 text-sky-700 border border-sky-200'
                          }`}
                        >
                          {job.status}
                        </span>
                        <span className="text-[11px] text-slate-400 font-mono hidden sm:inline">
                          {new Date(job.created_at).toLocaleTimeString()}
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Machine Fleet Status Table */}
          <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
              <div className="flex items-center gap-2">
                <Wrench className="w-4 h-4 text-slate-500" />
                <h2 className="text-sm font-bold text-slate-800">Physical Asset Registry Status</h2>
              </div>
              <button
                onClick={() => onNavigate('settings')}
                className="text-xs text-sky-600 hover:text-sky-700 font-medium"
              >
                Manage Equipment
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                  <tr>
                    <th className="px-5 py-2.5">Asset Tag</th>
                    <th className="px-5 py-2.5">Machine Name</th>
                    <th className="px-5 py-2.5">Category</th>
                    <th className="px-5 py-2.5">Status</th>
                    <th className="px-5 py-2.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {machines.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-5 py-8 text-center text-slate-400 text-xs">
                        No machinery registered. Register an asset to ingest telemetry.
                      </td>
                    </tr>
                  ) : (
                    machines.slice(0, 5).map((m) => (
                      <tr key={m.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="px-5 py-2.5 font-mono font-semibold text-slate-800">
                          {m.asset_tag}
                        </td>
                        <td className="px-5 py-2.5 text-slate-700">{m.name}</td>
                        <td className="px-5 py-2.5 text-slate-500">{m.category_code}</td>
                        <td className="px-5 py-2.5">
                          {m.archived_at ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600">
                              ARCHIVED
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                              ONLINE
                            </span>
                          )}
                        </td>
                        <td className="px-5 py-2.5 text-right">
                          <button
                            onClick={() => onOpenUpload(m.id)}
                            className="text-sky-600 hover:text-sky-800 font-medium"
                          >
                            Upload CSV
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right Column: Fleet Failure Risk & Quick Actions */}
        <div className="space-y-6">
          {/* Failure Distribution Overview */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
            <h2 className="text-sm font-bold text-slate-800 flex items-center gap-2 mb-3">
              <Activity className="w-4 h-4 text-sky-600" />
              Fleet Failure Risk Distribution
            </h2>
            <p className="text-xs text-slate-500 mb-4">
              Calibrated out-of-sample risk classification across recent telemetry batches
            </p>

            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="font-medium text-slate-700 flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-rose-500" /> High Risk (P &ge; 50%)
                  </span>
                  <span className="font-semibold text-rose-700">{highRiskCount}</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-rose-500 h-2 rounded-full transition-all duration-500"
                    style={{
                      width: `${totalPredictedRows > 0 ? (highRiskCount / totalPredictedRows) * 100 : 0}%`,
                    }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="font-medium text-slate-700 flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> Medium Risk (10% &le; P &lt; 50%)
                  </span>
                  <span className="font-semibold text-amber-700">{mediumRiskCount}</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-amber-500 h-2 rounded-full transition-all duration-500"
                    style={{
                      width: `${totalPredictedRows > 0 ? (mediumRiskCount / totalPredictedRows) * 100 : 0}%`,
                    }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="font-medium text-slate-700 flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Low Risk (P &lt; 10%)
                  </span>
                  <span className="font-semibold text-emerald-700">{lowRiskCount}</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-emerald-500 h-2 rounded-full transition-all duration-500"
                    style={{
                      width: `${totalPredictedRows > 0 ? (lowRiskCount / totalPredictedRows) * 100 : 0}%`,
                    }}
                  />
                </div>
              </div>
            </div>

            <div className="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>Overall Predicted Failures</span>
              <span className="font-bold text-slate-800">
                {totalPredictedFailures} / {totalPredictedRows} ({aggregateFailureRate.toFixed(1)}%)
              </span>
            </div>
          </div>

          {/* Quick Actions Card */}
          <div className="bg-slate-900 text-white rounded-xl p-5 shadow-sm space-y-4">
            <div>
              <h3 className="font-bold text-sm text-white flex items-center gap-2">
                <Layers className="w-4 h-4 text-sky-400" />
                Operational Shortcuts
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Standard workflows for plant telemetry evaluation
              </p>
            </div>

            <div className="space-y-2">
              <button
                onClick={() => onOpenUpload()}
                className="w-full bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold px-3 py-2.5 rounded-lg flex items-center justify-between transition-colors"
              >
                <span className="flex items-center gap-2">
                  <UploadCloud className="w-4 h-4 text-sky-400" /> Ingest Operating Telemetry
                </span>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
              </button>

              <button
                onClick={() => onNavigate('pipeline')}
                className="w-full bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold px-3 py-2.5 rounded-lg flex items-center justify-between transition-colors"
              >
                <span className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-indigo-400" /> View Production Models
                </span>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
              </button>

              <button
                onClick={() => onNavigate('predictions')}
                className="w-full bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold px-3 py-2.5 rounded-lg flex items-center justify-between transition-colors"
              >
                <span className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-emerald-400" /> Analytics & Risk Curves
                </span>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
