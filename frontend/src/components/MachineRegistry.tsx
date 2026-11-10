import React, { useState, useEffect } from 'react';
import { api, Machine, CompatibilityCheck, AnalysisResult } from '../api';
import { Plus, Archive, UploadCloud, Activity, Cpu, Wrench } from 'lucide-react';

interface MachineRegistryProps {
  onSelectUpload: (machineId: string) => void;
  onViewAnalysis: (resultId: string) => void;
}

export const MachineRegistry: React.FC<MachineRegistryProps> = ({ onSelectUpload, onViewAnalysis }) => {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [loading, setLoading] = useState(true);

  // New Machine Form State
  const [assetTag, setAssetTag] = useState('');
  const [name, setName] = useState('');
  const [categoryCode, setCategoryCode] = useState('GENERAL_MACHINE_TOOL');
  const [manufacturer, setManufacturer] = useState('');
  const [modelNumber, setModelNumber] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const [machs, cats] = await Promise.all([api.machines.list(), api.machines.categories()]);
      setMachines(machs);
      setCategories(cats);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateMachine = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    try {
      await api.machines.create({
        asset_tag: assetTag,
        name,
        category_code: categoryCode,
        manufacturer,
        model_number: modelNumber,
      });
      setShowCreateModal(false);
      setAssetTag('');
      setName('');
      loadData();
    } catch (err: any) {
      setFormError(err.message || 'Failed to create machine.');
    }
  };

  const handleArchive = async (id: string) => {
    if (confirm('Archive this machine? Archived machines reject new datasets (AC-MM-2).')) {
      await api.machines.archive(id);
      loadData();
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Machine Registry</h2>
          <p className="text-xs text-slate-400 mt-0.5">Asset Inventory & Operating State Data Ingestion</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="bg-sky-600 hover:bg-sky-500 text-white font-medium px-4 py-2 rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-lg shadow-sky-600/20"
        >
          <Plus className="w-4 h-4" /> Register Machine
        </button>
      </div>

      {/* Machine Table */}
      <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-900/80 text-slate-400 uppercase tracking-wider text-[11px] font-semibold border-b border-slate-700/60">
              <tr>
                <th className="px-5 py-3">Asset Tag</th>
                <th className="px-5 py-3">Machine Name</th>
                <th className="px-5 py-3">Category</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/40">
              {machines.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-slate-400 text-xs">
                    {loading ? 'Loading machines...' : 'No machines registered yet. Click "Register Machine" to begin.'}
                  </td>
                </tr>
              ) : (
                machines.map((m) => (
                  <tr key={m.id} className="hover:bg-slate-700/30 transition-colors">
                    <td className="px-5 py-3 font-mono font-semibold text-sky-400">{m.asset_tag}</td>
                    <td className="px-5 py-3 font-medium text-slate-200">{m.name}</td>
                    <td className="px-5 py-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-900/80 text-slate-300 border border-slate-700/60">
                        {m.category_code}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      {m.archived_at ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-700/50 text-slate-400 border border-slate-600/50">
                          ARCHIVED
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          ACTIVE
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-right space-x-2">
                      {!m.archived_at && (
                        <button
                          onClick={() => onSelectUpload(m.id)}
                          className="bg-sky-600/20 hover:bg-sky-600/30 text-sky-300 border border-sky-500/30 px-3 py-1 rounded text-[11px] font-semibold transition-colors inline-flex items-center gap-1"
                        >
                          <UploadCloud className="w-3.5 h-3.5" /> Upload CSV
                        </button>
                      )}
                      {!m.archived_at && (
                        <button
                          onClick={() => handleArchive(m.id)}
                          className="text-slate-400 hover:text-rose-400 p-1 transition-colors"
                          title="Archive machine"
                        >
                          <Archive className="w-4 h-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Machine Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-md w-full p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-4">Register Machine</h3>

            {formError && (
              <div className="mb-4 p-3 bg-rose-950/30 border border-rose-500/30 rounded-lg text-xs text-rose-300">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateMachine} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 mb-1 font-medium">Asset Tag (Unique ID)</label>
                <input
                  type="text"
                  required
                  value={assetTag}
                  onChange={(e) => setAssetTag(e.target.value)}
                  placeholder="MILL-001"
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 font-mono focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 mb-1 font-medium">Machine Name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="5-Axis CNC Milling Center"
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 mb-1 font-medium">Machine Category</label>
                <select
                  value={categoryCode}
                  onChange={(e) => setCategoryCode(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-sky-500"
                >
                  {categories.map((c) => (
                    <option key={c.code} value={c.code}>{c.name}</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 mb-1 font-medium">Manufacturer</label>
                  <input
                    type="text"
                    value={manufacturer}
                    onChange={(e) => setManufacturer(e.target.value)}
                    placeholder="Haas / Matsuura"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-sky-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 mb-1 font-medium">Model Number</label>
                  <input
                    type="text"
                    value={modelNumber}
                    onChange={(e) => setModelNumber(e.target.value)}
                    placeholder="VF-2SS"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-sky-500"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="text-slate-400 hover:text-white px-3 py-2 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-sky-600 hover:bg-sky-500 text-white font-medium px-4 py-2 rounded-lg transition-colors"
                >
                  Save Machine
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

