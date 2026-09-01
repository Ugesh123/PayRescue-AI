import type { RecoveryDecision } from "../api/types";

export default function SafetyCheckCard({ decision }: { decision: RecoveryDecision }) {
  const approved = !decision.requires_human_review;

  return (
    <div
      className={`rounded-lg border p-4 text-sm ${
        approved ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-amber-300 bg-amber-50 text-amber-800"
      }`}
    >
      <p className="font-medium">
        {approved ? "✅ Approved for automated recovery" : "🛡 Requires human review before any automatic action"}
      </p>
      {decision.requires_customer_action && (
        <p className="mt-1 text-xs opacity-80">This strategy also requires the customer to take action.</p>
      )}
    </div>
  );
}
