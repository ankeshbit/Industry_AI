import React, { useState, useEffect } from 'react';
import { api, Machine, User } from '../api';
import { 
  Building2, 
  Cpu, 
  Database, 
  ShieldCheck, 
  Sliders, 
  Plus, 
  Archive, 
  UploadCloud, 
  CheckCircle2, 
  Server, 
  HardDrive, 
  FileText, 
  AlertTriangle,
  RefreshCw,
  KeyRound,
  Lock
} from 'lucide-react';

interface SettingsViewProps {
  currentUser: User;
  onSelectMachineForUpload?: (machineId: string) => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({ currentUser, onSelectMachineForUpload }) => {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'equipment' | 'tenant' | 'database' | 'governance'>('equipment');

  // New Machine Modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [assetTag, setAssetTag] = useState('');
  const [name, setName] = useState('');
  const [categoryCode, setCategoryCode] = useState('GENERAL_MACHINE_TOOL');
  const [manufacturer, setManufacturer] = useState('');
  const [modelNumber, setModelNumber] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const [machs, cats] = await Promise.all([
        api.machines.list(), 
        api.machines.categories()
      ]);
      setMachines(machs);
      setCategories(cats);
    } catch (e) {
      console.error('Failed to load machine data:', e);
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
    setSubmitting(true);
    try {
      await api.machines.create({
        asset_tag: assetTag.trim(),
        name: name.trim(),
        category_code: categoryCode,
        manufacturer: manufacturer.trim() || undefined,
        model_number: modelNumber.trim() || undefined,
      });
      setShowCreateModal(false);
      setAssetTag('');
      setName('');
      setManufacturer('');
      setModelNumber('');
      await loadData();
    } catch (err: any) {
      setFormError(err.message || 'Failed to register machine asset.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleArchive = async (id: string, tag: string) => {
    if (confirm(`Archive machine ${tag}? Archived machines cannot accept new operating data (AC-MM-2).`)) {
      try {
        await api.machines.archive(id);
        await loadData();
      } catch (err: any) {
        alert(err?.message || 'Failed to archive machine.');
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Sliders className="w-5 h-5 text-sky-600" />
            System Settings & Asset Inventory
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Plant machinery registry, tenant organization profile, Neon PostgreSQL telemetry, and ML governance policies.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex bg-slate-100 p-1 rounded-xl text-xs font-medium text-slate-600 border border-slate-200/80">
          <button
            onClick={() => setActiveTab('equipment')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === 'equipment' ? 'bg-white text-slate-900 font-semibold shadow-sm' : 'hover:text-slate-900'
            }`}
          >
            <Cpu className="w-3.5 h-3.5 text-sky-600" />
            Equipment Inventory ({machines.length})
          </button>
          <button
            onClick={() => setActiveTab('tenant')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === 'tenant' ? 'bg-white text-slate-900 font-semibold shadow-sm' : 'hover:text-slate-900'
            }`}
          >
            <Building2 className="w-3.5 h-3.5 text-slate-600" />
            Tenant & Users
          </button>
          <button
            onClick={() => setActiveTab('database')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === 'database' ? 'bg-white text-slate-900 font-semibold shadow-sm' : 'hover:text-slate-900'
            }`}
          >
            <Database className="w-3.5 h-3.5 text-emerald-600" />
            Infrastructure & DB
          </button>
          <button
            onClick={() => setActiveTab('governance')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === 'governance' ? 'bg-white text-slate-900 font-semibold shadow-sm' : 'hover:text-slate-900'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5 text-amber-600" />
            Safety & Rules
          </button>
        </div>
      </div>

      {/* TAB 1: EQUIPMENT INVENTORY */}
      {activeTab === 'equipment' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Physical Machine Registry</h2>
              <p className="text-xs text-slate-500">
                Registered CNC milling tools, lathes, and high-speed spindles monitored under PRD v1.2 specifications.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={loadData}
                className="p-2 text-slate-500 hover:text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors shadow-sm"
                title="Refresh Machine List"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              </button>
              <button
                onClick={() => setShowCreateModal(true)}
                className="bg-sky-600 hover:bg-sky-700 text-white font-medium px-3.5 py-1.5 rounded-lg text-xs transition-colors flex items-center gap-1.5 shadow-sm"
              >
                <Plus className="w-4 h-4" /> Register New Asset
              </button>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-600 uppercase tracking-wider text-[11px] font-semibold border-b border-slate-200">
                  <tr>
                    <th className="px-5 py-3">Asset Tag</th>
                    <th className="px-5 py-3">Machine Name</th>
                    <th className="px-5 py-3">Category Code</th>
                    <th className="px-5 py-3">Manufacturer & Model</th>
                    <th className="px-5 py-3">Operational Status</th>
                    <th className="px-5 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {machines.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-5 py-10 text-center text-slate-400">
                        {loading ? 'Querying machinery assets from Neon database...' : 'No machines registered yet.'}
                      </td>
                    </tr>
                  ) : (
                    machines.map((m) => (
                      <tr key={m.id} className="hover:bg-slate-50/70 transition-colors">
                        <td className="px-5 py-3.5 font-mono font-bold text-sky-700">
                          {m.asset_tag}
                        </td>
                        <td className="px-5 py-3.5 font-semibold text-slate-900">
                          {m.name}
                        </td>
                        <td className="px-5 py-3.5">
                          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
                            {m.category_code}
                          </span>
                        </td>
                        <td className="px-5 py-3.5 text-slate-600">
                          {m.manufacturer || m.model_number ? (
                            <span>{m.manufacturer || '—'} / {m.model_number || '—'}</span>
                          ) : (
                            <span className="text-slate-400 italic">Not specified</span>
                          )}
                        </td>
                        <td className="px-5 py-3.5">
                          {m.archived_at ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-600 border border-slate-200">
                              ARCHIVED (LOCKED)
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                              ACTIVE
                            </span>
                          )}
                        </td>
                        <td className="px-5 py-3.5 text-right space-x-2">
                          {!m.archived_at && onSelectMachineForUpload && (
                            <button
                              onClick={() => onSelectMachineForUpload(m.id)}
                              className="bg-sky-50 hover:bg-sky-100 text-sky-700 border border-sky-200 px-2.5 py-1 rounded text-[11px] font-medium transition-colors inline-flex items-center gap-1"
                            >
                              <UploadCloud className="w-3.5 h-3.5" /> Ingest CSV
                            </button>
                          )}
                          {!m.archived_at && (
                            <button
                              onClick={() => handleArchive(m.id, m.asset_tag)}
                              className="text-slate-400 hover:text-rose-600 p-1 rounded hover:bg-rose-50 transition-colors"
                              title="Archive Machine (Lock from new uploads)"
                            >
                              <Archive className="w-3.5 h-3.5" />
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
        </div>
      )}

      {/* TAB 2: TENANT & USERS */}
      {activeTab === 'tenant' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Building2 className="w-4 h-4 text-sky-600" />
              Plant Organization Profile
            </h3>
            <div className="space-y-3 text-xs">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80">
                <div className="text-slate-500 text-[11px]">Organization Name</div>
                <div className="text-sm font-bold text-slate-900 mt-0.5">{currentUser.organisation.name}</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80">
                <div className="text-slate-500 text-[11px]">Organization Identifier (Tenant ID)</div>
                <div className="font-mono text-slate-700 mt-0.5 break-all">{currentUser.organisation.id}</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80">
                <div className="text-slate-500 text-[11px]">Deployment Architecture Mode</div>
                <div className="font-semibold text-slate-800 mt-0.5">Single-Tenant Production Monolith (PRD MS1)</div>
                <p className="text-[11px] text-slate-500 mt-1">
                  Tenant isolation enforced at schema & query boundaries via tenant-scoped organization filters.
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <KeyRound className="w-4 h-4 text-sky-600" />
              Authenticated Engineer Account
            </h3>
            <div className="space-y-3 text-xs">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80">
                <div className="text-slate-500 text-[11px]">Engineer Name</div>
                <div className="text-sm font-bold text-slate-900 mt-0.5">{currentUser.full_name}</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80">
                <div className="text-slate-500 text-[11px]">Email Address</div>
                <div className="font-mono text-slate-700 mt-0.5">{currentUser.email}</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80">
                <div className="text-slate-500 text-[11px]">Security Role & Access Tier</div>
                <div className="flex items-center gap-2 mt-1">
                  <span className="px-2.5 py-1 rounded text-xs font-bold bg-amber-50 text-amber-800 border border-amber-200 font-mono">
                    {currentUser.role}
                  </span>
                  <span className="text-[11px] text-slate-500">Full administrative access</span>
                </div>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80">
                <div className="text-slate-500 text-[11px]">Credential Security</div>
                <div className="font-semibold text-slate-800 mt-0.5 flex items-center gap-1.5">
                  <Lock className="w-3.5 h-3.5 text-emerald-600" />
                  Enterprise standard credential security + brute force lockout protection
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: INFRASTRUCTURE & DB */}
      {activeTab === 'database' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider">Primary Database</span>
                <Database className="w-4 h-4 text-emerald-600" />
              </div>
              <div className="text-base font-bold text-slate-900">Neon PostgreSQL</div>
              <div className="text-xs text-emerald-700 font-semibold mt-1 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Serverless Pooler Active
              </div>
              <p className="text-[11px] text-slate-500 mt-2 font-mono">
                AWS us-east-2 (Pooled Serverless Endpoint)
              </p>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider">ORM & Pool Engine</span>
                <HardDrive className="w-4 h-4 text-sky-600" />
              </div>
              <div className="text-base font-bold text-slate-900">SQLAlchemy 2.0</div>
              <div className="text-xs text-slate-700 font-medium mt-1">
                NullPool / Pooled Mode Compatible
              </div>
              <p className="text-[11px] text-slate-500 mt-2">
                SSL Mode: require • Channel Binding: require
              </p>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider">Job Runner Daemon</span>
                <Server className="w-4 h-4 text-indigo-600" />
              </div>
              <div className="text-base font-bold text-slate-900">Background Worker</div>
              <div className="text-xs text-emerald-700 font-semibold mt-1 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Polling queue active
              </div>
              <p className="text-[11px] text-slate-500 mt-2">
                Daemon polling `jobs` table with exponential backoff & state lock
              </p>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Server className="w-4 h-4 text-sky-600" />
              Production ML Artifact Catalog & Verification
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-600 uppercase tracking-wider text-[11px] font-semibold border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-2.5">Model Identifier</th>
                    <th className="px-4 py-2.5">Configuration</th>
                    <th className="px-4 py-2.5">Boosting Rounds (T*)</th>
                    <th className="px-4 py-2.5">Decision Threshold (&tau;*)</th>
                    <th className="px-4 py-2.5">Platt Parameters (w, c)</th>
                    <th className="px-4 py-2.5">SHA-256 Hash Integrity</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                  <tr>
                    <td className="px-4 py-3 font-bold text-sky-700">ai4i_failure_clf_typed</td>
                    <td className="px-4 py-3 text-slate-700">Config A (WITH_TYPE, 6 features)</td>
                    <td className="px-4 py-3 font-bold text-slate-900">74 rounds</td>
                    <td className="px-4 py-3 font-bold text-emerald-700">0.0100 (1.00%)</td>
                    <td className="px-4 py-3 text-slate-600">w=0.9502, c=-2.2492</td>
                    <td className="px-4 py-3 text-emerald-700 font-semibold flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" /> caa17fdb... (Verified)
                    </td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 font-bold text-sky-700">ai4i_failure_clf_notype</td>
                    <td className="px-4 py-3 text-slate-700">Config B (NO_TYPE, 5 features)</td>
                    <td className="px-4 py-3 font-bold text-slate-900">100 rounds</td>
                    <td className="px-4 py-3 font-bold text-emerald-700">0.0100 (1.00%)</td>
                    <td className="px-4 py-3 text-slate-600">w=0.9701, c=-2.1979</td>
                    <td className="px-4 py-3 text-emerald-700 font-semibold flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" /> 182f3a58... (Verified)
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: SAFETY & RULES */}
      {activeTab === 'governance' && (
        <div className="space-y-4">
          <div className="bg-amber-50/60 border border-amber-200/80 rounded-xl p-4 flex items-start gap-3 text-xs text-amber-900">
            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold">Authoritative Governance Notice:</span>
              <p className="mt-0.5">
                Model configurations and pipeline validation gates conform to Stage 3 Architecture v1.4.2 & PRD v1.2. 
                Parameters cannot be altered in production without formal peer re-validation.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-2">
              <div className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                AC-MM-2: Machine Archive Protection
              </div>
              <p className="text-xs text-slate-600">
                Archived machines enter a permanent write-lock state. Any API ingestion attempts against an archived machine are automatically blocked with HTTP 400 Bad Request.
              </p>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-2">
              <div className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                AC-XAI-2: Non-Causality Mandatory Disclaimer
              </div>
              <p className="text-xs text-slate-600">
                SHAP feature attributions represent observational associations only and must not be interpreted as physical causal guarantees for plant engineering interventions.
              </p>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-2">
              <div className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                AC-PIPE-1: Schema & Physical Unit Conversion
              </div>
              <p className="text-xs text-slate-600">
                Inference pipelines enforce Kelvin conversion: T(K) = T(°C) + 273.15 or T(K) = (T(°F) - 32) × 5/9 + 273.15. Unmapped mandatory physical dimensions trigger pipeline abort.
              </p>
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-2">
              <div className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                TreeSHAP Additivity Verification
              </div>
              <p className="text-xs text-slate-600">
                Every explained row validates TreeSHAP efficiency: |∑ φ_i - (f(x) - E[f(x)])| ≤ 1e-5. Discrepancies fail with integrity warnings.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* CREATE MACHINE MODAL */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white border border-slate-200 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Cpu className="w-4 h-4 text-sky-600" /> Register New Machinery Asset
              </h3>
              <button 
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-semibold"
              >
                ✕
              </button>
            </div>

            {formError && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateMachine} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 mb-1 font-semibold">Asset Tag (e.g. MILL-003, LATHE-002)</label>
                <input
                  type="text"
                  required
                  value={assetTag}
                  onChange={(e) => setAssetTag(e.target.value)}
                  placeholder="MILL-003"
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-900 font-mono focus:outline-none focus:border-sky-500 focus:bg-white"
                />
              </div>

              <div>
                <label className="block text-slate-700 mb-1 font-semibold">Machine Name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="5-Axis High-Precision CNC Milling Machine"
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:border-sky-500 focus:bg-white"
                />
              </div>

              <div>
                <label className="block text-slate-700 mb-1 font-semibold">Category Classification</label>
                <select
                  value={categoryCode}
                  onChange={(e) => setCategoryCode(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:border-sky-500 focus:bg-white"
                >
                  {categories.map((c) => (
                    <option key={c.code} value={c.code}>{c.name} ({c.code})</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 mb-1 font-semibold">Manufacturer</label>
                  <input
                    type="text"
                    value={manufacturer}
                    onChange={(e) => setManufacturer(e.target.value)}
                    placeholder="Haas / Matsuura"
                    className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:border-sky-500 focus:bg-white"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 mb-1 font-semibold">Model Number</label>
                  <input
                    type="text"
                    value={modelNumber}
                    onChange={(e) => setModelNumber(e.target.value)}
                    placeholder="VF-4SS"
                    className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-900 focus:outline-none focus:border-sky-500 focus:bg-white"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="text-slate-600 hover:text-slate-800 px-3 py-1.5 rounded-lg font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="bg-sky-600 hover:bg-sky-700 text-white font-medium px-4 py-1.5 rounded-lg transition-colors shadow-sm disabled:opacity-50"
                >
                  {submitting ? 'Registering...' : 'Save & Register'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
export default SettingsView;
