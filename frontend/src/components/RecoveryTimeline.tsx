import type { RecoveryAttemptRead } from "../api/types";
import { formatDateTime, titleCase } from "../utils/format";

const STATUS_STYLES: Record<RecoveryAttemptRead["status"], string> = {
  pending: "bg-amber-100 text-amber-700",
  success: "bg-emerald-100 text-emerald-700",
  failed: "bg-red-100 text-red-700",
};

export default function RecoveryTimeline({ attempts }: { attempts: RecoveryAttemptRead[] }) {
  if (attempts.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-5 text-sm text-slate-500 shadow-sm">
        No recovery attempts yet for this transaction.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-900">Recovery History</h3>
      <ul className="mt-4 space-y-3">
        {attempts.map((attempt) => (
          <li key={attempt.id} className="flex items-center justify-between border-l-2 border-slate-200 pl-3">
            <div>
              <p className="text-sm font-medium text-slate-800">
                {attempt.strategy ? titleCase(attempt.strategy) : "Unknown strategy"}
              </p>
              <p className="text-xs text-slate-400">
                {formatDateTime(attempt.created_at)} · Attempt #{attempt.id}
              </p>
            </div>
            <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLES[attempt.status]}`}>
              {titleCase(attempt.status)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
