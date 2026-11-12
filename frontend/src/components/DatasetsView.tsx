import React, { useState, useEffect } from 'react';
import {
  api,
  Machine,
  DatasetItem,
} from '../api';
import {
  Database,
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  Download,
  Filter,
  Search,
  Eye,
  Info,
  Layers,
  Wrench,
  Check,
  AlertCircle,
  ArrowRight,
} from 'lucide-react';

interface DatasetsViewProps {
  onStartUpload: (machineId?: string) => void;
  onSelectMachineUpload?: (machineId: string) => void;
}

export const DatasetsView: React.FC<DatasetsViewProps> = ({ onStartUpload }) => {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [selectedMachineId, setSelectedMachineId] = useState<string>('ALL');
  const [datasets, setDatasets] = useState<Array<DatasetItem & { machine_name?: string; asset_tag?: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  // Schema Template State
  const [downloadingTemplate, setDownloadingTemplate] = useState(false);

  // Active Preview State
  const [previewVersionId, setPreviewVersionId] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<any[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);

  const loadDatasetsData = async () => {
    setLoading(true);
    try {
      const machs = await api.machines.list();
      setMachines(machs);

      const allDatasets: Array<DatasetItem & { machine_name?: string; asset_tag?: string }> = [];

      for (const m of machs) {
        try {
          const mDs = await api.datasets.listForMachine(m.id);
          mDs.forEach((ds) => {
            allDatasets.push({
              ...ds,
              machine_name: m.name,
              asset_tag: m.asset_tag,
            });
          });
        } catch {
          // ignore individual fetch errors
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
      link.setAttribute('href', url);
      link.setAttribute('download', 'industria_telemetry_template.csv');
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      alert('Failed to download template. Please check network connectivity.');
    } finally {
      setDownloadingTemplate(false);
    }
  };

  const handlePreviewDataset = async (versionId: string) => {
    setPreviewVersionId(versionId);
    setPreviewLoading(true);
    try {
      const res = await api.datasets.getPreview(versionId);
      setPreviewData(res.preview || []);
    } catch (err) {
      console.error('Failed to preview dataset version:', err);
      setPreviewData([]);
    } finally {
      setPreviewLoading(false);
    }
  };

  const filteredDatasets = datasets.filter((ds) => {
    const matchesMachine =
      selectedMachineId === 'ALL' || ds.machine_id === selectedMachineId;
    const matchesSearch =
      ds.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (ds.asset_tag && ds.asset_tag.toLowerCase().includes(searchQuery.toLowerCase())) ||
      ds.id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesMachine && matchesSearch;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-1 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Dataset Management</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Operating telemetry ingestion, schema conformity, and column mapping history
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleDownloadTemplate}
            disabled={downloadingTemplate}
            className="bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 font-medium px-3.5 py-2 rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-xs"
          >
            <Download className="w-4 h-4 text-slate-500" />
            {downloadingTemplate ? 'Downloading...' : 'Download CSV Template'}
          </button>
          <button
            onClick={() => onStartUpload(selectedMachineId === 'ALL' ? undefined : selectedMachineId)}
            className="bg-sky-600 hover:bg-sky-700 text-white font-medium px-3.5 py-2 rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-xs"
          >
            <UploadCloud className="w-4 h-4" /> Upload New Batch
          </button>
        </div>
      </div>

      {/* Schema Contract & Validation Requirements Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <div className="flex items-start justify-between gap-4 mb-3">
          <div>
            <div className="flex items-center gap-2">
              <FileSpreadsheet className="w-4 h-4 text-sky-600" />
              <h2 className="text-sm font-bold text-slate-900">
                AI4I 2020 Standard Telemetry Specification (PRD §8.2.2)
              </h2>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Datasets must satisfy the feature schema below to pass compatibility gates and execute calibrated inference.
            </p>
          </div>
          <span className="px-2 py-0.5 rounded bg-sky-50 text-sky-700 border border-sky-200 text-[10px] font-semibold tracking-wide">
            STRICT VALIDATION
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-2">
          <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-lg">
            <span className="text-[10px] uppercase font-bold text-slate-400 block">Required #1</span>
            <span className="text-xs font-semibold text-slate-800 block mt-0.5">Air temperature</span>
            <span className="text-[11px] font-mono text-slate-500">[K] (float)</span>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-lg">
            <span className="text-[10px] uppercase font-bold text-slate-400 block">Required #2</span>
            <span className="text-xs font-semibold text-slate-800 block mt-0.5">Process temperature</span>
            <span className="text-[11px] font-mono text-slate-500">[K] (float)</span>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-lg">
            <span className="text-[10px] uppercase font-bold text-slate-400 block">Required #3</span>
            <span className="text-xs font-semibold text-slate-800 block mt-0.5">Rotational speed</span>
            <span className="text-[11px] font-mono text-slate-500">[rpm] (int/float)</span>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-lg">
            <span className="text-[10px] uppercase font-bold text-slate-400 block">Required #4</span>
            <span className="text-xs font-semibold text-slate-800 block mt-0.5">Torque</span>
            <span className="text-[11px] font-mono text-slate-500">[Nm] (float)</span>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-lg">
            <span className="text-[10px] uppercase font-bold text-slate-400 block">Required #5</span>
            <span className="text-xs font-semibold text-slate-800 block mt-0.5">Tool wear</span>
            <span className="text-[11px] font-mono text-slate-500">[min] (int/float)</span>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-lg">
            <span className="text-[10px] uppercase font-bold text-slate-400 block">Optional #6</span>
            <span className="text-xs font-semibold text-slate-800 block mt-0.5">Type</span>
            <span className="text-[11px] font-mono text-slate-500">L / M / H (Config A)</span>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-3 border border-slate-200 rounded-xl shadow-xs">
        <div className="flex items-center gap-2 flex-1 min-w-[240px]">
          <Search className="w-4 h-4 text-slate-400 ml-1" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by dataset name, asset tag, or ID..."
            className="w-full text-xs text-slate-800 placeholder-slate-400 bg-transparent focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-slate-600">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <span className="font-medium">Filter Machine:</span>
          </div>
          <select
            value={selectedMachineId}
            onChange={(e) => setSelectedMachineId(e.target.value)}
            className="text-xs font-medium bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 focus:outline-none focus:border-sky-500"
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

      {/* Dataset Version Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
              <tr>
                <th className="px-5 py-3">Dataset Collection</th>
                <th className="px-5 py-3">Associated Machine</th>
                <th className="px-5 py-3">Type</th>
                <th className="px-5 py-3">Ingested At</th>
                <th className="px-5 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-slate-400">
                    Loading datasets from Neon PostgreSQL...
                  </td>
                </tr>
              ) : filteredDatasets.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-slate-400">
                    No operating telemetry datasets match your filter. Click "Upload New Batch" to upload a CSV.
                  </td>
                </tr>
              ) : (
                filteredDatasets.map((ds) => (
                  <tr key={ds.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-5 py-3 font-semibold text-slate-800">
                      <div className="flex items-center gap-2">
                        <FileSpreadsheet className="w-4 h-4 text-slate-400" />
                        <div>
                          <span>{ds.name}</span>
                          <span className="block text-[10px] text-slate-400 font-mono">
                            ID: {ds.id.slice(0, 8)}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3 text-slate-700">
                      <span className="font-mono font-medium text-slate-900 bg-slate-100 px-1.5 py-0.5 rounded text-[11px] mr-1.5">
                        {ds.asset_tag || 'N/A'}
                      </span>
                      <span>{ds.machine_name}</span>
                    </td>
                    <td className="px-5 py-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-sky-50 text-sky-700 border border-sky-200">
                        {ds.dataset_type || 'OPERATING_TELEMETRY'}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-slate-500 font-mono text-[11px]">
                      {new Date(ds.created_at).toLocaleString()}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <button
                        onClick={() => onStartUpload(ds.machine_id)}
                        className="text-sky-600 hover:text-sky-800 font-medium px-2 py-1 rounded hover:bg-sky-50 transition-colors"
                      >
                        Upload Version
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Drag & Drop Upload Zone Card */}
      <div
        onClick={() => onStartUpload(selectedMachineId === 'ALL' ? undefined : selectedMachineId)}
        className="border-2 border-dashed border-slate-300 hover:border-sky-500 bg-white hover:bg-sky-50/40 rounded-xl p-8 text-center cursor-pointer transition-all group"
      >
        <div className="w-12 h-12 rounded-full bg-sky-50 text-sky-600 group-hover:bg-sky-600 group-hover:text-white flex items-center justify-center mx-auto mb-3 transition-colors shadow-xs">
          <UploadCloud className="w-6 h-6" />
        </div>
        <h3 className="text-sm font-bold text-slate-800 group-hover:text-sky-900">
          Upload Operating Telemetry Batch (CSV)
        </h3>
        <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
          Drag and drop your milling machine sensor CSV here or click to open the validation and column mapping wizard.
        </p>
      </div>
    </div>
  );
};
