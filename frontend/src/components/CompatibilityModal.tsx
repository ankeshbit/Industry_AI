import React, { useState } from 'react';
import { api, CompatibilityCheck, AnalysisResult } from '../api';
import { ShieldCheck, AlertTriangle, XCircle, CheckCircle2, Play, X } from 'lucide-react';

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
      } else {
        setError(`Analysis did not complete (job status: ${runRes.status}). Please check the job queue and retry.`);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to start inference analysis.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 overflow-y-auto">
      <div className="bg-white border border-slate-200 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-5 my-8">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-sky-600" />
              Pre-Execution Compatibility & Gate Verification
            </h3>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              Profile: {check.profile.profile_id} ({check.profile.configuration})
            </p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 p-1 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700">
            {error}
          </div>
        )}

        {/* Status Highlights */}
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200">
            <span className="text-slate-500 uppercase font-semibold text-[10px] tracking-wider">Stage 1: Schema Status</span>
            <div className="text-sm font-bold text-slate-900 mt-1 flex items-center gap-1.5">
              {(check.compatibility.status === 'COMPATIBLE' || check.compatibility.status === 'COMPATIBLE_WITH_WARNINGS') ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              ) : (
                <XCircle className="w-4 h-4 text-rose-600" />
              )}
              {check.compatibility.status}
            </div>
          </div>

          <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200">
            <span className="text-slate-500 uppercase font-semibold text-[10px] tracking-wider">Stage 2: Domain Applicability</span>
            <div className="text-sm font-bold text-slate-900 mt-1">
              {check.applicability.level}
            </div>
          </div>
        </div>

        {/* Reasons & Remedies List */}
        {check.compatibility.reasons.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Findings & Remedies</h4>
            <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
              {check.compatibility.reasons.map((r, i) => (
                <div key={i} className={`p-3 rounded-lg border text-xs space-y-1 ${
                  r.severity === 'ERROR' ? 'bg-rose-50 border-rose-200 text-rose-800' : 'bg-amber-50 border-amber-200 text-amber-800'
                }`}>
                  <div className="font-semibold flex items-center justify-between">
                    <span>[{r.code}] {r.message}</span>
                    <span className="font-mono text-[10px] uppercase px-1.5 py-0.5 rounded bg-white border border-current font-bold">
                      {r.severity}
                    </span>
                  </div>
                  {r.remedy && <div className="text-slate-700 text-[11px]"><strong className="text-slate-900">Remedy:</strong> {r.remedy}</div>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Warning Acknowledgements (if any) */}
        {check.requires_acknowledgement.length > 0 && (
          <div className="p-3.5 bg-amber-50/70 border border-amber-200 rounded-xl space-y-2">
            <div className="text-xs font-bold text-amber-900 uppercase tracking-wider">Required Warning Acknowledgements</div>
            {check.requires_acknowledgement.map((code) => (
              <label key={code} className="flex items-start gap-2.5 text-xs text-slate-800 cursor-pointer">
                <input
                  type="checkbox"
                  checked={acknowledgedCodes.includes(code)}
                  onChange={() => toggleWarning(code)}
                  className="mt-0.5 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                />
                <span>I acknowledge warning <strong>{code}</strong> and accept its operational implications.</span>
              </label>
            ))}
          </div>
        )}

        {/* Mandatory Limitation Acknowledgement */}
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-2">
          <div className="text-xs font-bold text-amber-900 uppercase tracking-wider flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <span>Mandatory Reference Model Limitation Statement</span>
          </div>
          <p className="text-xs text-amber-900 leading-relaxed font-serif italic">
            "This is a reference-dataset-trained model. It has not been validated on your equipment. Results are advisory."
          </p>
          <label className="flex items-start gap-2.5 text-xs text-slate-800 cursor-pointer pt-1">
            <input
              type="checkbox"
              checked={limitationAck}
              onChange={(e) => setLimitationAck(e.target.checked)}
              className="mt-0.5 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
            />
            <span className="font-semibold text-amber-950">I have read, understand, and explicitly acknowledge this limitation.</span>
          </label>
        </div>

        {/* Execution Footer */}
        <div className="flex justify-between items-center pt-3 border-t border-slate-100">
          <button onClick={onClose} className="text-xs text-slate-500 hover:text-slate-800 font-medium">Cancel</button>
          <button
            onClick={handleExecute}
            disabled={!canRun || loading}
            className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-5 py-2.5 rounded-lg text-xs transition-colors flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
          >
            {loading ? 'Executing AI4I Inference...' : 'Authorize & Run Prediction'} <Play className="w-3.5 h-3.5 fill-white" />
          </button>
        </div>
      </div>
    </div>
  );
};
export default CompatibilityModal;
