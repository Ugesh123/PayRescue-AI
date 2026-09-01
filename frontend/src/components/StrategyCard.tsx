import type { CandidateStrategy } from "../api/types";
import { formatPercent, titleCase } from "../utils/format";

export default function StrategyCard({
  candidate,
  isSelected,
}: {
  candidate: CandidateStrategy;
  isSelected: boolean;
}) {
  const hasHistoricalInfluence = candidate.reason.toLowerCase().includes("historical performance");

  return (
    <div
      className={`rounded-lg border p-4 transition-colors ${
        isSelected ? "border-emerald-400 bg-emerald-50" : "border-slate-200 bg-white"
      }`}
    >
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-900">{titleCase(candidate.strategy)}</p>
        {isSelected && (
          <span className="rounded-full bg-emerald-600 px-2 py-0.5 text-[11px] font-semibold text-white">
            SELECTED
          </span>
        )}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 text-xs text-slate-500">
        <div>
          <p className="text-slate-400">Score</p>
          <p className="text-sm font-medium text-slate-800">{formatPercent(candidate.score)}</p>
        </div>
        <div>
          <p className="text-slate-400">Success probability</p>
          <p className="text-sm font-medium text-slate-800">
            {formatPercent(candidate.estimated_success_probability)}
          </p>
        </div>
      </div>
      <p className="mt-3 text-xs text-slate-600">{candidate.reason}</p>
      {hasHistoricalInfluence && (
        <p className="mt-2 rounded-md bg-blue-50 px-2 py-1 text-[11px] font-medium text-blue-700">
          📈 Historical performance influenced this score
        </p>
      )}
    </div>
  );
}
