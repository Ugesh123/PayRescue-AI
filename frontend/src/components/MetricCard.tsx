interface MetricCardProps {
  label: string;
  value: string;
  accent?: "default" | "danger" | "success" | "warning";
}

const ACCENT_STYLES: Record<NonNullable<MetricCardProps["accent"]>, string> = {
  default: "text-slate-900",
  danger: "text-red-600",
  success: "text-emerald-600",
  warning: "text-amber-600",
};

export default function MetricCard({ label, value, accent = "default" }: MetricCardProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-2 text-2xl font-semibold ${ACCENT_STYLES[accent]}`}>{value}</p>
    </div>
  );
}
