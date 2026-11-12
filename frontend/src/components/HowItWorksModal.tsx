import React, { useState } from 'react';
import { 
  X, 
  ChevronRight, 
  ChevronLeft, 
  Cpu, 
  Database, 
  Sparkles, 
  ShieldCheck, 
  AlertTriangle, 
  ArrowRight,
  TrendingUp,
  Sliders,
  CheckCircle2,
  Layers,
  Wrench
} from 'lucide-react';

interface HowItWorksModalProps {
  isOpen: boolean;
  onClose: () => void;
  onStartUpload?: () => void;
}

export const HowItWorksModal: React.FC<HowItWorksModalProps> = ({
  isOpen,
  onClose,
  onStartUpload,
}) => {
  const [slide, setSlide] = useState<0 | 1 | 2>(0);

  if (!isOpen) return null;

  const slides = [
    {
      title: "1. Upload Machine Operating Datasets",
      subtitle: "Dataset-Driven SaaS • Historical & Batch CSV Ingestion",
      icon: Database,
      accent: "text-sky-600 bg-sky-50 border-sky-200",
      content: (
        <div className="space-y-4 text-xs text-slate-600">
          <p className="leading-relaxed">
            INDUSTRIA AI is a <strong>dataset-driven predictive-maintenance SaaS</strong>. Rather than direct IoT or physical machine control, plant engineers upload historical or exported batch CSV operating datasets from supported machinery assets.
          </p>
          <div className="grid grid-cols-2 gap-2.5">
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <span className="font-bold text-slate-800 text-[11px] block">Air & Process Temperature</span>
              <span className="text-[11px] text-slate-500 font-mono">Kelvin (K), Celsius (°C), or Fahrenheit (°F)</span>
              <p className="text-[11px] text-slate-500 mt-1">Automatically converted to Kelvin: T(K) = T(°C) + 273.15.</p>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <span className="font-bold text-slate-800 text-[11px] block">Rotational Speed & Torque</span>
              <span className="text-[11px] text-slate-500 font-mono">rpm, rad/s • N·m, lbf·ft</span>
              <p className="text-[11px] text-slate-500 mt-1">Measures motor mechanical loading and torque dissipation.</p>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <span className="font-bold text-slate-800 text-[11px] block">Tool Wear Time</span>
              <span className="text-[11px] text-slate-500 font-mono">Minutes (min) or Hours (h)</span>
              <p className="text-[11px] text-slate-500 mt-1">Cumulative cutting tool usage before sharpening or replacement.</p>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <span className="font-bold text-slate-800 text-[11px] block">Dataset Quality Score (Q)</span>
              <span className="text-[11px] text-emerald-700 font-semibold font-mono">0 to 100 Quality Metric</span>
              <p className="text-[11px] text-slate-500 mt-1">Scans completeness, monotonic indices, and valid numerical formats.</p>
            </div>
          </div>
        </div>
      )
    },
    {
      title: "2. Validate & Analyze via Supported ML Pipeline",
      subtitle: "Domain Applicability Gates & Platt-Calibrated XGBoost",
      icon: Cpu,
      accent: "text-indigo-600 bg-indigo-50 border-indigo-200",
      content: (
        <div className="space-y-4 text-xs text-slate-600">
          <p className="leading-relaxed">
            Uploaded datasets are validated against reference operating envelopes before running through the Stage 3 production XGBoost model refitted with Platt sigmoid calibration.
          </p>
          <div className="space-y-2.5">
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 flex items-start gap-3">
              <div className="w-6 h-6 rounded-lg bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center shrink-0">1</div>
              <div>
                <span className="font-bold text-slate-800 text-[11px] block">Domain Applicability Pre-Check</span>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Flags Out-of-Distribution (OOD) readings that exceed reference training bounds to alert engineers of extrapolation risks.
                </p>
              </div>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 flex items-start gap-3">
              <div className="w-6 h-6 rounded-lg bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center shrink-0">2</div>
              <div>
                <span className="font-bold text-slate-800 text-[11px] block">Platt Probability Calibration</span>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Converts raw tree margin scores into calibrated failure probabilities P(failure | z) ∈ [0, 1] using post-hoc logistic scaling.
                </p>
              </div>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 flex items-start gap-3">
              <div className="w-6 h-6 rounded-lg bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center shrink-0">3</div>
              <div>
                <span className="font-bold text-slate-800 text-[11px] block">Operational Decision Bands (&tau;* = 0.0100)</span>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Threshold bands (HIGH: p &ge; 1.0%, MEDIUM: 0.5% &le; p &lt; 1.0%, LOW: p &lt; 0.5%) are cost-optimized decision thresholds derived from a 50:1 false-negative penalty, not universally validated physical machine health states.
                </p>
              </div>
            </div>
          </div>
        </div>
      )
    },
    {
      title: "3. Review Failure Risks, Explanations & Reports",
      subtitle: "TreeSHAP Attributions & Advisory Engineering Decision Support",
      icon: Sparkles,
      accent: "text-amber-600 bg-amber-50 border-amber-200",
      content: (
        <div className="space-y-4 text-xs text-slate-600">
          <p className="leading-relaxed">
            Review estimated failure probabilities, inspect feature contributions, and export audit reports. Predictions are decision-support estimates with no implied time horizon and do not execute automated machine shutdowns.
          </p>
          <div className="grid grid-cols-2 gap-2.5">
            <div className="p-3 bg-rose-50 rounded-xl border border-rose-200">
              <span className="font-bold text-rose-800 text-[11px] block">Positive Risk Drivers (+φ)</span>
              <p className="text-[11px] text-rose-700 mt-0.5">
                Observed sensor values that increased the model failure score relative to baseline prevalence.
              </p>
            </div>
            <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200">
              <span className="font-bold text-emerald-800 text-[11px] block">Dampening Factors (-φ)</span>
              <p className="text-[11px] text-emerald-700 mt-0.5">
                Observed operating features in normal ranges that lowered the model failure estimate.
              </p>
            </div>
          </div>
          <div className="p-3 bg-amber-50/70 border border-amber-200 rounded-xl flex items-start gap-2.5 text-amber-900">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div className="text-[11px]">
              <strong className="font-bold">Advisory Engineering Decision Support:</strong> SHAP values indicate statistical model associations, not physical mechanical causation. Predictions do not estimate time-to-failure or remaining useful life. Use predictions to prioritize routine physical inspections, never as autonomous emergency shutdown triggers.
            </div>
          </div>
        </div>
      )
    }
  ];

  const current = slides[slide];
  const Icon = current.icon;

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
      <div className="bg-white border border-slate-200 rounded-2xl max-w-xl w-full p-6 shadow-2xl space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-3">
            <img src="/logo.png" alt="Industry AI Logo" className="w-8 h-8 object-contain shrink-0" />
            <div>
              <h3 className="text-sm font-bold text-slate-900">{current.title}</h3>
              <p className="text-[11px] text-slate-500 font-medium">{current.subtitle}</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Slide Body */}
        <div className="py-1 min-h-[260px]">
          {current.content}
        </div>

        {/* Footer Navigation */}
        <div className="flex items-center justify-between pt-3 border-t border-slate-100">
          <div className="flex items-center gap-1.5">
            {slides.map((_, idx) => (
              <button
                key={idx}
                onClick={() => setSlide(idx as any)}
                className={`h-2 rounded-full transition-all ${
                  slide === idx ? 'w-6 bg-sky-600' : 'w-2 bg-slate-200 hover:bg-slate-300'
                }`}
                title={`Go to step ${idx + 1}`}
              />
            ))}
          </div>

          <div className="flex items-center gap-2">
            {slide > 0 && (
              <button
                onClick={() => setSlide((slide - 1) as any)}
                className="px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-colors flex items-center gap-1"
              >
                <ChevronLeft className="w-3.5 h-3.5" /> Back
              </button>
            )}

            {slide < slides.length - 1 ? (
              <button
                onClick={() => setSlide((slide + 1) as any)}
                className="px-4 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-700 text-xs font-semibold text-white transition-colors flex items-center gap-1 shadow-sm"
              >
                Next <ChevronRight className="w-3.5 h-3.5" />
              </button>
            ) : (
              <button
                onClick={() => {
                  onClose();
                  if (onStartUpload) onStartUpload();
                }}
                className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-xs font-semibold text-white transition-colors flex items-center gap-1 shadow-sm"
              >
                Get Started <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
export default HowItWorksModal;
