import { useState } from "react";
import type { ExecutionResult } from "../api/types";
import { titleCase } from "../utils/format";

const STATUS_STYLES: Record<ExecutionResult["execution_status"], string> = {
  success: "bg-emerald-100 text-emerald-700",
  simulated: "bg-blue-100 text-blue-700",
  scheduled: "bg-amber-100 text-amber-700",
  blocked: "bg-slate-200 text-slate-700",
  failed: "bg-red-100 text-red-700",
};

export default function ExecutionResultCard({ result }: { result: ExecutionResult }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!result.payment_link_url) return;
    try {
      await navigator.clipboard.writeText(result.payment_link_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API may be unavailable in some contexts.
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900">Execution Result</h3>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLES[result.execution_status]}`}>
          {titleCase(result.execution_status)}
        </span>
      </div>

      <p className="mt-3 text-sm font-medium text-slate-900">{titleCase(result.strategy)}</p>
      <p className="mt-1 text-sm text-slate-600">{result.action_taken}</p>
      <p className="mt-1 text-xs text-slate-500">{result.message}</p>

      {result.recovery_attempt_id !== null && (
        <p className="mt-3 text-xs text-slate-400">Recovery attempt #{result.recovery_attempt_id}</p>
      )}

      {result.payment_link_url && (
        <div className="mt-4 flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3">
          <span className="flex-1 truncate font-mono text-xs text-slate-700">{result.payment_link_url}</span>
          <button
            onClick={handleCopy}
            className="shrink-0 rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700"
          >
            {copied ? "Copied!" : "Copy Payment Link"}
          </button>
        </div>
      )}

      {result.evidence && (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3">
          <p className="text-xs font-semibold text-amber-800">Escalation Evidence</p>
          <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-amber-800">
            {Object.entries(result.evidence)
              .filter(([, value]) => value !== null && value !== undefined)
              .map(([key, value]) => (
                <div key={key} className="contents">
                  <dt className="text-amber-600">{titleCase(key)}</dt>
                  <dd className="truncate font-medium">{String(value)}</dd>
                </div>
              ))}
          </dl>
        </div>
      )}
    </div>
  );
}
