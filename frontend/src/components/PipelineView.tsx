import React, { useState, useEffect } from 'react';
import {
  api,
  Job,
  ModelInfo,
} from '../api';
import {
  GitBranch,
  CheckCircle2,
  AlertCircle,
  Clock,
  Play,
  RotateCw,
  Cpu,
  Layers,
  Database,
  ShieldCheck,
  Activity,
  FileCheck,
  Check,
  XCircle,
  AlertOctagon,
  Info,
} from 'lucide-react';

interface PipelineViewProps {
  onNavigateToPredictions: () => void;
}

export const PipelineView: React.FC<PipelineViewProps> = ({ onNavigateToPredictions }) => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadPipelineData = async () => {
    try {
      const [jobsData, modelsData] = await Promise.all([
        api.jobs.list().catch(() => [] as Job[]),
        api.models.list().catch(() => [] as ModelInfo[]),
      ]);
      setJobs(jobsData);
      setModels(modelsData);
    } catch (err) {
      console.error('Failed to load pipeline data:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadPipelineData();
    // Poll jobs every 5 seconds if there are active jobs
    const interval = setInterval(() => {
      api.jobs.list().then((res) => setJobs(res)).catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    loadPipelineData();
  };

  const activeJob = jobs.find((j) => j.status === 'RUNNING' || j.status === 'QUEUED');

  // Authoritative pipeline execution stages defined in backend analysis service
  const PIPELINE_STAGES = [
    {
      step: 1,
      title: 'Dataset Ingestion & Mapping',
      desc: 'CSV header parsing, column type resolution, and missingness verification',
      icon: Database,
    },
    {
      step: 2,
      title: 'Data Quality & Validation',
      desc: 'Zero-variance checks, float32 bounds parsing, and validation reporting',
      icon: FileCheck,
    },
    {
      step: 3,
      title: 'Domain Applicability Gate',
      desc: 'Out-Of-Distribution boundary checks against AI4I reference operating envelopes',
      icon: ShieldCheck,
    },
    {
      step: 4,
      title: 'Calibrated Inference (M2 v3.0)',
      desc: 'XGBoost tree margin sums passed through Platt Sigmoid Calibrator at tau* = 0.0100',
      icon: Cpu,
    },
    {
      step: 5,
      title: 'TreeSHAP Feature Attribution',
      desc: 'Margin attribution computation enforcing exact additivity (max delta <= 1e-5)',
      icon: Activity,
    },
    {
      step: 6,
      title: 'Provenance & Result Ledger',
      desc: 'Cryptographic result snapshot, audit trail creation, and multi-tenant persistence',
      icon: Layers,
    },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-1 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <img src="/logo.png" alt="Industry AI Logo" className="w-9 h-9 object-contain shrink-0" />
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Machine Learning Pipeline</h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Stage 3 production models, execution lifecycle stages, and asynchronous background worker ledger
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 font-medium px-3.5 py-2 rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-xs"
          >
            <RotateCw className={`w-4 h-4 text-slate-500 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh Queue
          </button>
        </div>
      </div>

      {/* Visual ML Execution Lifecycle Representation */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-sky-600" />
            <h2 className="text-sm font-bold text-slate-900">
              End-to-End Inference Lifecycle Architecture (PRD §8.5 & Architecture §12)
            </h2>
          </div>
          <span className="px-2.5 py-1 rounded bg-slate-100 text-slate-700 font-mono text-[11px] font-semibold">
            PostgreSQL SKIP LOCKED Queue
          </span>
        </div>
        <p className="text-xs text-slate-500 mb-6">
          Each uploaded dataset batch advances deterministically through 6 sequential execution stages verified by tenant-isolated transactions.
        </p>

        {/* Pipeline Stages Stepper */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {PIPELINE_STAGES.map((st) => {
            const Icon = st.icon;
            return (
              <div
                key={st.step}
                className="p-4 rounded-xl border border-slate-200/90 bg-slate-50/50 hover:bg-slate-50 hover:border-slate-300 transition-all flex items-start gap-3 relative"
              >
                <div className="w-7 h-7 rounded-lg bg-white border border-slate-200 text-sky-700 font-bold text-xs flex items-center justify-center shrink-0 shadow-xs">
                  {st.step}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                    <Icon className="w-3.5 h-3.5 text-slate-500" />
                    {st.title}
                  </h3>
                  <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                    {st.desc}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Active Production Models in Registry */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-indigo-600" />
            <h2 className="text-sm font-bold text-slate-900">
              Active Production Models (Database Registry)
            </h2>
          </div>
          <span className="text-xs text-slate-500 font-mono">
            Table: model_versions (stage = 'PRODUCTION')
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
              <tr>
                <th className="px-5 py-3">Registry Name</th>
                <th className="px-5 py-3">Version</th>
                <th className="px-5 py-3">Configuration</th>
                <th className="px-5 py-3">Algorithm</th>
                <th className="px-5 py-3">Stage</th>
                <th className="px-5 py-3">Training Domain</th>
                <th className="px-5 py-3 text-right">Customer Validation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono">
              {models.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-8 text-center text-slate-400 font-sans">
                    {loading ? 'Querying production models...' : 'No production models registered.'}
                  </td>
                </tr>
              ) : (
                models.map((m) => (
                  <tr key={m.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-5 py-3.5 font-bold text-slate-900">
                      {m.registry_name}
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="px-1.5 py-0.5 rounded bg-sky-50 text-sky-800 font-bold text-[10px]">
                        v{m.version}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-slate-700">
                      {m.configuration} ({m.pipeline})
                    </td>
                    <td className="px-5 py-3.5 text-slate-800 font-sans">
                      {m.algorithm}
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                        {m.stage}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-slate-600 font-sans">
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700">
                        {m.training_domain}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-right font-sans">
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                        PENDING PLANT DATA
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Asynchronous Background Job Execution Ledger */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-slate-600" />
            <h2 className="text-sm font-bold text-slate-900">
              Background Job Execution Queue (PRD §8.5, §13.5)
            </h2>
          </div>
          <span className="text-xs text-slate-500 font-mono">
            {jobs.length} jobs in history
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
              <tr>
                <th className="px-5 py-3">Job ID</th>
                <th className="px-5 py-3">Task Type</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Progress</th>
                <th className="px-5 py-3">Current Step / Result</th>
                <th className="px-5 py-3 text-right">Submitted At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {jobs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-slate-400">
                    No asynchronous queue jobs in records.
                  </td>
                </tr>
              ) : (
                jobs.map((j) => {
                  const isDone = j.status === 'SUCCEEDED';
                  const isFail = j.status === 'FAILED';
                  const isRun = j.status === 'RUNNING' || j.status === 'QUEUED';

                  return (
                    <tr key={j.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="px-5 py-3 font-mono text-slate-700">
                        {j.id.slice(0, 8)}...
                      </td>
                      <td className="px-5 py-3 font-semibold text-slate-800">
                        {j.job_type}
                      </td>
                      <td className="px-5 py-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            isDone
                              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                              : isFail
                              ? 'bg-rose-50 text-rose-800 border border-rose-200'
                              : 'bg-sky-50 text-sky-800 border border-sky-200 animate-pulse'
                          }`}
                        >
                          {j.status}
                        </span>
                      </td>
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-20 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                            <div
                              className={`h-1.5 rounded-full ${
                                isDone ? 'bg-emerald-500' : isFail ? 'bg-rose-500' : 'bg-sky-500'
                              }`}
                              style={{ width: `${j.progress_percent}%` }}
                            />
                          </div>
                          <span className="font-mono text-[11px] text-slate-500">
                            {j.progress_percent}%
                          </span>
                        </div>
                      </td>
                      <td className="px-5 py-3 text-slate-600 truncate max-w-xs">
                        {j.current_step || 'Finished'}
                      </td>
                      <td className="px-5 py-3 text-right text-slate-400 font-mono text-[11px]">
                        {new Date(j.created_at).toLocaleTimeString()}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
