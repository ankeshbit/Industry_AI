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

  // Provenance-reconciled Stage 3 evaluations from metadata JSON files:
  // 1. Nested-CV Protocol: 25 outer folds x 8,000 observations dev pool
  // 2. Historical Test Benchmark: 2,000 observations locked test set (68 true failures)
  const BENCHMARK_EVALUATIONS = {
    configA: {
      name: 'ai4i_failure_clf_typed (Configuration A - WITH_TYPE)',
      config_code: 'A',
      features_count: 6,
      features: ['Type', 'Air temperature', 'Process temperature', 'Rotational speed', 'Torque', 'Tool wear'],
      boosting_rounds: 74,
      threshold: 0.0100,
      platt_w: 0.9502,
      platt_c: -2.2492,
      nested_cv: {
        ap: '0.71723 ± 0.0615',
        roc_auc: '0.97147 ± 0.0097',
        brier: '0.016128 ± 0.0017',
        cost: '$72,856.00',
        n_outer_folds: 25,
      },
      historical_test: {
        ap: '0.76165',
        roc_auc: '0.96881',
        brier: '0.014822',
        cost: '$77,200.00',
        threshold: '0.0100',
        tp: 65,
        fp: 236,
        fn: 3,
        tn: 1696,
        recall: '95.59%',
        precision: '21.59%',
        f1: '0.3523',
      },
    },
    configB: {
      name: 'ai4i_failure_clf_notype (Configuration B - NO_TYPE)',
      config_code: 'B',
      features_count: 5,
      features: ['Air temperature', 'Process temperature', 'Rotational speed', 'Torque', 'Tool wear'],
      boosting_rounds: 100,
      threshold: 0.0100,
      platt_w: 0.9701,
      platt_c: -2.1979,
      nested_cv: {
        ap: '0.69961 ± 0.0719',
        roc_auc: '0.97198 ± 0.0107',
        brier: '0.016541 ± 0.0019',
        cost: '$74,432.00',
        n_outer_folds: 25,
      },
      historical_test: {
        ap: '0.73822',
        roc_auc: '0.97159',
        brier: '0.014970',
        cost: '$72,400.00',
        threshold: '0.0100',
        tp: 65,
        fp: 212,
        fn: 3,
        tn: 1720,
        recall: '95.59%',
        precision: '23.47%',
        f1: '0.3768',
      },
    },
  };

  const handleExportJSON = () => {
    const reportData = {
      governance_authority: 'PRD v1.2 & Stage 3 Evaluation Architecture v1.4.2 §12',
      export_timestamp: new Date().toISOString(),
      models: BENCHMARK_EVALUATIONS,
      provenance_notes: {
        nested_cv_provenance: 'Outer folds across 8,000-observation development pool under modal configuration selection (§12.2)',
        historical_test_provenance: 'Exploratory assessment on locked 2,000-observation historical test set (§8.1)',
        status: 'REFERENCE_ONLY',
      },
    };
    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `industria_governance_audit_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const currentData = selectedModelIndex === 0 ? BENCHMARK_EVALUATIONS.configA : BENCHMARK_EVALUATIONS.configB;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-1 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <img src="/logo.png" alt="Industry AI Logo" className="w-9 h-9 object-contain shrink-0" />
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Reports & Model Governance</h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Stage 3 evaluation provenance, calibration diagnostics, and benchmark certificates
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExportJSON}
            className="px-3 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 flex items-center gap-1.5 shadow-xs transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-sky-600" />
            <span>Export Governance JSON</span>
          </button>
          <button
            onClick={() => window.print()}
            className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-xs font-semibold text-white flex items-center gap-1.5 shadow-xs transition-colors"
          >
            <FileText className="w-3.5 h-3.5 text-slate-300" />
            <span>Print Summary</span>
          </button>
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
          Production models in this registry are selected deterministically under the <strong>Multi-Objective Statistical Parity Rule (§12.1)</strong> and refitted on the 8,000-observation development pool with disjoint Sub-Train ($N=5,600$), Calibration ($N=1,200$), and Threshold Validation ($N=1,200$) partitions under modal hyperparameter selection (§12.2). All benchmarks retain explicit <strong>REFERENCE_ONLY</strong> provenance.
        </p>
      </div>

      {/* Model Selector Tabs */}
      <div className="flex border-b border-slate-200 gap-4">
        {['Configuration A (WITH_TYPE)', 'Configuration B (NO_TYPE)'].map((tabLabel, idx) => (
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

      {/* Primary Card: Nested CV vs Historical Test Benchmark */}
      <div className="space-y-6">
        {/* Section 1: Repeated Nested-CV Evaluation */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
                  Protocol: 5x5 Nested CV
                </span>
                <h3 className="text-sm font-bold text-slate-900">
                  Development Pool Cross-Validation (25 Outer Folds, N=8,000)
                </h3>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Out-of-sample repeated nested cross-validation generalization metrics across disjoint outer test partitions
              </p>
            </div>
            <span className="text-[11px] font-mono font-semibold text-slate-500">
              PRD §10.1 & Architecture §6
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
              <span className="text-[10px] uppercase font-bold text-slate-500 block">Average Precision (AP)</span>
              <span className="text-base font-bold text-slate-900 font-mono mt-1 block">
                {currentData.nested_cv.ap}
              </span>
              <span className="text-[10px] text-slate-500">Ranking metric mean ± std</span>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
              <span className="text-[10px] uppercase font-bold text-slate-500 block">ROC-AUC</span>
              <span className="text-base font-bold text-slate-900 font-mono mt-1 block">
                {currentData.nested_cv.roc_auc}
              </span>
              <span className="text-[10px] text-slate-500">Discrimination area</span>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
              <span className="text-[10px] uppercase font-bold text-slate-500 block">Brier Score</span>
              <span className="text-base font-bold text-slate-900 font-mono mt-1 block">
                {currentData.nested_cv.brier}
              </span>
              <span className="text-[10px] text-slate-500">Probability calibration</span>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
              <span className="text-[10px] uppercase font-bold text-slate-500 block">Operational Cost</span>
              <span className="text-base font-bold text-slate-900 font-mono mt-1 block">
                {currentData.nested_cv.cost}
              </span>
              <span className="text-[10px] text-slate-500">Under 50:1 cost matrix</span>
            </div>
          </div>
        </div>

        {/* Section 2: Locked Historical Test Benchmark */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
                  Exploratory Reference (N=2,000)
                </span>
                <h3 className="text-sm font-bold text-slate-900">
                  Historical Test Set Benchmark Assessment
                </h3>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Evaluation of refitted production model against the locked 2,000-observation reference partition (68 failures)
              </p>
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
              REFERENCE_ONLY
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Historical Test Metrics */}
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                <span className="text-[10px] uppercase font-bold text-slate-500 block">Historical Test AP</span>
                <span className="text-base font-bold text-sky-800 font-mono mt-0.5 block">
                  {currentData.historical_test.ap}
                </span>
                <span className="text-[10px] text-slate-500">Benchmark AP</span>
              </div>

              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                <span className="text-[10px] uppercase font-bold text-slate-500 block">Historical Test ROC-AUC</span>
                <span className="text-base font-bold text-slate-800 font-mono mt-0.5 block">
                  {currentData.historical_test.roc_auc}
                </span>
                <span className="text-[10px] text-slate-500">Area under curve</span>
              </div>

              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                <span className="text-[10px] uppercase font-bold text-slate-500 block">Failure Recall</span>
                <span className="text-base font-bold text-emerald-800 font-mono mt-0.5 block">
                  {currentData.historical_test.recall}
                </span>
                <span className="text-[10px] text-emerald-700">{currentData.historical_test.tp} / 68 failures</span>
              </div>

              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                <span className="text-[10px] uppercase font-bold text-slate-500 block">Operational Cost</span>
                <span className="text-base font-bold text-slate-900 font-mono mt-0.5 block">
                  {currentData.historical_test.cost}
                </span>
                <span className="text-[10px] text-slate-500">Total cost score</span>
              </div>
            </div>

            {/* Historical Test Confusion Matrix */}
            <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs">
              <span className="font-bold text-slate-800 block text-xs">
                Historical Test Confusion Matrix (&tau;* = 0.0100)
              </span>
              <div className="grid grid-cols-2 gap-2 text-center text-xs">
                <div className="p-2 bg-emerald-100/60 rounded border border-emerald-200">
                  <span className="text-[9px] font-bold text-emerald-800 block uppercase">True Positives</span>
                  <span className="text-sm font-bold font-mono text-emerald-900">{currentData.historical_test.tp}</span>
                </div>
                <div className="p-2 bg-rose-100/60 rounded border border-rose-200">
                  <span className="text-[9px] font-bold text-rose-800 block uppercase">False Negatives</span>
                  <span className="text-sm font-bold font-mono text-rose-900">{currentData.historical_test.fn}</span>
                </div>
                <div className="p-2 bg-amber-100/60 rounded border border-amber-200">
                  <span className="text-[9px] font-bold text-amber-800 block uppercase">False Positives</span>
                  <span className="text-sm font-bold font-mono text-amber-900">{currentData.historical_test.fp}</span>
                </div>
                <div className="p-2 bg-slate-200/60 rounded border border-slate-300">
                  <span className="text-[9px] font-bold text-slate-700 block uppercase">True Negatives</span>
                  <span className="text-sm font-bold font-mono text-slate-900">{currentData.historical_test.tn}</span>
                </div>
              </div>
              <p className="text-[10px] text-slate-500 italic pt-1">
                Notice: Historical reference results do not substitute for plant equipment validation.
              </p>
            </div>
          </div>
        </div>

        {/* Section 3: Platt Sigmoid Calibration & Operational Decision Threshold */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-50 text-sky-700 border border-sky-200">
                  Phase 3 Calibration
                </span>
                <h3 className="text-sm font-bold text-slate-900">
                  Platt Sigmoid Calibration & Operational Decision Threshold
                </h3>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Exact post-hoc calibration formula and operating parameters refitted on independent validation split ($N=1,200$)
              </p>
            </div>
            <span className="text-[11px] font-mono text-slate-500">
              AC-FP-5 & Architecture §5
            </span>
          </div>

          {/* Formula Display Box */}
          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
            <span className="text-xs font-bold text-slate-800 block">
              Parametric Platt Sigmoid Calibration Formula:
            </span>
            <div className="p-3 bg-white border border-slate-200 rounded-lg font-mono text-xs text-slate-900 text-center font-bold">
              P(failure | z) = 1 / (1 + exp(-(w · z + c)))
            </div>
            <p className="text-[11px] text-slate-600 leading-relaxed">
              Where <code className="bg-slate-200/60 px-1 rounded font-bold">z = f(x)</code> is the raw uncalibrated XGBoost tree leaf output margin, <code className="bg-slate-200/60 px-1 rounded font-bold">w</code> is the positive calibration slope weight (<code className="font-bold">w &gt; 0</code>), and <code className="bg-slate-200/60 px-1 rounded font-bold">c</code> is the scalar intercept parameter.
            </p>
          </div>

          {/* Calibrator Parameters Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-3.5 border border-slate-200 rounded-lg space-y-1">
              <span className="text-xs font-bold text-slate-800 block">Tree Boosting Rounds</span>
              <span className="text-xl font-bold font-mono text-indigo-700 block">
                {currentData.boosting_rounds} rounds
              </span>
              <span className="text-[10px] text-slate-500 block">
                Ceiling median across outer folds (§12.2)
              </span>
            </div>

            <div className="p-3.5 border border-slate-200 rounded-lg space-y-1">
              <span className="text-xs font-bold text-slate-800 block">Fitted Platt Parameters</span>
              <span className="text-xs font-mono font-bold text-slate-900 block mt-1">
                w = {currentData.platt_w}, c = {currentData.platt_c}
              </span>
              <span className="text-[10px] text-slate-500 block">
                Fitted on calibration split (N=1,200, 41 positives)
              </span>
            </div>

            <div className="p-3.5 border border-slate-200 rounded-lg space-y-1">
              <span className="text-xs font-bold text-slate-800 block">Operational Decision Threshold (&tau;*)</span>
              <span className="text-xl font-bold font-mono text-sky-700 block">
                &tau;* = {currentData.threshold.toFixed(4)}
              </span>
              <span className="text-[10px] text-slate-500 block">
                Optimal cost cutoff under 50:1 cost matrix
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
export default ReportsView;
