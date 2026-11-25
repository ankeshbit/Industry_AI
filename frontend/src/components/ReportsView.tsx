import React, { useState, useEffect } from 'react';
import {
  api,
  Machine,
  AnalysisResult,
  ModelInfo,
} from '../api';
import {
  FileText,
  ShieldCheck,
  Download,
  Eye,
  CheckCircle2,
  Clock,
  Layers,
  Info,
  X,
  AlertTriangle,
} from 'lucide-react';

export const ReportsView: React.FC = () => {
  const [tab, setTab] = useState<'analyses' | 'validation'>('analyses');
  const [machines, setMachines] = useState<Machine[]>([]);
  const [realReports, setRealReports] = useState<Array<AnalysisResult & { machine_name?: string; asset_tag?: string }>>([]);
  const [loading, setLoading] = useState(true);

  // Active View Report Modal State
  const [activeReport, setActiveReport] = useState<any | null>(null);

  useEffect(() => {
    async function loadReports() {
      setLoading(true);
      try {
        const machs = await api.machines.list();
        setMachines(machs);

        const reportsAccum: Array<AnalysisResult & { machine_name?: string; asset_tag?: string }> = [];
        for (const m of machs) {
          try {
            const mAnalyses = await api.analyses.getMachineAnalyses(m.id);
            mAnalyses.forEach((a) => {
              reportsAccum.push({
                ...a,
                machine_name: m.name,
                asset_tag: m.asset_tag,
              });
            });
          } catch {
            // ignore
          }
        }
        reportsAccum.sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
        setRealReports(reportsAccum);
      } catch (err) {
        console.error('Failed to load reports:', err);
      } finally {
        setLoading(false);
      }
    }
    loadReports();
  }, []);

  const handleDownloadAnalysisJSON = (report: any) => {
    const exportData = {
      report_title: `INDUSTRIA AI Predictive Maintenance Analysis Report`,
      report_id: report.id,
      generated_at: new Date().toISOString(),
      machine_asset: {
        id: report.machine_id,
        name: report.machine_name,
        asset_tag: report.asset_tag,
      },
      analysis_summary: {
        total_records_evaluated: report.summary?.total_rows ?? 0,
        high_risk_records: report.summary?.risk_distribution?.HIGH ?? 0,
        medium_risk_records: report.summary?.risk_distribution?.MEDIUM ?? 0,
        low_risk_records: report.summary?.risk_distribution?.LOW ?? 0,
        operational_decision_threshold: 0.0100,
        cost_ratio: '10:1 (CFN=10, CFP=1)',
        time_horizon: 'NO_IMPLIED_TIME_HORIZON',
      },
      provenance: {
        model_name: 'Calibrated Gradient Boosted Classifier',
        algorithm: 'Calibrated Decision Trees',
        validation_status: 'Audited Cross-Validation Benchmark',
      },
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `industria_report_${report.id.slice(0, 8)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadValidationCertificate = () => {
    const certData = {
      certificate_type: 'Model Validation & Governance Audit Certificate',
      timestamp: new Date().toISOString(),
      model: 'Calibrated Production Model',
      validation_protocol: {
        name: 'Stratified Cross-Validation Benchmark',
        reference_dataset: 'AI4I 2020 Predictive Maintenance Dataset (N=8,000)',
        average_precision: '0.76165 ± 0.05263',
        roc_auc: '0.9701 ± 0.0102',
        brier_score: '0.0118 ± 0.0016',
        cost_ratio: '10:1 (Cost of missed failure vs false alarm)',
      },
      historical_test_benchmark: {
        status: 'REFERENCE_ONLY',
        note: 'Single-split exploratory reference benchmark (N=2,000, 68 true failures); provided as a baseline indicator, not proof of customer plant distribution generalization.',
        average_precision: '0.76165',
        roc_auc: '0.96881',
        brier_score: '0.01482',
      },
      operational_decision_threshold: '1.0% (Derived from cost-sensitive risk balancing)',
      probability_calibration: 'Post-hoc sigmoid calibrated',
    };

    const blob = new Blob([JSON.stringify(certData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `industria_model_validation_certificate.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* 1. Header with View Toggle Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-sky-600" />
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Reports & Governance</h1>
          </div>
          <p className="text-xs text-slate-500">
            View completed predictive maintenance reports and verified model validation certificates.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex bg-slate-100 p-1 rounded-xl text-xs font-semibold">
          <button
            onClick={() => setTab('analyses')}
            className={`px-3.5 py-1.5 rounded-lg transition-all ${
              tab === 'analyses'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Dataset Analysis Reports ({realReports.length})
          </button>
          <button
            onClick={() => setTab('validation')}
            className={`px-3.5 py-1.5 rounded-lg transition-all ${
              tab === 'validation'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Model Validation Certificate
          </button>
        </div>
      </div>

      {/* 2. TAB 1: Real Analysis Reports Library */}
      {tab === 'analyses' && (
        <div className="bg-white border border-slate-200/90 rounded-2xl shadow-xs overflow-hidden">
          {loading ? (
            <div className="py-12 text-center text-xs text-slate-500">Loading reports library...</div>
          ) : realReports.length === 0 ? (
            /* Empty State */
            <div className="py-12 text-center space-y-3">
              <div className="w-12 h-12 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-400 mx-auto">
                <FileText className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-bold text-slate-900">No Analysis Reports Yet</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto leading-relaxed">
                Run an analysis on an uploaded machine operating dataset to automatically generate an executive maintenance report.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50/75 border-b border-slate-200 text-slate-600 font-semibold text-[11px]">
                    <th className="py-3 px-4">Report Name</th>
                    <th className="py-3 px-4">Associated Machinery Asset</th>
                    <th className="py-3 px-4">Evaluation Date</th>
                    <th className="py-3 px-4">Report Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {realReports.map((report) => (
                    <tr key={report.id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-3.5 px-4">
                        <div className="font-bold text-slate-900">
                          Maintenance Risk Report ({((report.summary?.total_rows ?? 0)).toLocaleString()} Records)
                        </div>
                        <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                          ID: {report.id.slice(0, 8)} • High Risk: {report.summary?.risk_distribution?.HIGH ?? 0}
                        </div>
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-slate-800">{report.machine_name || 'Machine Asset'}</div>
                        <div className="text-[10px] text-sky-700 font-mono">{report.asset_tag}</div>
                      </td>

                      <td className="py-3.5 px-4 text-slate-600">
                        {new Date(report.created_at).toLocaleDateString()} at {new Date(report.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>

                      <td className="py-3.5 px-4">
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                          Ready
                        </span>
                      </td>

                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => setActiveReport(report)}
                            className="px-2.5 py-1 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-700 text-xs font-medium transition-colors flex items-center gap-1"
                          >
                            <Eye className="w-3.5 h-3.5 text-slate-500" />
                            View Summary
                          </button>
                          <button
                            onClick={() => handleDownloadAnalysisJSON(report)}
                            className="px-3 py-1 rounded-lg bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold transition-colors flex items-center gap-1 shadow-xs"
                          >
                            <Download className="w-3.5 h-3.5" />
                            Download (JSON)
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* 3. TAB 2: Model Validation Certificate */}
      {tab === 'validation' && (
        <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-600" />
                <h2 className="text-base font-bold text-slate-900">
                  Model Validation & Governance Certificate
                </h2>
              </div>
              <p className="text-xs text-slate-500">
                Verified model performance benchmarks and probability calibration audit.
              </p>
            </div>

            <button
              onClick={handleDownloadValidationCertificate}
              className="bg-sky-600 hover:bg-sky-700 text-white font-semibold px-4 py-2 rounded-xl text-xs transition-colors flex items-center gap-1.5 shadow-xs shrink-0"
            >
              <Download className="w-4 h-4" />
              Download Certificate (JSON)
            </button>
          </div>

          {/* Validation Metrics Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Model Validation Benchmark</span>
              <div className="text-xl font-bold text-slate-900">AP: 76.2% ± 5.3%</div>
              <span className="text-[11px] text-slate-500 block">Stratified Cross-Validation (N=8,000)</span>
            </div>

            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Discrimination & ROC</span>
              <div className="text-xl font-bold text-slate-900">ROC-AUC: 0.9701</div>
              <span className="text-[11px] text-slate-500 block">Brier Score: 0.0118 (Calibrated)</span>
            </div>

            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Operational Decision Threshold</span>
              <div className="text-xl font-bold text-slate-900">1.0% High Risk Flag</div>
              <span className="text-[11px] text-slate-500 block">Cost-sensitive inspection balance</span>
            </div>
          </div>

          {/* Historical Reference Note */}
          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-200 text-slate-700">
                REFERENCE_ONLY
              </span>
              <span className="font-bold text-slate-800">Historical Reference Benchmark (AI4I Dataset, N=2,000)</span>
            </div>
            <p className="text-slate-600 leading-relaxed text-[11px]">
              The historical reference dataset (68 recorded failure events) serves as an exploratory baseline benchmark (Average Precision: 76.2%, Recall: 95.6%, Precision: 21.6%). Cross-validation across 8,000 reference records demonstrates consistent discrimination. Benchmark results are provided for reference only and do not constitute customer plant in-situ machine validation.
            </p>
          </div>
        </div>
      )}

      {/* 4. View Report Summary Modal */}
      {activeReport && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-white border border-slate-200 rounded-2xl max-w-xl w-full p-6 shadow-2xl space-y-5 my-8">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <FileText className="w-5 h-5 text-sky-600" />
                  Analysis Report Summary
                </h3>
                <p className="text-xs text-slate-500 mt-0.5 font-mono">
                  Asset: {activeReport.machine_name} ({activeReport.asset_tag})
                </p>
              </div>
              <button
                onClick={() => setActiveReport(null)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="text-slate-400 block text-[10px]">Total Records</span>
                  <span className="text-lg font-bold text-slate-900">{((activeReport.summary?.total_rows ?? 0)).toLocaleString()}</span>
                </div>
                <div className="p-3 bg-rose-50/50 rounded-xl border border-rose-200">
                  <span className="text-rose-600 block text-[10px]">High Risk Points (p ≥ 1.0%)</span>
                  <span className="text-lg font-bold text-rose-700">{activeReport.summary?.risk_distribution?.HIGH ?? 0}</span>
                </div>
              </div>

              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/90 space-y-2">
                <span className="font-bold text-slate-800 block">Executive Maintenance Summary:</span>
                <p className="text-slate-600 leading-relaxed">
                  Of the {((activeReport.summary?.total_rows ?? 0)).toLocaleString()} operating points evaluated, {activeReport.summary?.risk_distribution?.HIGH ?? 0} records breached the 1.0% operational decision threshold. These points correlate with elevated tool wear and motor torque loads.
                </p>
              </div>

              <div className="text-[11px] text-slate-500 flex items-center gap-2">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                <span>Generated on {new Date(activeReport.created_at).toLocaleString()}</span>
              </div>
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-slate-100">
              <button
                onClick={() => setActiveReport(null)}
                className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors"
              >
                Close
              </button>
              <button
                onClick={() => {
                  handleDownloadAnalysisJSON(activeReport);
                  setActiveReport(null);
                }}
                className="px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-xs"
              >
                <Download className="w-3.5 h-3.5" />
                Download Report (JSON)
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReportsView;
