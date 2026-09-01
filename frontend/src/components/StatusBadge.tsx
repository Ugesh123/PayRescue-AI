import type { TransactionStatus } from "../api/types";

const STATUS_STYLES: Record<TransactionStatus, string> = {
  created: "bg-slate-100 text-slate-700",
  failed: "bg-red-100 text-red-700",
  captured: "bg-emerald-100 text-emerald-700",
  recovered: "bg-blue-100 text-blue-700",
};

export default function StatusBadge({ status }: { status: TransactionStatus }) {
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${STATUS_STYLES[status]}`}>
      {status}
    </span>
  );
}
