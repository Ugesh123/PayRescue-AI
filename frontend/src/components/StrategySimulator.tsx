import type { RecoveryDecision } from "../api/types";
import { formatPercent, titleCase } from "../utils/format";
import StrategyCard from "./StrategyCard";

export default function StrategySimulator({ decision }: { decision: RecoveryDecision }) {
  const sortedCandidates = [...decision.candidate_strategies].sort((a, b) => b.score - a.score);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900">🧠 Recovery Strategy Simulator</h3>
        <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700">
          {sortedCandidates.length} {sortedCandidates.length === 1 ? "strategy" : "strategies"} evaluated
        </span>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {sortedCandidates.map((candidate) => (
          <StrategyCard key={candidate.strategy} candidate={candidate} isSelected={candidate.strategy === decision.strategy} />
        ))}
      </div>

      <div className="mt-5 rounded-lg border border-emerald-200 bg-emerald-50 p-4">
        <p className="text-xs font-medium uppercase tracking-wide text-emerald-700">✅ Selected Strategy</p>
        <p className="mt-1 text-lg font-semibold text-emerald-900">{titleCase(decision.strategy)}</p>
        <p className="mt-1 text-sm text-emerald-800">{decision.reason}</p>

        <div className="mt-4 grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
          <Metric label="Confidence" value={formatPercent(decision.confidence)} />
          <Metric label="Urgency" value={titleCase(decision.urgency)} />
          <Metric label="Success Probability" value={formatPercent(decision.estimated_success_probability)} />
          <Metric label="Next Step" value={decision.next_step} />
        </div>

        <div className="mt-4 flex flex-wrap gap-2 text-xs">
          <Flag active={decision.requires_customer_action} label="Requires customer action" />
          <Flag active={decision.requires_human_review} label="Requires human review" />
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-emerald-600">{label}</p>
      <p className="mt-0.5 font-medium text-emerald-900">{value}</p>
    </div>
  );
}

function Flag({ active, label }: { active: boolean; label: string }) {
  return (
    <span className={`rounded-full px-2.5 py-1 font-medium ${active ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-500"}`}>
      {active ? "⚠️ " : "— "}
      {label}
    </span>
  );
}
