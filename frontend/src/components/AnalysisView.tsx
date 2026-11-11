import React, { useState, useEffect } from 'react';
import { api, AnalysisResult } from '../api';
import { TrustPanel } from './TrustPanel';
import { Activity, AlertOctagon, TrendingUp, Cpu, Table, ArrowLeft } from 'lucide-react';

interface AnalysisViewProps {
  resultId: string;
  onBack: () => void;
}

export const AnalysisView: React.FC<AnalysisViewProps> = ({ resultId, onBack }) => {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [res, rowsData] = await Promise.all([
          api.analyses.get(resultId),
          api.analyses.getRows(resultId)
        ]);
        setResult(res);
        setRows(rowsData.top_rows);
      } catch (e: any) {
        console.error(e);
        setError(e?.message || 'Failed to load analysis results.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [resultId]);

  if (error) {
    return (
      <div className="p-8 text-center text-rose-300 text-sm space-y-3">
        <div>{error}</div>
        <button onClick={onBack} className="text-xs text-slate-400 hover:text-white underline">Back to Machine Registry</button>
      </div>
    );
  }

  if (loading || !result) {
    return (
      <div className="p-8 text-center text-slate-400 text-sm">
        Loading predictive maintenance analysis results...
      </div>
    );
  }

  const s = result.summary;

  return (
    <div className="space-y-6">
      {/* Top Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Machine Registry
        </button>
        <div className="text-xs text-slate-400 font-mono">
          Analysis ID: {result.id.slice(0, 8)} • v{result.result_version} ({result.configuration})
        </div>
      </div>

      {/* Mandatory Trust Panel */}
      <TrustPanel result={result} />

      {/* High-Level Metric KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-800/80 p-4 rounded-xl border border-slate-700/60 shadow-lg">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Evaluated Rows</span>
            <Table className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-1">{s.total_rows.toLocaleString()}</div>
          <span className="text-xs text-slate-500">Operating snapshots</span>
        </div>

        <div className="bg-slate-800/80 p-4 rounded-xl border border-slate-700/60 shadow-lg">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Predicted Failures</span>
            <AlertOctagon className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold text-rose-400 mt-1">{s.predicted_failures}</div>
          <span className="text-xs text-slate-500">{(s.failure_rate * 100).toFixed(1)}% predicted failure rate</span>
        </div>

        <div className="bg-slate-800/80 p-4 rounded-xl border border-slate-700/60 shadow-lg">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Mean Probability</span>
            <TrendingUp className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400 mt-1">{(s.mean_failure_probability * 100).toFixed(2)}%</div>
          <span className="text-xs text-slate-500">Reference model score</span>
        </div>

        <div className="bg-slate-800/80 p-4 rounded-xl border border-slate-700/60 shadow-lg">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Risk Classes</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex items-center gap-2 mt-2 text-xs font-semibold">
            <span className="text-rose-400">HIGH: {s.risk_distribution.HIGH}</span>
            <span className="text-slate-600">•</span>
            <span className="text-amber-400">MED: {s.risk_distribution.MEDIUM}</span>
            <span className="text-slate-600">•</span>
            <span className="text-emerald-400">LOW: {s.risk_distribution.LOW}</span>
          </div>
          <span className="text-xs text-slate-500 block mt-1">Provisional Threshold: τ = {s.threshold_used}</span>
        </div>
      </div>

      {/* Top Highest Risk Rows Table */}
      <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl overflow-hidden shadow-xl">
        <div className="px-5 py-3.5 border-b border-slate-700/60 flex items-center justify-between">
          <h4 className="font-semibold text-slate-200 text-sm flex items-center gap-2">
            <Cpu className="w-4 h-4 text-sky-400" />
            Top Highest Risk Operating States (Top {rows.length})
          </h4>
          <span className="text-xs text-slate-400 font-mono">Sorted by P(Failure) DESC</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-900/80 text-slate-400 uppercase tracking-wider text-[11px] font-semibold border-b border-slate-700/60">
              <tr>
                <th className="px-4 py-3">Row #</th>
                <th className="px-4 py-3">Failure Prob</th>
                <th className="px-4 py-3">Risk Class</th>
                <th className="px-4 py-3">Domain Status</th>
                <th className="px-4 py-3">Air Temp (K)</th>
                <th className="px-4 py-3">Process Temp (K)</th>
                <th className="px-4 py-3">RPM</th>
                <th className="px-4 py-3">Torque (Nm)</th>
                <th className="px-4 py-3">Tool Wear (min)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/40">
              {rows.map((r) => {
                const isHigh = r.risk_class === 'HIGH';
                const f = r.features;
                return (
                  <tr key={r.row_index} className="hover:bg-slate-700/30 transition-colors font-mono">
                    <td className="px-4 py-2.5 text-slate-400">#{r.row_index}</td>
                    <td className={`px-4 py-2.5 font-bold ${isHigh ? 'text-rose-400' : 'text-slate-200'}`}>
                      {(r.failure_probability * 100).toFixed(2)}%
                    </td>
                    <td className="px-4 py-2.5">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        r.risk_class === 'HIGH' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' :
                        r.risk_class === 'MEDIUM' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' :
                        'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      }`}>
                        {r.risk_class}
                      </span>
                    </td>
                    <td className="px-4 py-2.5">
                      {r.ood_warning ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                          OOD WARNING
                        </span>
                      ) : (
                        <span className="text-slate-400 text-[11px]">IN RANGE</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-slate-300">{f['Air temperature [K]'] ?? '-'}</td>
                    <td className="px-4 py-2.5 text-slate-300">{f['Process temperature [K]'] ?? '-'}</td>
                    <td className="px-4 py-2.5 text-slate-300">{f['Rotational speed [rpm]'] ?? '-'}</td>
                    <td className="px-4 py-2.5 text-slate-300">{f['Torque [Nm]'] ?? '-'}</td>
                    <td className="px-4 py-2.5 text-slate-300">{f['Tool wear [min]'] ?? '-'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

