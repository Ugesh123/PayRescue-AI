import type { DiagnosisResult } from "../api/types";
import { formatPercent, titleCase } from "../utils/format";

export default function DiagnosisCard({ diagnosis }: { diagnosis: DiagnosisResult }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900">🔎 Failure Diagnosis</h3>
        <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700">
          {formatPercent(diagnosis.confidence)} confidence
        </span>
      </div>
      <p className="mt-3 text-lg font-semibold text-slate-900">{titleCase(diagnosis.category)}</p>
      <p className="mt-1 text-sm text-slate-600">{diagnosis.reason}</p>
      <div className="mt-4 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500">
        Recommended next step:{" "}
        <span className="font-medium text-slate-700">{titleCase(diagnosis.recommended_next_step)}</span>
      </div>
    </div>
  );
}
