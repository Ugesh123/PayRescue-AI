import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function RevenueBarChart({
  revenueAtRisk,
  revenueRecovered,
}: {
  revenueAtRisk: number;
  revenueRecovered: number;
}) {
  const data = [
    { name: "At Risk", value: Math.round(revenueAtRisk / 100) },
    { name: "Recovered", value: Math.round(revenueRecovered / 100) },
  ];

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="name" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip formatter={(value: number) => `₹${value.toLocaleString("en-IN")}`} />
        <Bar dataKey="value" fill="#334155" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
