import React, { useState, useEffect } from 'react';
import {
  api,
  Machine,
  AnalysisResult,
} from '../api';
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Cpu,
  Download,
  Filter,
  Info,
  Layers,
  Search,
  ShieldAlert,
  Table,
  TrendingUp,
  Wrench,
  Sparkles,
} from 'lucide-react';

interface PredictionsViewProps {
  initialResultId?: string | null;
  onSelectExplainabilityRow?: (row: any) => void;
  onNavigateToExplainability?: () => void;
}

export const PredictionsView: React.FC<PredictionsViewProps> = ({
  initialResultId,
  onSelectExplainabilityRow,
  onNavigateToExplainability,
}) => {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [selectedMachineId, setSelectedMachineId] = useState<string>('');
  const [analyses, setAnalyses] = useState<AnalysisResult[]>([]);
  const [selectedAnalysisId, setSelectedAnalysisId] = useState<string>(initialResultId || '');
  const [currentResult, setCurrentResult] = useState<AnalysisResult | null>(null);
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Table Controls State
  const [searchQuery, setSearchQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState<'ALL' | 'HIGH' | 'MEDIUM' | 'LOW'>('ALL');
  const [oodFilter, setOodFilter] = useState<'ALL' | 'IN_RANGE' | 'OOD_WARNING'>('ALL');
  const [sortField, setSortField] = useState<'probability' | 'row_index'>('probability');
  const [sortAsc, setSortAsc] = useState(false);

  // 1. Initial Load: Machines
  useEffect(() => {
    async function init() {
      try {
        const machs = await api.machines.list();
        setMachines(machs);
        if (machs.length > 0 && !selectedMachineId) {
          setSelectedMachineId(machs[0].id);
        }
      } catch (err) {
        console.error('Failed to load machines:', err);
      }
    }
    init();
  }, []);

  // 2. When selectedMachineId changes, load analyses
  useEffect(() => {
    if (!selectedMachineId) return;
    async function loadAnalyses() {
      try {
        const results = await api.analyses.getMachineAnalyses(selectedMachineId);
        setAnalyses(results);
        if (results.length > 0) {
          // If initialResultId is in results, keep it; else select latest
          const found = results.find((r) => r.id === initialResultId);
          setSelectedAnalysisId(found ? found.id : results[0].id);
        } else {
          setSelectedAnalysisId('');
          setCurrentResult(null);
          setRows([]);
        }
      } catch (err) {
        console.error('Failed to load analyses for machine:', err);
      }
    }
    loadAnalyses();
  }, [selectedMachineId]);

  // 3. When selectedAnalysisId changes, fetch full result and rows
  useEffect(() => {
    if (!selectedAnalysisId) {
      setLoading(false);
      return;
    }
    async function loadResultDetails() {
      setLoading(true);
      try {
        const [resData, rowsData] = await Promise.all([
          api.analyses.get(selectedAnalysisId),
          api.analyses.getRows(selectedAnalysisId),
        ]);
        setCurrentResult(resData);
        setRows(rowsData.top_rows || []);
      } catch (err) {
        console.error('Failed to load analysis details:', err);
      } finally {
        setLoading(false);
      }
    }
    loadResultDetails();
  }, [selectedAnalysisId]);

  const s = currentResult?.summary;

  // Filter & Sort Rows
  const filteredRows = rows
    .filter((r) => {
      const matchesRisk = riskFilter === 'ALL' || r.risk_class === riskFilter;
      const matchesOod =
        oodFilter === 'ALL' ||
        (oodFilter === 'OOD_WARNING' && r.ood_warning) ||
        (oodFilter === 'IN_RANGE' && !r.ood_warning);
      const matchesSearch =
        searchQuery === '' ||
        r.row_index.toString().includes(searchQuery) ||
        JSON.stringify(r.features).toLowerCase().includes(searchQuery.toLowerCase());
      return matchesRisk && matchesOod && matchesSearch;
    })
    .sort((a, b) => {
      const valA = sortField === 'probability' ? a.failure_probability : a.row_index;
      const valB = sortField === 'probability' ? b.failure_probability : b.row_index;
      return sortAsc ? valA - valB : valB - valA;
    });

  // Calculate histogram bins for failure probability distribution (0 to 100% in 10 bins)
  const probabilityBins = Array(10).fill(0);
  rows.forEach((r) => {
    const p = r.failure_probability || 0;
    const binIdx = Math.min(Math.floor(p * 10), 9);
    probabilityBins[binIdx]++;
  });
  const maxBinVal = Math.max(...probabilityBins, 1);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header and Machine/Analysis Selector */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-1 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Predictions & Analytics</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Calibrated operating state evaluations, risk classifications, and confusion matrices
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Machine Selector */}
          <div className="flex items-center gap-1.5 text-xs text-slate-600">
            <span className="font-semibold text-slate-700">Machine:</span>
            <select
              value={selectedMachineId}
              onChange={(e) => setSelectedMachineId(e.target.value)}
              className="text-xs font-medium bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-slate-800 focus:outline-none focus:border-sky-500 shadow-xs"
            >
              {machines.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.asset_tag} — {m.name}
                </option>
              ))}
            </select>
          </div>

          {/* Analysis Result Selector */}
          {analyses.length > 0 && (
            <div className="flex items-center gap-1.5 text-xs text-slate-600">
              <span className="font-semibold text-slate-700">Run:</span>
              <select
                value={selectedAnalysisId}
                onChange={(e) => setSelectedAnalysisId(e.target.value)}
                className="text-xs font-mono font-medium bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-slate-800 focus:outline-none focus:border-sky-500 shadow-xs"
              >
                {analyses.map((a) => (
                  <option key={a.id} value={a.id}>
                    #{a.id.slice(0, 8)} (v{a.result_version} - {a.configuration})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Mandatory Regulatory / Trust Warning Banner */}
      <div className="bg-amber-50 border border-amber-200/90 rounded-xl p-4 text-xs text-amber-900 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="font-bold">
            RELIABILITY STATUS: REFERENCE_ONLY (PRD §8.4.1 Invariant)
          </div>
          <p className="text-amber-800 leading-relaxed text-[11px]">
            Predictions are generated by Stage 3 Production XGBoost (M2) calibrated on synthetic AI4I 2020 simulation data. This model has not yet undergone formal customer plant in-situ sensor validation. Do not connect outputs to autonomous emergency equipment shutdown loops without qualified supervisory engineering approval.
          </p>
        </div>
      </div>

      {!currentResult && !loading && (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500">
          <Activity className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-slate-800">No Analysis Results for this Asset</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
            Upload an operating telemetry dataset CSV for this machine to execute the calibrated ML pipeline.
          </p>
        </div>
      )}

      {currentResult && s && (
        <>
          {/* Summary KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between text-slate-500 mb-1">
                <span className="text-xs font-semibold uppercase tracking-wider">Evaluated Snapshots</span>
                <Table className="w-4 h-4 text-sky-600" />
              </div>
              <div className="text-2xl font-bold text-slate-900 mt-1">
                {s.total_rows.toLocaleString()}
              </div>
              <span className="text-[11px] text-slate-500">Operating telemetry rows</span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between text-slate-500 mb-1">
                <span className="text-xs font-semibold uppercase tracking-wider">Predicted Failures</span>
                <AlertOctagon className="w-4 h-4 text-rose-600" />
              </div>
              <div className="text-2xl font-bold text-rose-600 mt-1">
                {s.predicted_failures}
              </div>
              <span className="text-[11px] text-slate-500">
                {(s.failure_rate * 100).toFixed(1)}% predicted failure rate
              </span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between text-slate-500 mb-1">
                <span className="text-xs font-semibold uppercase tracking-wider">Mean Probability</span>
                <TrendingUp className="w-4 h-4 text-amber-600" />
              </div>
              <div className="text-2xl font-bold text-amber-600 mt-1">
                {(s.mean_failure_probability * 100).toFixed(2)}%
              </div>
              <span className="text-[11px] text-slate-500">Platt sigmoid calibrated</span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between text-slate-500 mb-1">
                <span className="text-xs font-semibold uppercase tracking-wider">Operating Threshold</span>
                <Cpu className="w-4 h-4 text-indigo-600" />
              </div>
              <div className="text-2xl font-bold text-indigo-700 font-mono mt-1">
                &tau;* = {s.threshold_used}
              </div>
              <span className="text-[11px] text-slate-500">Bayes Point: &tau; = 0.0196</span>
            </div>
          </div>

          {/* Visualizations: Histogram & Confusion Matrix */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Probability Distribution Histogram */}
            <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-sm font-bold text-slate-900">
                    Calibrated Failure Probability Distribution
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Frequency histogram of predicted failure probability across 10-percentile bins
                  </p>
                </div>
                <span className="text-xs font-mono text-slate-400">N = {rows.length} rows</span>
              </div>

              {/* Bar Chart Visualization */}
              <div className="h-44 flex items-end gap-2 pt-6 pb-2 px-2 border-b border-slate-200">
                {probabilityBins.map((count, idx) => {
                  const heightPercent = maxBinVal > 0 ? (count / maxBinVal) * 100 : 0;
                  const isHigh = idx >= 5;
                  const isMed = idx >= 1 && idx < 5;

                  return (
                    <div key={idx} className="flex-1 flex flex-col items-center gap-1 group relative">
                      {/* Tooltip */}
                      <div className="opacity-0 group-hover:opacity-100 transition-opacity absolute -top-8 bg-slate-900 text-white text-[10px] px-2 py-0.5 rounded shadow pointer-events-none whitespace-nowrap z-10">
                        {idx * 10}% - {(idx + 1) * 10}%: {count} samples
                      </div>
                      <div className="w-full bg-slate-100 rounded-t h-32 flex items-end overflow-hidden">
                        <div
                          className={`w-full transition-all duration-300 rounded-t ${
                            isHigh ? 'bg-rose-500' : isMed ? 'bg-amber-500' : 'bg-emerald-500'
                          }`}
                          style={{ height: `${heightPercent}%` }}
                        />
                      </div>
                      <span className="text-[10px] font-mono text-slate-400 mt-1">
                        {idx * 10}%
                      </span>
                    </div>
                  );
                })}
              </div>

              <div className="flex items-center justify-center gap-6 mt-4 text-xs">
                <span className="flex items-center gap-1.5 text-slate-600">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Low Risk (0–10%)
                </span>
                <span className="flex items-center gap-1.5 text-slate-600">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> Medium Risk (10–50%)
                </span>
                <span className="flex items-center gap-1.5 text-slate-600">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-500" /> High Risk (&gt;50%)
                </span>
              </div>
            </div>

            {/* Stage 3 Authoritative Confusion Matrix */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-bold text-slate-900">
                  Confirmed Benchmark Matrix
                </h2>
                <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-sky-50 text-sky-800 border border-sky-200">
                  N = 2,000
                </span>
              </div>
              <p className="text-[11px] text-slate-500 mb-4">
                Evaluation performance on locked historical benchmark under $10,000 FN vs $200 FP cost matrix.
              </p>

              {/* 2x2 Matrix Grid */}
              <div className="grid grid-cols-2 gap-2 text-center text-xs">
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
                  <span className="text-[10px] uppercase font-bold text-emerald-800 block">True Positive</span>
                  <span className="text-xl font-bold text-emerald-900 font-mono mt-0.5 block">65</span>
                  <span className="text-[10px] text-emerald-700">Detected Failures</span>
                </div>

                <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg">
                  <span className="text-[10px] uppercase font-bold text-rose-800 block">False Negative</span>
                  <span className="text-xl font-bold text-rose-900 font-mono mt-0.5 block">3</span>
                  <span className="text-[10px] text-rose-700">Missed Failures</span>
                </div>

                <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                  <span className="text-[10px] uppercase font-bold text-amber-800 block">False Positive</span>
                  <span className="text-xl font-bold text-amber-900 font-mono mt-0.5 block">236</span>
                  <span className="text-[10px] text-amber-700">Unneeded Inspections</span>
                </div>

                <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                  <span className="text-[10px] uppercase font-bold text-slate-600 block">True Negative</span>
                  <span className="text-xl font-bold text-slate-900 font-mono mt-0.5 block">1,696</span>
                  <span className="text-[10px] text-slate-500">Normal Operations</span>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 space-y-1 text-xs">
                <div className="flex justify-between text-slate-600">
                  <span>Benchmark Recall on Failures:</span>
                  <span className="font-bold text-slate-900">95.59% (65 / 68)</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Benchmark Precision:</span>
                  <span className="font-bold text-slate-900">21.59%</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Operational Benchmark Cost:</span>
                  <span className="font-mono font-bold text-slate-900">$77,200.00</span>
                </div>
              </div>
            </div>
          </div>

          {/* Prediction Records Table */}
          <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3 bg-slate-50/50">
              <div>
                <h3 className="font-bold text-sm text-slate-900 flex items-center gap-2">
                  <Table className="w-4 h-4 text-sky-600" />
                  Telemetry Snapshot Records (Showing {filteredRows.length} of {rows.length})
                </h3>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Click any row to inspect exact TreeSHAP local feature attribution contributions
                </p>
              </div>

              {/* Table Filters */}
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <input
                  type="text"
                  placeholder="Filter row # or feature..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-white border border-slate-300 rounded-lg px-2.5 py-1 text-xs text-slate-700 placeholder-slate-400 focus:outline-none focus:border-sky-500"
                />

                <select
                  value={riskFilter}
                  onChange={(e) => setRiskFilter(e.target.value as any)}
                  className="bg-white border border-slate-300 rounded-lg px-2 py-1 text-xs text-slate-700 focus:outline-none focus:border-sky-500"
                >
                  <option value="ALL">All Risk Tiers</option>
                  <option value="HIGH">High Risk</option>
                  <option value="MEDIUM">Medium Risk</option>
                  <option value="LOW">Low Risk</option>
                </select>

                <select
                  value={oodFilter}
                  onChange={(e) => setOodFilter(e.target.value as any)}
                  className="bg-white border border-slate-300 rounded-lg px-2 py-1 text-xs text-slate-700 focus:outline-none focus:border-sky-500"
                >
                  <option value="ALL">All Envelopes</option>
                  <option value="IN_RANGE">In Reference Range</option>
                  <option value="OOD_WARNING">OOD Warning</option>
                </select>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">Row #</th>
                    <th className="px-4 py-3">P(Failure)</th>
                    <th className="px-4 py-3">Risk Class</th>
                    <th className="px-4 py-3">Applicability</th>
                    <th className="px-4 py-3">Air Temp (K)</th>
                    <th className="px-4 py-3">Process Temp (K)</th>
                    <th className="px-4 py-3">Speed (rpm)</th>
                    <th className="px-4 py-3">Torque (Nm)</th>
                    <th className="px-4 py-3">Tool Wear (min)</th>
                    <th className="px-4 py-3 text-right">Explain</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {filteredRows.length === 0 ? (
                    <tr>
                      <td colSpan={10} className="px-5 py-8 text-center text-slate-400 font-sans">
                        No rows match your current filter criteria.
                      </td>
                    </tr>
                  ) : (
                    filteredRows.map((r) => {
                      const isHigh = r.risk_class === 'HIGH';
                      const f = r.features;

                      return (
                        <tr
                          key={r.row_index}
                          className="hover:bg-sky-50/50 transition-colors cursor-pointer group"
                          onClick={() => {
                            if (onSelectExplainabilityRow) onSelectExplainabilityRow(r);
                            if (onNavigateToExplainability) onNavigateToExplainability();
                          }}
                        >
                          <td className="px-4 py-2.5 font-bold text-slate-800">
                            #{r.row_index}
                          </td>
                          <td className={`px-4 py-2.5 font-bold ${isHigh ? 'text-rose-600' : 'text-slate-800'}`}>
                            {(r.failure_probability * 100).toFixed(2)}%
                          </td>
                          <td className="px-4 py-2.5">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                r.risk_class === 'HIGH'
                                  ? 'bg-rose-50 text-rose-700 border border-rose-200'
                                  : r.risk_class === 'MEDIUM'
                                  ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                  : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              }`}
                            >
                              {r.risk_class}
                            </span>
                          </td>
                          <td className="px-4 py-2.5">
                            {r.ood_warning ? (
                              <span className="px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-semibold">
                                OOD WARNING
                              </span>
                            ) : (
                              <span className="text-slate-500 text-[11px] font-sans">IN RANGE</span>
                            )}
                          </td>
                          <td className="px-4 py-2.5 text-slate-600">{f['Air temperature [K]'] ?? '-'}</td>
                          <td className="px-4 py-2.5 text-slate-600">{f['Process temperature [K]'] ?? '-'}</td>
                          <td className="px-4 py-2.5 text-slate-600">{f['Rotational speed [rpm]'] ?? '-'}</td>
                          <td className="px-4 py-2.5 text-slate-600 font-semibold">{f['Torque [Nm]'] ?? '-'}</td>
                          <td className="px-4 py-2.5 text-slate-600">{f['Tool wear [min]'] ?? '-'}</td>
                          <td className="px-4 py-2.5 text-right font-sans">
                            <span className="text-sky-600 group-hover:text-sky-800 font-medium inline-flex items-center gap-1 text-[11px]">
                              SHAP <Sparkles className="w-3 h-3" />
                            </span>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
