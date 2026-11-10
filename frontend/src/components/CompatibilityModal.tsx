import React, { useState } from 'react';
import { api, CompatibilityCheck, AnalysisResult } from '../api';
import { ShieldCheck, AlertTriangle, XCircle, CheckCircle2, Play } from 'lucide-react';

interface CompatibilityModalProps {
  check: CompatibilityCheck;
  onAnalysisStarted: (result: AnalysisResult) => void;
  onClose: () => void;
}

export const CompatibilityModal: React.FC<CompatibilityModalProps> = ({ check, onAnalysisStarted, onClose }) => {
  const [acknowledgedCodes, setAcknowledgedCodes] = useState<string[]>([]);
  const [limitationAck, setLimitationAck] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isBlocked = check.compatibility.status === 'INCOMPATIBLE' ||
                    check.compatibility.status === 'UNSUPPORTED_FORMAT' ||
                    check.compatibility.status === 'INSUFFICIENT_DATA' ||
                    check.applicability.level === 'MOSTLY_OUTSIDE_REFERENCE_RANGE';

  const allWarningsAcknowledged = check.requires_acknowledgement.every((code) => acknowledgedCodes.includes(code));
  const canRun = !isBlocked && allWarningsAcknowledged && limitationAck;

  const toggleWarning = (code: string) => {
    if (acknowledgedCodes.includes(code)) {
      setAcknowledgedCodes(acknowledgedCodes.filter((c) => c !== code));
    } else {
      setAcknowledgedCodes([...acknowledgedCodes, code]);
    }
  };

  const handleExecute = async () => {
    setError(null);
    setLoading(true);
    try {
      const runRes = await api.analyses.run(check.id, acknowledgedCodes, limitationAck);
      if (runRes.analysis_result_id) {
        const fullResult = await api.analyses.get(runRes.analysis_result_id);
        onAnalysisStarted(fullResult);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to start analysis.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-5 my-8">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-sky-400" />
              Pre-Execution Compatibility & Gate Verification
            </h3>
            <p className="text-xs text-slate-400 font-mono mt-0.5">Profile: {check.profile.profile_id} ({check.profile.configuration})</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-sm">Close</button>
        </div>

        {error && (
          <div className="p-3 bg-rose-950/30 border border-rose-500/30 rounded-lg text-xs text-rose-300">
            {error}
          </div>
        )}

        {/* Status Highlights */}
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="bg-slate-800/80 p-3 rounded-xl border border-slate-700/60">
            <span className="text-slate-400 uppercase font-semibold">Stage 1: Status</span>
            <div className="text-sm font-bold text-slate-200 mt-1 flex items-center gap-1.5">
              {check.compatibility.status.includes('COMPATIBLE') ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              ) : (
                <XCircle className="w-4 h-4 text-rose-400" />
              )}
              {check.compatibility.status}
            </div>
          </div>

          <div className="bg-slate-800/80 p-3 rounded-xl border border-slate-700/60">
            <span className="text-slate-400 uppercase font-semibold">Stage 2: Applicability</span>
            <div className="text-sm font-bold text-slate-200 mt-1">
              {check.applicability.level}
            </div>
          </div>
        </div>

        {/* Reasons & Remedies List */}
        {check.compatibility.reasons.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Findings & Remedies</h4>
            <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
              {check.compatibility.reasons.map((r, i) => (
                <div key={i} className={`p-3 rounded-lg border text-xs space-y-1 ${
                  r.severity === 'ERROR' ? 'bg-rose-950/20 border-rose-500/20 text-rose-200' : 'bg-amber-950/20 border-amber-500/20 text-amber-200'
                }`}>
                  <div className="font-semibold flex items-center justify-between">
                    <span>[{r.code}] {r.message}</span>
                    <span className="font-mono text-[10px] uppercase px-1.5 py-0.5 rounded bg-slate-900/60">{r.severity}</span>
                  </div>
                  {r.remedy && <div className="text-slate-300"><strong className="text-slate-200">Remedy:</strong> {r.remedy}</div>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Warning Acknowledgements (if any) */}
        {check.requires_acknowledgement.length > 0 && (
          <div className="p-3.5 bg-slate-800/60 border border-slate-700/50 rounded-xl space-y-2">
            <div className="text-xs font-semibold text-amber-400 uppercase tracking-wider">Required Warning Acknowledgements</div>
            {check.requires_acknowledgement.map((code) => (
              <label key={code} className="flex items-start gap-2.5 text-xs text-slate-200 cursor-pointer">
                <input
                  type="checkbox"
                  checked={acknowledgedCodes.includes(code)}
                  onChange={() => toggleWarning(code)}
                  className="mt-0.5 rounded border-slate-700 bg-slate-900 text-sky-500 focus:ring-0"
                />
                <span>I acknowledge warning <strong>{code}</strong> and accept its operational implications.</span>
              </label>
            ))}
          </div>
        )}

        {/* Mandatory Limitation Acknowledgement */}
        <div className="p-3.5 bg-amber-950/30 border border-amber-500/30 rounded-xl space-y-2">
          <div className="text-xs font-semibold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4" />
            <span>Mandatory Reference Model Limitation Statement</span>
          </div>
          <p className="text-xs text-amber-200/90 leading-relaxed font-serif italic">
            "This is a reference-dataset-trained model. It has not been validated on your equipment. Results are advisory."
          </p>
          <label className="flex items-start gap-2.5 text-xs text-slate-200 cursor-pointer pt-1">
            <input
              type="checkbox"
              checked={limitationAck}
              onChange={(e) => setLimitationAck(e.target.checked)}
              className="mt-0.5 rounded border-slate-700 bg-slate-900 text-sky-500 focus:ring-0"
            />
            <span className="font-semibold text-amber-300">I have read, understand, and explicitly acknowledge this limitation.</span>
          </label>
        </div>

        {/* Execution Footer */}
        <div className="flex justify-between items-center pt-2 border-t border-slate-800">
          <button onClick={onClose} className="text-xs text-slate-400 hover:text-white">Cancel</button>
          <button
            onClick={handleExecute}
            disabled={!canRun || loading}
            className="bg-emerald-600 hover:bg-emerald-500 text-white font-medium px-5 py-2.5 rounded-lg text-sm transition-colors flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-emerald-600/20"
          >
            {loading ? 'Executing AI4I Inference...' : 'Authorize & Run Prediction'} <Play className="w-4 h-4 fill-white" />
          </button>
        </div>
      </div>
    </div>
  );
};

