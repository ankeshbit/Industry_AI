import React, { useState } from 'react';
import { ShieldAlert, AlertTriangle, CheckCircle, Info, ChevronDown, ChevronUp } from 'lucide-react';
import { AnalysisResult } from '../api';

interface TrustPanelProps {
  result: AnalysisResult;
}

export const TrustPanel: React.FC<TrustPanelProps> = ({ result }) => {
  const [evidenceOpen, setEvidenceOpen] = useState(false);

  const getApplicabilityBadge = (level: string) => {
    switch (level) {
      case 'IN_REFERENCE_RANGE':
        return <span className="px-2.5 py-1 text-xs font-semibold rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">IN REFERENCE RANGE</span>;
      case 'PARTLY_OUTSIDE_REFERENCE_RANGE':
        return <span className="px-2.5 py-1 text-xs font-semibold rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">PARTLY OUTSIDE REFERENCE RANGE</span>;
      case 'MOSTLY_OUTSIDE_REFERENCE_RANGE':
        return <span className="px-2.5 py-1 text-xs font-semibold rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">MOSTLY OUTSIDE REFERENCE RANGE</span>;
      default:
        return <span className="px-2.5 py-1 text-xs font-semibold rounded bg-slate-500/10 text-slate-400 border border-slate-500/20">{level}</span>;
    }
  };

  return (
    <div className="bg-slate-800/90 border border-slate-700/80 rounded-xl p-5 shadow-xl space-y-4 text-sm">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-700/60 pb-3">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-amber-400" />
          <h3 className="font-semibold text-slate-100 text-base">Model Trust & Provenance Panel</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20">
            {result.provenance.model.trained_on}
          </span>
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
            TIER: {result.trust.reliability_tier}
          </span>
        </div>
      </div>

      {/* Core 3-Stage Chips */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {/* Stage 1: Compatibility */}
        <div className="bg-slate-900/60 p-3.5 rounded-lg border border-slate-700/40">
          <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold mb-1">Stage 1: Compatibility</div>
          {/* Previously hard-coded to "COMPATIBLE" even for COMPATIBLE_WITH_WARNINGS results */}
          <div className="flex items-center gap-2 mt-1">
            {result.trust.compatibility === 'COMPATIBLE' ? (
              <CheckCircle className="w-4 h-4 text-emerald-400" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-amber-400" />
            )}
            <span className="font-medium text-slate-200">{result.trust.compatibility}</span>
          </div>
          <p className="text-xs text-slate-400 mt-1">Dataset format, schema, and units matched to profile.</p>
        </div>

        {/* Stage 2: Applicability */}
        <div className="bg-slate-900/60 p-3.5 rounded-lg border border-slate-700/40">
          <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold mb-1">Stage 2: Applicability</div>
          <div className="mt-1">{getApplicabilityBadge(result.trust.applicability)}</div>
          <p className="text-xs text-slate-400 mt-1">
            {result.ood_summary.flagged_rows} of {result.ood_summary.total_rows} rows outside range ({Math.round(result.ood_summary.flagged_fraction * 100)}%).
            <span className="block italic text-slate-500 mt-0.5">A warning mechanism, not proof of reliability.</span>
          </p>
        </div>

        {/* Stage 3: Reliability Tier */}
        <div className="bg-slate-900/60 p-3.5 rounded-lg border border-slate-700/40">
          <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold mb-1">Stage 3: Reliability Tier</div>
          <div className="text-amber-400 font-medium mt-1">{result.trust.label}</div>
          <p className="text-xs text-slate-400 mt-1">Customer-specific validation: <span className="text-slate-300 font-semibold">None performed</span>.</p>
        </div>
      </div>

      {/* Mandatory Limitations & Advisory Disclaimers */}
      <div className="bg-amber-950/20 border border-amber-500/20 rounded-lg p-3.5 text-xs text-amber-200/90 space-y-1.5">
        <div className="flex items-center gap-1.5 font-semibold text-amber-300">
          <AlertTriangle className="w-4 h-4" />
          <span>Operational Advisory & Limitations</span>
        </div>
        <p className="leading-relaxed">
          <strong>Advisory Notice:</strong>{' '}
          {result.advisory_notice ?? 'Predictions from public reference-dataset models do not represent validated performance on your equipment. Not a safety assessment.'}
        </p>
        <p className="leading-relaxed text-slate-300">
          <strong>Semantics:</strong> {result.semantics}
        </p>
        <p className="text-slate-400 italic">
          {result.explanation_disclaimer}
        </p>
      </div>

      {/* Expandable Evidence Details */}
      <div className="border-t border-slate-700/40 pt-2">
        <button
          onClick={() => setEvidenceOpen(!evidenceOpen)}
          className="flex items-center justify-between w-full text-xs text-slate-400 hover:text-slate-200 py-1 transition-colors"
        >
          <span>Evaluation Evidence & Model Card Details</span>
          {evidenceOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {evidenceOpen && (
          <div className="mt-3 p-3 bg-slate-900/80 rounded-lg text-xs space-y-2 border border-slate-700/40 font-mono text-slate-300">
            <div><strong>Registered Model:</strong> {result.provenance.model.registry_name} v{result.provenance.model.version}</div>
            <div><strong>Configuration:</strong> {result.configuration}</div>
            <div><strong>Training Domain:</strong> {result.provenance.model.training_domain}</div>
            <div><strong>Dataset Version ID:</strong> {result.provenance.dataset.id}</div>
            <div><strong>Computed At:</strong> {result.provenance.computed_at}</div>
            <div className="mt-2 text-slate-400">
              Model Card URI: {result.evaluation_sections.reference_dataset_evaluation.model_card_uri ?? 'n/a'}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

