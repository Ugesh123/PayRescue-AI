import type { Anomaly } from "../api/types";
import { titleCase } from "../utils/format";

const SEVERITY_STYLES: Record<Anomaly["severity"], string> = {
  low: "border-slate-200 bg-slate-50",
  medium: "border-amber-300 bg-amber-50",
  high: "border-red-400 bg-red-50",
};

const SEVERITY_BADGE: Record<Anomaly["severity"], string> = {
  low: "bg-slate-200 text-slate-700",
  medium: "bg-amber-200 text-amber-800",
  high: "bg-red-600 text-white",
};

export default function AnomalyCard({ anomaly }: { anomaly: Anomaly }) {
  const isHigh = anomaly.severity === "high";
  return (
    <div className={`rounded-lg border p-4 ${SEVERITY_STYLES[anomaly.severity]} ${isHigh ? "border-2" : ""}`}>
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-900">
          {isHigh ? "⚠️ " : "• "}
          {titleCase(anomaly.pattern)}
        </p>
        <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase ${SEVERITY_BADGE[anomaly.severity]}`}>
          {anomaly.severity}
        </span>
      </div>
      <p className="mt-1 text-sm text-slate-600">{anomaly.message}</p>
      <p className="mt-2 text-xs text-slate-500">
        Affected transactions: <span className="font-medium text-slate-700">{anomaly.affected_transaction_count}</span>
      </p>
      <div className="mt-2 rounded-md bg-white/60 px-2.5 py-1.5 text-xs text-slate-600">
        <span className="font-medium text-slate-700">Recommendation: </span>
        {anomaly.recommended_action}
      </div>
    </div>
  );
}
