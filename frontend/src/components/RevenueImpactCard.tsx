import type { DashboardSummary, RecoveryAnalytics } from "../api/types";
import { formatCurrency, formatPercent } from "../utils/format";
import MetricCard from "./MetricCard";

export default function RevenueImpactCard({
  summary,
  analytics,
}: {
  summary: DashboardSummary;
  analytics: RecoveryAnalytics;
}) {
  const potentialRecoverableValue = Math.round(summary.revenue_at_risk * analytics.recovery_rate);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-900">Revenue Impact</h2>
      <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard label="Revenue at Risk" value={formatCurrency(summary.revenue_at_risk)} accent="warning" />
        <MetricCard label="Revenue Recovered" value={formatCurrency(summary.revenue_recovered)} accent="success" />
        <MetricCard label="Recovery Rate" value={formatPercent(analytics.recovery_rate)} accent="success" />
        <MetricCard label="Potential Recoverable" value={formatCurrency(potentialRecoverableValue)} />
      </div>
      <p className="mt-3 text-xs text-slate-400">
        Potential recoverable value is estimated by applying the current recovery rate (
        {formatPercent(analytics.recovery_rate)}) to today's revenue at risk — not a guaranteed amount.
      </p>
    </div>
  );
}
