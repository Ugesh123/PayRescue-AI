import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { StrategyPerformance } from "../../api/types";
import { titleCase } from "../../utils/format";

export default function StrategySuccessChart({ data }: { data: StrategyPerformance[] }) {
  if (data.length === 0) {
    return <p className="py-8 text-center text-sm text-slate-400">No strategy data yet.</p>;
  }

  const chartData = data.map((row) => ({
    name: titleCase(row.strategy),
    "Success Rate": Math.round(row.success_rate * 100),
  }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-15} textAnchor="end" height={50} />
        <YAxis tick={{ fontSize: 11 }} unit="%" domain={[0, 100]} />
        <Tooltip formatter={(value: number) => `${value}%`} />
        <Bar dataKey="Success Rate" fill="#0f172a" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
