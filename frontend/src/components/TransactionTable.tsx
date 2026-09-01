import { Link } from "react-router-dom";
import type { TransactionRead } from "../api/types";
import { formatCurrency, formatDateTime } from "../utils/format";
import StatusBadge from "./StatusBadge";

export default function TransactionTable({ transactions }: { transactions: TransactionRead[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-slate-500">ID</th>
            <th className="px-4 py-3 text-left font-medium text-slate-500">Order ID</th>
            <th className="px-4 py-3 text-left font-medium text-slate-500">Amount</th>
            <th className="px-4 py-3 text-left font-medium text-slate-500">Status</th>
            <th className="px-4 py-3 text-left font-medium text-slate-500">Failure Reason</th>
            <th className="px-4 py-3 text-left font-medium text-slate-500">Created</th>
            <th className="px-4 py-3 text-left font-medium text-slate-500">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {transactions.map((txn) => (
            <tr key={txn.id} className="hover:bg-slate-50">
              <td className="px-4 py-3 text-slate-700">#{txn.id}</td>
              <td className="px-4 py-3 font-mono text-xs text-slate-600">{txn.razorpay_order_id}</td>
              <td className="px-4 py-3 text-slate-900">{formatCurrency(txn.amount, txn.currency)}</td>
              <td className="px-4 py-3">
                <StatusBadge status={txn.status} />
              </td>
              <td className="max-w-xs truncate px-4 py-3 text-slate-500">{txn.failure_reason ?? "—"}</td>
              <td className="px-4 py-3 text-slate-500">{formatDateTime(txn.created_at)}</td>
              <td className="px-4 py-3">
                <Link
                  to={`/transactions/${txn.id}`}
                  className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700"
                >
                  {txn.status === "failed" ? "Analyze" : "View"}
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
