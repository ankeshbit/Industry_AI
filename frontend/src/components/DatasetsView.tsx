import React, { useState, useEffect } from 'react';
import {
  api,
  Machine,
  DatasetItem,
  AnalysisResult,
} from '../api';
import {
  Database,
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Download,
  Search,
  Eye,
  Info,
  ArrowRight,
  Play,
  X,
} from 'lucide-react';
import { NavSection } from './Sidebar';

interface DatasetsViewProps {
  onStartUpload: (machineId?: string) => void;
  onNavigateToAnalysis?: (datasetId?: string, machineId?: string) => void;
}

export const DatasetsView: React.FC<DatasetsViewProps> = ({
  onStartUpload,
  onNavigateToAnalysis,
}) => {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [selectedMachineId, setSelectedMachineId] = useState<string>('ALL');
  const [datasets, setDatasets] = useState<Array<DatasetItem & { machine_name?: string; asset_tag?: string; has_analysis?: boolean; analysis_id?: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [downloadingTemplate, setDownloadingTemplate] = useState(false);

  // Preview Modal State
  const [previewVersionId, setPreviewVersionId] = useState<string | null>(null);
  const [previewDatasetName, setPreviewDatasetName] = useState<string>('');
  const [previewData, setPreviewData] = useState<any[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);

  const loadDatasetsData = async () => {
    setLoading(true);
    try {
      const machs = await api.machines.list();
      setMachines(machs);

      const allDatasets: Array<DatasetItem & { machine_name?: string; asset_tag?: string; has_analysis?: boolean; analysis_id?: string }> = [];

      for (const m of machs) {
        try {
          const [mDs, mAnalyses] = await Promise.all([
            api.datasets.listForMachine(m.id).catch(() => []),
            api.analyses.getMachineAnalyses(m.id).catch(() => []),
          ]);

          mDs.forEach((ds) => {
            const matchedAnalysis = mAnalyses.find(
              (a: AnalysisResult) => a.provenance?.dataset?.id === ds.id || a.machine_id === m.id
            );
            allDatasets.push({
              ...ds,
              machine_name: m.name,
              asset_tag: m.asset_tag,
              has_analysis: Boolean(matchedAnalysis),
              analysis_id: matchedAnalysis?.id,
            });
          });
        } catch {
          // ignore
        }
      }

      setDatasets(allDatasets);
    } catch (err) {
      console.error('Error fetching datasets:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDatasetsData();
  }, []);

  const handleDownloadTemplate = async () => {
    setDownloadingTemplate(true);
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
      alert('Unable to download CSV template.');
    } finally {
      setDownloadingTemplate(false);
    }
  };

  const handleOpenPreview = async (versionId: string, dsName: string) => {
    setPreviewVersionId(versionId);
    setPreviewDatasetName(dsName);
    setPreviewLoading(true);
    try {
      const res = await api.datasets.getPreview(versionId);
      setPreviewData(res.preview || []);
    } catch {
      setPreviewData([]);
    } finally {
      setPreviewLoading(false);
    }
  };

  const filteredDatasets = datasets.filter((ds) => {
    const matchesMachine = selectedMachineId === 'ALL' || ds.machine_id === selectedMachineId;
    const matchesSearch =
      ds.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (ds.asset_tag && ds.asset_tag.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (ds.machine_name && ds.machine_name.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesMachine && matchesSearch;
  });

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* 1. Header with Upload Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-sky-600" />
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">My Datasets</h1>
          </div>
          <p className="text-xs text-slate-500">
            Upload, validate, and manage machine operating datasets for predictive maintenance analysis.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleDownloadTemplate}
            disabled={downloadingTemplate}
            className="border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 font-medium px-3.5 py-2 rounded-xl text-xs transition-colors flex items-center gap-1.5 shadow-xs"
          >
            <Download className="w-3.5 h-3.5 text-slate-500" />
            {downloadingTemplate ? 'Downloading...' : 'Sample CSV'}
          </button>
          <button
            onClick={() => onStartUpload(selectedMachineId === 'ALL' ? undefined : selectedMachineId)}
            className="bg-sky-600 hover:bg-sky-700 text-white font-semibold px-4 py-2 rounded-xl text-xs transition-colors flex items-center gap-1.5 shadow-xs"
          >
            <UploadCloud className="w-4 h-4 text-white" />
            Upload Dataset
          </button>
        </div>
      </div>

      {/* 2. Supported Data Requirements Guide (Simplified & Friendly) */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-800">
            <FileSpreadsheet className="w-4 h-4 text-sky-600" />
            Supported Operating CSV Columns
          </div>
          <span className="text-[10px] font-semibold bg-sky-50 text-sky-700 border border-sky-200 px-2 py-0.5 rounded-full">
            6 Standard Columns
          </span>
        </div>
        <p className="text-xs text-slate-600 leading-relaxed">
          Your uploaded CSV should include physical operating readings. Columns are automatically recognized during upload:
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 pt-1 text-xs">
          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80">
            <span className="text-[10px] uppercase font-bold text-slate-400 block">Temperature 1</span>
            <span className="font-semibold text-slate-800">Air Temperature</span>
            <span className="text-[10px] text-slate-500 block font-mono">Kelvin [K]</span>
          </div>
          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80">
            <span className="text-[10px] uppercase font-bold text-slate-400 block">Temperature 2</span>
            <span className="font-semibold text-slate-800">Process Temp</span>
            <span className="text-[10px] text-slate-500 block font-mono">Kelvin [K]</span>
          </div>
          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80">
            <span className="text-[10px] uppercase font-bold text-slate-400 block">Speed</span>
            <span className="font-semibold text-slate-800">Rotational Speed</span>
            <span className="text-[10px] text-slate-500 block font-mono">RPM</span>
          </div>
          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80">
            <span className="text-[10px] uppercase font-bold text-slate-400 block">Force</span>
            <span className="font-semibold text-slate-800">Torque</span>
            <span className="text-[10px] text-slate-500 block font-mono">Nm</span>
          </div>
          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80">
            <span className="text-[10px] uppercase font-bold text-slate-400 block">Wear</span>
            <span className="font-semibold text-slate-800">Tool Wear</span>
            <span className="text-[10px] text-slate-500 block font-mono">Minutes</span>
          </div>
          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80">
            <span className="text-[10px] uppercase font-bold text-slate-400 block">Optional</span>
            <span className="font-semibold text-slate-800">Type</span>
            <span className="text-[10px] text-slate-500 block font-mono">L / M / H</span>
          </div>
        </div>
      </div>

      {/* 3. Search & Machine Filter Controls */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search datasets by name or machine..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-white border border-slate-200 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-sky-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 font-medium shrink-0">Filter Machine:</span>
          <select
            value={selectedMachineId}
            onChange={(e) => setSelectedMachineId(e.target.value)}
            className="bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs text-slate-800 font-medium focus:outline-none focus:border-sky-500"
          >
            <option value="ALL">All Machinery Assets ({machines.length})</option>
            {machines.map((m) => (
              <option key={m.id} value={m.id}>
                {m.asset_tag} — {m.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* 4. Datasets Table / Cards */}
      <div className="bg-white border border-slate-200/90 rounded-2xl shadow-xs overflow-hidden">
        {loading ? (
          <div className="py-12 text-center text-xs text-slate-500">Loading datasets...</div>
        ) : filteredDatasets.length === 0 ? (
          /* Empty State */
          <div className="py-12 text-center space-y-3">
            <div className="w-12 h-12 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-400 mx-auto">
              <Database className="w-6 h-6" />
            </div>
            <div className="text-sm font-bold text-slate-900">No Datasets Found</div>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              {searchQuery ? 'No datasets match your search filter.' : 'Upload a dataset to start predictive maintenance analysis.'}
            </p>
            <button
              onClick={() => onStartUpload()}
              className="bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-colors shadow-xs mt-2"
            >
              Upload Dataset
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/75 border-b border-slate-200 text-slate-600 font-semibold text-[11px]">
                  <th className="py-3 px-4">Dataset Name</th>
                  <th className="py-3 px-4">Associated Machine</th>
                  <th className="py-3 px-4">Upload Date</th>
                  <th className="py-3 px-4">Validation Status</th>
                  <th className="py-3 px-4">Analysis Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredDatasets.map((ds) => {
                  const uploadDate = new Date(ds.created_at).toLocaleDateString();
                  return (
                    <tr key={ds.id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-3.5 px-4">
                        <div className="font-bold text-slate-900">{ds.name}</div>
                        <div className="text-[10px] text-slate-500 font-mono mt-0.5">ID: {ds.id.slice(0, 8)}</div>
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-slate-800">{ds.machine_name || 'Machine'}</div>
                        <div className="text-[10px] text-sky-700 font-mono">{ds.asset_tag}</div>
                      </td>

                      <td className="py-3.5 px-4 text-slate-600">
                        {uploadDate}
                      </td>

                      <td className="py-3.5 px-4">
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                          Compatible
                        </span>
                      </td>

                      <td className="py-3.5 px-4">
                        {ds.has_analysis ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-sky-50 text-sky-800 border border-sky-200">
                            Analyzed
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                            Ready to Analyze
                          </span>
                        )}
                      </td>

                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {(ds.current_version_id || ds.id) && (
                            <button
                              onClick={() => handleOpenPreview(ds.current_version_id || ds.id, ds.name)}
                              className="px-2.5 py-1 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-700 text-xs font-medium transition-colors flex items-center gap-1"
                              title="Preview Dataset Columns & Rows"
                            >
                              <Eye className="w-3.5 h-3.5 text-slate-500" />
                              Preview
                            </button>
                          )}

                          <button
                            onClick={() => onNavigateToAnalysis && onNavigateToAnalysis(ds.id, ds.machine_id)}
                            className="px-3 py-1 rounded-lg bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold transition-colors flex items-center gap-1 shadow-xs"
                          >
                            <Play className="w-3 h-3 fill-white" />
                            {ds.has_analysis ? 'View Results' : 'Run Analysis'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 5. Dataset Preview Modal */}
      {previewVersionId && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-white border border-slate-200 rounded-2xl max-w-4xl w-full p-6 shadow-2xl space-y-4 my-8">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <FileSpreadsheet className="w-5 h-5 text-sky-600" />
                  Dataset Preview: {previewDatasetName}
                </h3>
                <p className="text-xs text-slate-500 mt-0.5 font-mono">
                  Version ID: {previewVersionId}
                </p>
              </div>
              <button
                onClick={() => setPreviewVersionId(null)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {previewLoading ? (
              <div className="py-12 text-center text-xs text-slate-500">Loading dataset rows...</div>
            ) : previewData.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-500">No preview records available for this dataset version.</div>
            ) : (
              <div className="space-y-3">
                <div className="text-xs text-slate-600">
                  Displaying first <span className="font-semibold text-slate-900">{previewData.length} records</span> with detected columns:
                </div>
                <div className="overflow-x-auto max-h-96 border border-slate-200 rounded-xl">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-200 text-slate-700 font-semibold">
                        {Object.keys(previewData[0] || {}).map((col) => (
                          <th key={col} className="py-2.5 px-3 whitespace-nowrap">{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                      {previewData.map((row, idx) => (
                        <tr key={idx} className="hover:bg-slate-50/50">
                          {Object.values(row).map((val: any, cIdx) => (
                            <td key={cIdx} className="py-2 px-3 whitespace-nowrap text-slate-700">
                              {String(val)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <div className="flex justify-end pt-2 border-t border-slate-100">
              <button
                onClick={() => setPreviewVersionId(null)}
                className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DatasetsView;
