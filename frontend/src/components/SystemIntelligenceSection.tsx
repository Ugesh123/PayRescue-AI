import type { Anomaly } from "../api/types";
import AnomalyCard from "./AnomalyCard";

export default function SystemIntelligenceSection({ anomalies }: { anomalies: Anomaly[] }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-900">System Intelligence</h2>
      <p className="text-xs text-slate-500">Automated pattern detection across recent failures</p>

      {anomalies.length === 0 ? (
        <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
          ✅ No active anomalies detected
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          {anomalies.map((anomaly, index) => (
            <AnomalyCard key={`${anomaly.pattern}-${index}`} anomaly={anomaly} />
          ))}
        </div>
      )}
    </div>
  );
}
