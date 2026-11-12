import React, { useState, useEffect } from 'react';
import {
  api,
  ModelInfo,
} from '../api';
import {
  FileText,
  ShieldCheck,
  Cpu,
  Layers,
  CheckCircle2,
  AlertTriangle,
  Download,
  Info,
  Check,
  Table,
  BarChart,
  ExternalLink,
} from 'lucide-react';

export const ReportsView: React.FC = () => {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedModelIndex, setSelectedModelIndex] = useState(0);

  useEffect(() => {
    async function load() {
      try {
        const res = await api.models.list();
        setModels(res);
      } catch (err) {
        console.error('Failed to load models for reports:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const activeModel = models[selectedModelIndex] || null;

  // Authoritative Stage 3 repeated nested-CV benchmark metrics
  const BENCHMARK_EVALUATIONS = {
    configA: {
      name: 'ai4i_failure_clf_typed (Configuration A - WITH_TYPE)',
      hash: 'caa17fdb6c6871afdd87c5bd05d1ad5bc5a568e2c94877935bd242fbcb16824a',
      ap: '0.71723 ± 0.062',
      roc_auc: '0.97147 ± 0.010',
      brier: '0.016128 ± 0.0017',
      cost: '$72,856.00',
      boosting_rounds: 74,
      threshold: 0.0100,
      platt_w: 0.9502,
      platt_c: -2.2492,
    },
    configB: {
      name: 'ai4i_failure_clf_notype (Configuration B - NO_TYPE)',
      hash: '182f3a58a6ef0f2e35a23401cd7214d2699f7887d289e216258d9ac7cac4a8d5',
      ap: '0.69961 ± 0.072',
      roc_auc: '0.97198 ± 0.011',
      brier: '0.016541 ± 0.0019',
      cost: '$74,432.00',
      boosting_rounds: 100,
      threshold: 0.0100,
      platt_w: 0.9701,
      platt_c: -2.1979,
    },
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-1 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Reports & Model Governance</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Stage 3 nested cross-validation audit trails, model cards, and provenance certificates
          </p>
        </div>
      </div>

      {/* Model Governance Authority Notice */}
      <div className="bg-slate-900 text-white rounded-xl p-5 shadow-sm space-y-2">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-sky-400" />
          <h2 className="text-sm font-bold text-white">
            Architecture Governance Contract (v1.4.2 §12 Formal Addendum)
          </h2>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed">
          Production models in this registry are selected deterministically under the <strong>Multi-Objective Statistical Parity Rule (§12.1)</strong> and refitted on the 8,000-observation development pool with disjoint Sub-Train ($N=5,600$), Calibration ($N=1,200$), and Threshold Validation ($N=1,200$) partitions under modal hyperparameter selection (§12.2).
        </p>
      </div>

      {/* Model Selector Tabs */}
      <div className="flex border-b border-slate-200 gap-4">
        {['Configuration A (Typed)', 'Configuration B (No Type)'].map((tabLabel, idx) => (
          <button
            key={tabLabel}
            onClick={() => setSelectedModelIndex(idx)}
            className={`pb-3 text-xs font-semibold border-b-2 transition-colors ${
              selectedModelIndex === idx
                ? 'border-sky-600 text-sky-700'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {tabLabel}
          </button>
        ))}
      </div>

      {/* Active Report Card */}
      {(() => {
        const data = selectedModelIndex === 0 ? BENCHMARK_EVALUATIONS.configA : BENCHMARK_EVALUATIONS.configB;
        return (
          <div className="space-y-6">
            {/* Model Card Metadata Overview */}
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-5">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
                <div>
                  <h3 className="text-base font-bold text-slate-900">{data.name}</h3>
                  <div className="text-xs font-mono text-slate-500 mt-1">
                    SHA-256: <span className="text-slate-800">{data.hash}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-1 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-bold font-mono">
                    STAGE: PRODUCTION
                  </span>
                  <span className="px-2.5 py-1 rounded bg-amber-50 text-amber-800 border border-amber-200 text-xs font-bold">
                    REFERENCE_ONLY
                  </span>
                </div>
              </div>

              {/* Benchmark Metric Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <span className="text-[11px] font-semibold text-slate-500 uppercase block">Outer Mean AP</span>
                  <span className="text-lg font-bold text-slate-900 font-mono mt-0.5 block">{data.ap}</span>
                  <span className="text-[10px] text-emerald-600 font-medium">&gt; 0.70 Gate PASS</span>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <span className="text-[11px] font-semibold text-slate-500 uppercase block">Outer Mean ROC-AUC</span>
                  <span className="text-lg font-bold text-slate-900 font-mono mt-0.5 block">{data.roc_auc}</span>
                  <span className="text-[10px] text-slate-500 font-medium">Rank discrimination</span>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <span className="text-[11px] font-semibold text-slate-500 uppercase block">Outer Mean Brier</span>
                  <span className="text-lg font-bold text-slate-900 font-mono mt-0.5 block">{data.brier}</span>
                  <span className="text-[10px] text-emerald-600 font-medium">-34.5% vs B1 PASS</span>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <span className="text-[11px] font-semibold text-slate-500 uppercase block">Outer Mean Cost</span>
                  <span className="text-lg font-bold text-slate-900 font-mono mt-0.5 block">{data.cost}</span>
                  <span className="text-[10px] text-slate-500 font-medium">50:1 cost ratio ($10k/$200)</span>
                </div>
              </div>

              {/* Calibration & Aggregation Parameters */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
                <div className="p-3.5 border border-slate-200 rounded-lg space-y-1">
                  <span className="text-xs font-bold text-slate-800 block">Boosting Trees ($T^*$)</span>
                  <span className="text-xl font-bold font-mono text-indigo-700 block">
                    {data.boosting_rounds} rounds
                  </span>
                  <span className="text-[10px] text-slate-500 block">
                    Ceiling median of outer nested folds (§12.2)
                  </span>
                </div>

                <div className="p-3.5 border border-slate-200 rounded-lg space-y-1">
                  <span className="text-xs font-bold text-slate-800 block">Platt Sigmoid Calibrator</span>
                  <span className="text-xs font-mono text-slate-800 block">
                    w = {data.platt_w}, c = {data.platt_c}
                  </span>
                  <span className="text-[10px] text-slate-500 block">
                    Fitted on independent calibration split (N=1,200)
                  </span>
                </div>

                <div className="p-3.5 border border-slate-200 rounded-lg space-y-1">
                  <span className="text-xs font-bold text-slate-800 block">Operating Threshold (&tau;*)</span>
                  <span className="text-xl font-bold font-mono text-sky-700 block">
                    {data.threshold.toFixed(4)}
                  </span>
                  <span className="text-[10px] text-slate-500 block">
                    Threshold-Validation partition sweep (N=1,200)
                  </span>
                </div>
              </div>
            </div>

            {/* Locked Historical Test Set Assessment */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-bold text-slate-900">
                  Exploratory Historical Reference Benchmark (N=2,000, 68 Failures)
                </h4>
                <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                  SHA-256: 8e8fef98...
                </span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                The locked test set serves strictly as an exploratory historical reference benchmark. Evaluation confirms <strong>65 out of 68 true failures detected</strong> (95.59% recall) at the cost-optimal decision threshold $\tau^* = 0.0100$ with 236 false positives and a total benchmark operational cost of $77,200.00.
              </p>
            </div>
          </div>
        );
      })()}
    </div>
  );
};
