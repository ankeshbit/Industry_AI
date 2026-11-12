import React, { useState, useEffect } from 'react';
import { api, CompatibilityCheck } from '../api';
import { UploadCloud, CheckCircle2, AlertCircle, ArrowRight, Check, Sparkles, X } from 'lucide-react';

interface DatasetUploadWizardProps {
  machineId: string;
  onComplete: (check: CompatibilityCheck) => void;
  onCancel: () => void;
}

export const DatasetUploadWizard: React.FC<DatasetUploadWizardProps> = ({ machineId, onComplete, onCancel }) => {
  const [step, setStep] = useState<1 | 2>(1);
  const [datasetName, setDatasetName] = useState('Operating Batch Data');
  const [file, setFile] = useState<File | null>(null);
  const [datasetId, setDatasetId] = useState<string | null>(null);
  const [versionId, setVersionId] = useState<string | null>(null);
  const [qualityScore, setQualityScore] = useState<number | null>(null);
  const [columns, setColumns] = useState<string[]>([]);
  const [profileId, setProfileId] = useState<'ai4i_failure_no_type' | 'ai4i_failure_with_type'>('ai4i_failure_no_type');

  // Mapping state
  const [airTempCol, setAirTempCol] = useState('');
  const [airTempUnit, setAirTempUnit] = useState('degC');
  const [procTempCol, setProcTempCol] = useState('');
  const [procTempUnit, setProcTempUnit] = useState('degC');
  const [speedCol, setSpeedCol] = useState('');
  const [speedUnit, setSpeedUnit] = useState('rpm');
  const [torqueCol, setTorqueCol] = useState('');
  const [torqueUnit, setTorqueUnit] = useState('Nm');
  const [wearCol, setWearCol] = useState('');
  const [wearUnit, setWearUnit] = useState('min');
  const [typeCol, setTypeCol] = useState('');
  const [assertedEquivalence, setAssertedEquivalence] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setError(null);
    setLoading(true);

    try {
      // 1. Create dataset
      let dsId = datasetId;
      if (!dsId) {
        const ds = await api.datasets.createForMachine(machineId, { name: datasetName });
        dsId = ds.id;
        setDatasetId(ds.id);
      }

      // 2. Upload file
      const up = await api.datasets.upload(dsId, file);
      setVersionId(up.dataset_version_id);
      setQualityScore(up.quality_score);

      // 3. Get column names and suggestions
      const vDetails = await api.datasets.getVersion(up.dataset_version_id);
      const cols = vDetails.columns.map((c: any) => c.name);
      setColumns(cols);

      // Ask for suggestions against WITH_TYPE profile
      const sug = await api.datasets.getSuggestions(up.dataset_version_id, 'ai4i_failure_with_type');
      const s = sug.suggestions;
      if (s.air_temperature) { setAirTempCol(s.air_temperature.column); if (s.air_temperature.unit) setAirTempUnit(s.air_temperature.unit); }
      if (s.process_temperature) { setProcTempCol(s.process_temperature.column); if (s.process_temperature.unit) setProcTempUnit(s.process_temperature.unit); }
      if (s.rotational_speed) { setSpeedCol(s.rotational_speed.column); if (s.rotational_speed.unit) setSpeedUnit(s.rotational_speed.unit); }
      if (s.torque) { setTorqueCol(s.torque.column); if (s.torque.unit) setTorqueUnit(s.torque.unit); }
      if (s.tool_wear) { setWearCol(s.tool_wear.column); if (s.tool_wear.unit) setWearUnit(s.tool_wear.unit); }
      if (s.product_type) { setTypeCol(s.product_type.column); setProfileId('ai4i_failure_with_type'); }

      setStep(2);
    } catch (err: any) {
      setError(err.message || 'File upload or validation failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveMappingAndEvaluate = async () => {
    if (!versionId) return;
    setError(null);
    setLoading(true);

    try {
      const mappings: Record<string, any> = {
        air_temperature: { column: airTempCol, unit: airTempUnit },
        process_temperature: { column: procTempCol, unit: procTempUnit },
        rotational_speed: { column: speedCol, unit: speedUnit },
        torque: { column: torqueCol, unit: torqueUnit },
        tool_wear: { column: wearCol, unit: wearUnit },
      };

      if (profileId === 'ai4i_failure_with_type' && typeCol) {
        mappings.product_type = { column: typeCol, asserted_equivalence: assertedEquivalence };
      }

      // Save mapping
      await api.datasets.saveMapping(versionId, profileId, mappings);

      // Run compatibility evaluation
      const checks = await api.compatibility.runChecks(versionId);
      const targetCheck = checks.find((c) => c.profile.configuration === (profileId === 'ai4i_failure_with_type' ? 'WITH_TYPE' : 'NO_TYPE')) || checks[0];

      onComplete(targetCheck);
    } catch (err: any) {
      setError(err.message || 'Mapping validation failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 overflow-y-auto">
      <div className="bg-white border border-slate-200 rounded-2xl max-w-2xl w-full p-6 shadow-2xl my-8 space-y-5">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div>
            <h3 className="text-base font-bold text-slate-900">Dataset Ingestion & Schema Alignment Wizard</h3>
            <p className="text-xs text-slate-500 mt-0.5">Step {step} of 2 • AI4I Canonical Feature Mapping</p>
          </div>
          <button onClick={onCancel} className="text-slate-400 hover:text-slate-600 p-1 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-500" />
            <span>{error}</span>
          </div>
        )}

        {step === 1 && (
          <form onSubmit={handleFileUpload} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Dataset Batch Name</label>
              <input
                type="text"
                required
                value={datasetName}
                onChange={(e) => setDatasetName(e.target.value)}
                className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-sky-500 focus:bg-white"
              />
            </div>

            <div className="border-2 border-dashed border-slate-300 hover:border-sky-500 rounded-xl p-8 text-center bg-slate-50/50 transition-colors">
              <UploadCloud className="w-10 h-10 text-slate-400 mx-auto mb-2" />
              <div className="text-xs text-slate-800 font-semibold">Select or drag CSV sensor dataset</div>
              <p className="text-[11px] text-slate-500 mt-1">UTF-8 tabular CSV up to 50 MB with header row</p>
              <input
                type="file"
                accept=".csv,.tsv"
                required
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="mt-4 block mx-auto text-xs text-slate-500 file:mr-4 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-sky-600 file:text-white hover:file:bg-sky-700 cursor-pointer"
              />
              {file && (
                <p className="text-xs text-emerald-700 font-semibold mt-3 font-mono">
                  ✓ Ready: {file.name} ({(file.size / 1024).toFixed(1)} KB)
                </p>
              )}
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={onCancel}
                className="text-slate-600 hover:text-slate-800 px-4 py-2 rounded-lg text-xs font-medium"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!file || loading}
                className="bg-sky-600 hover:bg-sky-700 text-white font-medium px-5 py-2 rounded-lg text-xs transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
              >
                {loading ? 'Ingesting & Calculating Quality Score...' : 'Ingest & Scan Schema'} <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </form>
        )}

        {step === 2 && (
          <div className="space-y-5">
            {/* Quality Score Banner */}
            <div className="bg-emerald-50/70 p-4 rounded-xl border border-emerald-200/80 flex items-center justify-between">
              <div>
                <div className="text-[11px] text-emerald-800 uppercase tracking-wider font-bold">Data Quality Score (Q)</div>
                <div className="text-2xl font-bold text-emerald-700 mt-0.5">{qualityScore} / 100</div>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-emerald-800 bg-white/80 px-3 py-1.5 rounded-lg border border-emerald-200 shadow-sm">
                <Sparkles className="w-4 h-4 text-amber-500" />
                <span className="font-semibold">Auto-detected Column Suggestions</span>
              </div>
            </div>

            {/* Profile Selector */}
            <div className="flex gap-2 p-1 bg-slate-100 rounded-lg text-xs font-semibold">
              <button
                onClick={() => setProfileId('ai4i_failure_no_type')}
                className={`flex-1 py-1.5 rounded-md transition-colors ${
                  profileId === 'ai4i_failure_no_type' 
                    ? 'bg-white text-slate-900 shadow-sm' 
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Profile: Without Type (NO_TYPE • Config B)
              </button>
              <button
                onClick={() => setProfileId('ai4i_failure_with_type')}
                className={`flex-1 py-1.5 rounded-md transition-colors ${
                  profileId === 'ai4i_failure_with_type' 
                    ? 'bg-white text-slate-900 shadow-sm' 
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Profile: With Type (WITH_TYPE • Config A)
              </button>
            </div>

            {/* Mapping Grid */}
            <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1 text-xs">
              {/* Air Temp */}
              <div className="grid grid-cols-12 gap-2 items-center bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <div className="col-span-4 font-semibold text-slate-800">Air Temperature</div>
                <select
                  value={airTempCol}
                  onChange={(e) => setAirTempCol(e.target.value)}
                  className="col-span-5 bg-white border border-slate-300 rounded px-2.5 py-1 text-slate-800 focus:outline-none focus:border-sky-500"
                >
                  <option value="">-- Select Column --</option>
                  {columns.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
                <select
                  value={airTempUnit}
                  onChange={(e) => setAirTempUnit(e.target.value)}
                  className="col-span-3 bg-white border border-slate-300 rounded px-2 py-1 text-slate-700 font-mono"
                >
                  <option value="degC">degC (°C)</option>
                  <option value="K">Kelvin (K)</option>
                  <option value="degF">degF (°F)</option>
                </select>
              </div>

              {/* Process Temp */}
              <div className="grid grid-cols-12 gap-2 items-center bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <div className="col-span-4 font-semibold text-slate-800">Process Temperature</div>
                <select
                  value={procTempCol}
                  onChange={(e) => setProcTempCol(e.target.value)}
                  className="col-span-5 bg-white border border-slate-300 rounded px-2.5 py-1 text-slate-800 focus:outline-none focus:border-sky-500"
                >
                  <option value="">-- Select Column --</option>
                  {columns.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
                <select
                  value={procTempUnit}
                  onChange={(e) => setProcTempUnit(e.target.value)}
                  className="col-span-3 bg-white border border-slate-300 rounded px-2 py-1 text-slate-700 font-mono"
                >
                  <option value="degC">degC (°C)</option>
                  <option value="K">Kelvin (K)</option>
                  <option value="degF">degF (°F)</option>
                </select>
              </div>

              {/* Rotational Speed */}
              <div className="grid grid-cols-12 gap-2 items-center bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <div className="col-span-4 font-semibold text-slate-800">Rotational Speed</div>
                <select
                  value={speedCol}
                  onChange={(e) => setSpeedCol(e.target.value)}
                  className="col-span-5 bg-white border border-slate-300 rounded px-2.5 py-1 text-slate-800 focus:outline-none focus:border-sky-500"
                >
                  <option value="">-- Select Column --</option>
                  {columns.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
                <select
                  value={speedUnit}
                  onChange={(e) => setSpeedUnit(e.target.value)}
                  className="col-span-3 bg-white border border-slate-300 rounded px-2 py-1 text-slate-700 font-mono"
                >
                  <option value="rpm">rpm</option>
                  <option value="rad_s">rad/s</option>
                  <option value="Hz">Hz</option>
                </select>
              </div>

              {/* Torque */}
              <div className="grid grid-cols-12 gap-2 items-center bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <div className="col-span-4 font-semibold text-slate-800">Torque</div>
                <select
                  value={torqueCol}
                  onChange={(e) => setTorqueCol(e.target.value)}
                  className="col-span-5 bg-white border border-slate-300 rounded px-2.5 py-1 text-slate-800 focus:outline-none focus:border-sky-500"
                >
                  <option value="">-- Select Column --</option>
                  {columns.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
                <select
                  value={torqueUnit}
                  onChange={(e) => setTorqueUnit(e.target.value)}
                  className="col-span-3 bg-white border border-slate-300 rounded px-2 py-1 text-slate-700 font-mono"
                >
                  <option value="Nm">Nm</option>
                  <option value="lbf_ft">lbf·ft</option>
                </select>
              </div>

              {/* Tool Wear */}
              <div className="grid grid-cols-12 gap-2 items-center bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                <div className="col-span-4 font-semibold text-slate-800">Tool Wear</div>
                <select
                  value={wearCol}
                  onChange={(e) => setWearCol(e.target.value)}
                  className="col-span-5 bg-white border border-slate-300 rounded px-2.5 py-1 text-slate-800 focus:outline-none focus:border-sky-500"
                >
                  <option value="">-- Select Column --</option>
                  {columns.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
                <select
                  value={wearUnit}
                  onChange={(e) => setWearUnit(e.target.value)}
                  className="col-span-3 bg-white border border-slate-300 rounded px-2 py-1 text-slate-700 font-mono"
                >
                  <option value="min">min</option>
                  <option value="h">hours</option>
                </select>
              </div>

              {/* Optional Product Type (for WITH_TYPE) */}
              {profileId === 'ai4i_failure_with_type' && (
                <div className="p-3 bg-sky-50 border border-sky-200 rounded-lg space-y-2">
                  <div className="grid grid-cols-12 gap-2 items-center">
                    <div className="col-span-4 font-semibold text-sky-900">Product Type (L/M/H)</div>
                    <select
                      value={typeCol}
                      onChange={(e) => setTypeCol(e.target.value)}
                      className="col-span-8 bg-white border border-sky-300 rounded px-2.5 py-1 text-slate-800"
                    >
                      <option value="">-- Select Variant Column --</option>
                      {columns.map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <label className="flex items-start gap-2 text-xs text-sky-800 cursor-pointer pt-1">
                    <input
                      type="checkbox"
                      checked={assertedEquivalence}
                      onChange={(e) => setAssertedEquivalence(e.target.checked)}
                      className="mt-0.5 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                    />
                    <span>I confirm this column represents AI4I manufacturing quality variant (L/M/H).</span>
                  </label>
                </div>
              )}
            </div>

            <div className="flex justify-between items-center pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="text-xs text-slate-500 hover:text-slate-800 font-medium"
              >
                Back to file upload
              </button>
              <button
                type="button"
                onClick={handleSaveMappingAndEvaluate}
                disabled={loading || !airTempCol || !procTempCol || !speedCol || !torqueCol || !wearCol}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-5 py-2 rounded-lg text-xs transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
              >
                {loading ? 'Evaluating Compatibility...' : 'Confirm Mapping & Check Gate'} <Check className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
export default DatasetUploadWizard;
