import React, { useState, useEffect } from 'react';
import { api, CompatibilityCheck } from '../api';
import { 
  UploadCloud, 
  CheckCircle2, 
  AlertCircle, 
  ArrowRight, 
  Check, 
  Sparkles, 
  X, 
  FileSpreadsheet, 
  Table, 
  Eye, 
  Info,
  HelpCircle,
  FileCheck,
  AlertTriangle
} from 'lucide-react';

interface DatasetUploadWizardProps {
  machineId: string;
  onComplete: (check: CompatibilityCheck) => void;
  onCancel: () => void;
}

interface PreviewRow {
  headers: string[];
  rows: string[][];
  types: Record<string, 'numeric' | 'string'>;
  nullCount: number;
}

export const DatasetUploadWizard: React.FC<DatasetUploadWizardProps> = ({ machineId, onComplete, onCancel }) => {
  const [step, setStep] = useState<1 | 2>(1);
  const [datasetName, setDatasetName] = useState('Operating Batch Data');
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewRow | null>(null);
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

  const [error, setError] = useState<{ message: string; details?: string; remedy?: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploadProgressText, setUploadProgressText] = useState('');
  const [isDragging, setIsDragging] = useState(false);

  // Client-side CSV preview parser
  const parsePreview = (inputFile: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const text = e.target?.result as string;
        if (!text) return;
        const lines = text.split(/\r?\n/).filter(line => line.trim().length > 0);
        if (lines.length > 0) {
          const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''));
          const sampleLines = lines.slice(1, 6);
          let nulls = 0;
          const rows = sampleLines.map(line => {
            const cells = line.split(',').map(c => c.trim().replace(/^"|"$/g, ''));
            cells.forEach(c => {
              if (c === '' || c.toLowerCase() === 'nan' || c.toLowerCase() === 'null') {
                nulls++;
              }
            });
            return cells;
          });

          // Detect column data types
          const types: Record<string, 'numeric' | 'string'> = {};
          headers.forEach((h, colIdx) => {
            let isNum = true;
            for (const r of rows) {
              const val = r[colIdx];
              if (val !== undefined && val !== '' && isNaN(Number(val))) {
                isNum = false;
                break;
              }
            }
            types[h] = isNum ? 'numeric' : 'string';
          });

          setPreview({
            headers,
            rows,
            types,
            nullCount: nulls,
          });
        }
      } catch (err) {
        console.warn('Failed to parse client preview:', err);
      }
    };
    reader.readAsText(inputFile.slice(0, 16384)); // Read first 16KB for fast preview
  };

  const handleSelectFile = (newFile: File) => {
    setFile(newFile);
    setError(null);
    parsePreview(newFile);
  };

  // 1-Click: Load Sample AI4I Dataset
  const handleLoadSampleDataset = async () => {
    try {
      setLoading(true);
      setUploadProgressText('Fetching canonical AI4I benchmark sample dataset...');
      const resp = await fetch('/sample_ai4i_dataset.csv');
      if (!resp.ok) throw new Error('Sample dataset file not found on server.');
      const blob = await resp.blob();
      const sampleFile = new File([blob], 'ai4i_canonical_sample_100rows.csv', { type: 'text/csv' });
      setDatasetName('AI4I Benchmark Sample Ingestion');
      handleSelectFile(sampleFile);
    } catch (err: any) {
      setError({
        message: 'Could not load sample dataset automatically.',
        remedy: 'Please download the sample CSV manually using the link below and drag it into the upload box.'
      });
    } finally {
      setLoading(false);
      setUploadProgressText('');
    }
  };

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setError(null);
    setLoading(true);
    setUploadProgressText('Creating dataset batch record in Neon database...');

    try {
      // 1. Create dataset
      let dsId = datasetId;
      if (!dsId) {
        const ds = await api.datasets.createForMachine(machineId, { name: datasetName });
        dsId = ds.id;
        setDatasetId(ds.id);
      }

      setUploadProgressText('Uploading file & calculating Data Quality Score (Q)...');
      // 2. Upload file
      const up = await api.datasets.upload(dsId, file);
      setVersionId(up.dataset_version_id);
      setQualityScore(up.quality_score);

      setUploadProgressText('Inspecting schema & auto-detecting canonical physical sensors...');
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
      setError({
        message: err.message || 'File upload or validation failed.',
        details: 'The uploaded file could not be parsed as a valid tabular CSV, or contains incompatible delimiters.',
        remedy: 'Ensure your file is encoded in UTF-8, contains a header row, and has comma-separated columns.'
      });
    } finally {
      setLoading(false);
      setUploadProgressText('');
    }
  };

  const handleSaveMappingAndEvaluate = async () => {
    if (!versionId) return;
    setError(null);
    setLoading(true);
    setUploadProgressText('Saving canonical mappings & running Pre-Execution Gate checks...');

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
      setError({
        message: err.message || 'Mapping validation failed.',
        details: 'One or more required sensor mappings are missing or contain values outside valid physical operating bounds.',
        remedy: 'Verify that all 5 core mechanical dimensions are assigned to corresponding columns in your CSV.'
      });
    } finally {
      setLoading(false);
      setUploadProgressText('');
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 overflow-y-auto animate-in fade-in duration-200">
      <div className="bg-white border border-slate-200 rounded-2xl max-w-2xl w-full p-6 shadow-2xl my-8 space-y-5">
        {/* Wizard Header */}
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div className="flex items-center gap-3">
            <img src="/logo.png" alt="Industry AI" className="w-8 h-8 object-contain shrink-0" />
            <div>
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-100 text-sky-800 border border-sky-200 uppercase">
                  Step {step} of 2
                </span>
                <h3 className="text-base font-bold text-slate-900">
                  {step === 1 ? 'Dataset Ingestion & Client Preview' : 'Canonical Schema Alignment'}
                </h3>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                {step === 1 
                  ? 'Select or drag your machine operating CSV telemetry file for schema inspection.'
                  : 'Map your sensor columns to AI4I canonical physical dimensions and units.'}
              </p>
            </div>
          </div>
          <button onClick={onCancel} className="text-slate-400 hover:text-slate-600 p-1 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Actionable Error Alert */}
        {error && (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl space-y-1.5 text-xs text-rose-800">
            <div className="flex items-center gap-2 font-bold text-rose-900">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{error.message}</span>
            </div>
            {error.details && <p className="text-rose-700 ml-6">{error.details}</p>}
            {error.remedy && (
              <div className="ml-6 pt-1 text-slate-700 text-[11px] bg-white/70 p-2 rounded-lg border border-rose-200">
                <strong className="text-slate-900">Recommended Remedy:</strong> {error.remedy}
              </div>
            )}
          </div>
        )}

        {/* STEP 1: UPLOAD & PREVIEW */}
        {step === 1 && (
          <form onSubmit={handleFileUpload} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Dataset Batch Name
              </label>
              <input
                type="text"
                required
                value={datasetName}
                onChange={(e) => setDatasetName(e.target.value)}
                placeholder="e.g. Milling Line B - Q4 Run"
                className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-sky-500 focus:bg-white"
              />
            </div>

            {/* Drag & Drop Upload Zone */}
            <div
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                if (e.dataTransfer.files?.[0]) {
                  handleSelectFile(e.dataTransfer.files[0]);
                }
              }}
              className={`border-2 border-dashed rounded-xl p-6 text-center transition-all ${
                isDragging 
                  ? 'border-sky-500 bg-sky-50/70' 
                  : file 
                  ? 'border-emerald-400 bg-emerald-50/30' 
                  : 'border-slate-300 hover:border-sky-400 bg-slate-50/50'
              }`}
            >
              <UploadCloud className={`w-10 h-10 mx-auto mb-2 ${file ? 'text-emerald-600' : 'text-slate-400'}`} />
              
              {file ? (
                <div className="space-y-1">
                  <div className="text-xs font-bold text-emerald-800 flex items-center justify-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    File Selected: {file.name}
                  </div>
                  <p className="text-[11px] text-slate-500 font-mono">
                    Size: {(file.size / 1024).toFixed(1)} KB • Ready for schema verification
                  </p>
                </div>
              ) : (
                <div className="space-y-1">
                  <div className="text-xs text-slate-800 font-semibold">
                    Drag and drop your machine operating CSV here, or browse
                  </div>
                  <p className="text-[11px] text-slate-500">
                    Supports UTF-8 tabular CSV up to 50 MB with header row
                  </p>
                </div>
              )}

              <input
                type="file"
                accept=".csv,.tsv"
                onChange={(e) => {
                  if (e.target.files?.[0]) handleSelectFile(e.target.files[0]);
                }}
                className="mt-3 block mx-auto text-xs text-slate-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-sky-600 file:text-white hover:file:bg-sky-700 cursor-pointer"
              />

              {/* Quick Sample Trigger */}
              <div className="mt-4 pt-3 border-t border-slate-200/80 flex flex-wrap items-center justify-center gap-2 text-xs">
                <span className="text-slate-500">First-time user without a dataset?</span>
                <button
                  type="button"
                  onClick={handleLoadSampleDataset}
                  className="text-sky-700 hover:text-sky-800 font-bold underline inline-flex items-center gap-1"
                >
                  <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                  Load Canonical AI4I Sample CSV (100 Rows)
                </button>
              </div>
            </div>

            {/* Client-Side CSV Preview Table */}
            {preview && (
              <div className="space-y-2 pt-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-slate-800 flex items-center gap-1.5">
                    <Table className="w-3.5 h-3.5 text-sky-600" />
                    Instant Client-Side Preview (First 5 Rows)
                  </span>
                  <div className="flex items-center gap-3 text-[11px] text-slate-500">
                    <span><strong>{preview.headers.length}</strong> Columns detected</span>
                    <span>
                      {preview.nullCount === 0 ? (
                        <span className="text-emerald-700 font-semibold">✓ 0 Missing values</span>
                      ) : (
                        <span className="text-amber-700 font-semibold">⚠️ {preview.nullCount} missing cells</span>
                      )}
                    </span>
                  </div>
                </div>

                <div className="border border-slate-200 rounded-xl overflow-x-auto max-h-40 bg-white">
                  <table className="w-full text-[11px] text-left">
                    <thead className="bg-slate-50 border-b border-slate-200 text-slate-600">
                      <tr>
                        {preview.headers.map((h, i) => (
                          <th key={i} className="px-3 py-2 font-semibold whitespace-nowrap">
                            <div className="flex items-center gap-1">
                              <span>{h}</span>
                              <span className={`text-[9px] px-1 py-0.2 rounded font-mono ${
                                preview.types[h] === 'numeric' ? 'bg-sky-50 text-sky-700' : 'bg-slate-100 text-slate-600'
                              }`}>
                                {preview.types[h]}
                              </span>
                            </div>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-mono text-slate-700">
                      {preview.rows.map((row, rIdx) => (
                        <tr key={rIdx} className="hover:bg-slate-50/50">
                          {row.map((cell, cIdx) => (
                            <td key={cIdx} className="px-3 py-1.5 whitespace-nowrap">
                              {cell || <span className="text-slate-400 italic">null</span>}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Upload Progress Banner */}
            {loading && (
              <div className="p-3 bg-sky-50 border border-sky-200 rounded-xl flex items-center gap-3 text-xs text-sky-900">
                <div className="w-4 h-4 border-2 border-sky-600 border-t-transparent rounded-full animate-spin shrink-0" />
                <span className="font-semibold">{uploadProgressText || 'Processing dataset...'}</span>
              </div>
            )}

            {/* Footer Buttons */}
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={onCancel}
                className="text-slate-600 hover:text-slate-800 px-4 py-2 rounded-lg text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!file || loading}
                className="bg-sky-600 hover:bg-sky-700 text-white font-semibold px-5 py-2 rounded-lg text-xs transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
              >
                {loading ? 'Processing...' : 'Ingest & Scan Schema'} <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </form>
        )}

        {/* STEP 2: SCHEMA MAPPING & CANONICAL ALIGNMENT */}
        {step === 2 && (
          <div className="space-y-4">
            {/* Quality Score Banner */}
            <div className="bg-emerald-50/70 p-3.5 rounded-xl border border-emerald-200/80 flex items-center justify-between">
              <div>
                <div className="text-[10px] text-emerald-800 uppercase tracking-wider font-bold">Data Quality Score (Q)</div>
                <div className="text-2xl font-bold text-emerald-700 mt-0.5">{qualityScore} / 100</div>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-emerald-800 bg-white/90 px-3 py-1.5 rounded-lg border border-emerald-200 shadow-sm">
                <Sparkles className="w-4 h-4 text-amber-500" />
                <span className="font-semibold">Auto-detected Column Suggestions</span>
              </div>
            </div>

            {/* Profile Selection */}
            <div className="flex gap-2 p-1 bg-slate-100 rounded-lg text-xs font-semibold">
              <button
                type="button"
                onClick={() => setProfileId('ai4i_failure_no_type')}
                className={`flex-1 py-1.5 rounded-md transition-colors ${
                  profileId === 'ai4i_failure_no_type' 
                    ? 'bg-white text-slate-900 shadow-sm' 
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Standard Profile: 5 Sensors (NO_TYPE • Config B)
              </button>
              <button
                type="button"
                onClick={() => setProfileId('ai4i_failure_with_type')}
                className={`flex-1 py-1.5 rounded-md transition-colors ${
                  profileId === 'ai4i_failure_with_type' 
                    ? 'bg-white text-slate-900 shadow-sm' 
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Extended Profile: 6 Sensors with Quality Variant (WITH_TYPE • Config A)
              </button>
            </div>

            {/* Mapping Grid */}
            <div className="space-y-2 max-h-64 overflow-y-auto pr-1 text-xs">
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

              {/* Speed */}
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

              {/* Optional Product Type */}
              {profileId === 'ai4i_failure_with_type' && (
                <div className="p-3 bg-sky-50 border border-sky-200 rounded-lg space-y-2">
                  <div className="grid grid-cols-12 gap-2 items-center">
                    <div className="col-span-4 font-semibold text-sky-900">Product Quality Type</div>
                    <select
                      value={typeCol}
                      onChange={(e) => setTypeCol(e.target.value)}
                      className="col-span-8 bg-white border border-sky-300 rounded px-2.5 py-1 text-slate-800"
                    >
                      <option value="">-- Select Variant Column (L / M / H) --</option>
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
                    <span>I confirm this column maps to AI4I manufacturing variant (L/M/H).</span>
                  </label>
                </div>
              )}
            </div>

            {/* Unit Guidance Pill */}
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-start gap-2 text-[11px] text-slate-600">
              <Info className="w-4 h-4 text-sky-600 shrink-0 mt-0.5" />
              <span>
                <strong>Automatic Normalization:</strong> Temperatures are converted to Kelvin, Rotational Speed to RPM, Torque to N·m, and Tool Wear to minutes prior to XGBoost tree evaluation.
              </span>
            </div>

            {/* Progress Text */}
            {loading && (
              <div className="p-3 bg-sky-50 border border-sky-200 rounded-xl flex items-center gap-3 text-xs text-sky-900">
                <div className="w-4 h-4 border-2 border-sky-600 border-t-transparent rounded-full animate-spin shrink-0" />
                <span className="font-semibold">{uploadProgressText || 'Validating mappings...'}</span>
              </div>
            )}

            {/* Footer Buttons */}
            <div className="flex justify-between items-center pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="text-xs text-slate-500 hover:text-slate-800 font-semibold"
              >
                Back to file preview
              </button>
              <button
                type="button"
                onClick={handleSaveMappingAndEvaluate}
                disabled={loading || !airTempCol || !procTempCol || !speedCol || !torqueCol || !wearCol}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-5 py-2 rounded-lg text-xs transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
              >
                {loading ? 'Evaluating...' : 'Confirm Mapping & Check Gate'} <Check className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
export default DatasetUploadWizard;
