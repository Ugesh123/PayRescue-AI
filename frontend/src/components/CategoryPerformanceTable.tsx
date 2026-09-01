import type { CategoryPerformance } from "../api/types";
import { formatPercent, titleCase } from "../utils/format";

export default function CategoryPerformanceTable({ data }: { data: CategoryPerformance[] }) {
  if (data.length === 0) {
    return <p className="text-sm text-slate-500">No diagnosed failures recorded yet.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead>
          <tr className="text-left text-xs font-medium uppercase tracking-wide text-slate-400">
            <th className="py-2 pr-4">Category</th>
            <th className="py-2 pr-4">Failures</th>
            <th className="py-2 pr-4">Recovered</th>
            <th className="py-2 pr-4">Recovery Rate</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {data.map((row) => (
            <tr key={row.category}>
              <td className="py-2 pr-4 font-medium text-slate-800">{titleCase(row.category)}</td>
              <td className="py-2 pr-4 text-slate-600">{row.total_failed}</td>
              <td className="py-2 pr-4 text-slate-600">{row.total_recovered}</td>
              <td className="py-2 pr-4 font-medium text-slate-800">{formatPercent(row.recovery_rate)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
