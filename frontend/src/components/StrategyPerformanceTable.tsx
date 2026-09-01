import type { StrategyPerformance } from "../api/types";
import { formatPercent, titleCase } from "../utils/format";

export default function StrategyPerformanceTable({ data }: { data: StrategyPerformance[] }) {
  if (data.length === 0) {
    return <p className="text-sm text-slate-500">No recovery attempts recorded yet.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead>
          <tr className="text-left text-xs font-medium uppercase tracking-wide text-slate-400">
            <th className="py-2 pr-4">Strategy</th>
            <th className="py-2 pr-4">Attempts</th>
            <th className="py-2 pr-4">Successful</th>
            <th className="py-2 pr-4">Success Rate</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {data.map((row) => (
            <tr key={row.strategy}>
              <td className="py-2 pr-4 font-medium text-slate-800">{titleCase(row.strategy)}</td>
              <td className="py-2 pr-4 text-slate-600">{row.total_attempts}</td>
              <td className="py-2 pr-4 text-slate-600">{row.successful_attempts}</td>
              <td className="py-2 pr-4 font-medium text-slate-800">{formatPercent(row.success_rate)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
