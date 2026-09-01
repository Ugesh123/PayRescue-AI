import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getTransactions, seedTransactions, ApiError } from "../api/client";
import type { TransactionRead, TransactionStatus } from "../api/types";
import TransactionTable from "../components/TransactionTable";
import { LoadingState, ErrorState, EmptyState } from "../components/StateViews";

const PAGE_SIZE = 10;
const STATUS_OPTIONS: Array<TransactionStatus | "all"> = ["all", "failed", "captured", "created", "recovered"];

export default function TransactionsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const statusFilter = (searchParams.get("status") as TransactionStatus | null) ?? "all";
  const page = Number(searchParams.get("page") ?? "0");

  const [transactions, setTransactions] = useState<TransactionRead[]>([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [errorMessage, setErrorMessage] = useState("");
  const [isSeeding, setIsSeeding] = useState(false);

  const load = () => {
    setStatus("loading");
    getTransactions({
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
      status: statusFilter === "all" ? undefined : statusFilter,
    })
      .then((data) => {
        setTransactions(data.items);
        setTotal(data.total);
        setStatus("success");
      })
      .catch((err) => {
        setErrorMessage(err instanceof ApiError ? err.message : "Failed to load transactions");
        setStatus("error");
      });
  };

  useEffect(load, [statusFilter, page]);

  const updateStatusFilter = (value: string) => setSearchParams({ status: value, page: "0" });
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const handleSeedDemoData = () => {
    setIsSeeding(true);
    seedTransactions()
      .then(() => load())
      .catch((err) => {
        setErrorMessage(err instanceof ApiError ? err.message : "Failed to load demo data");
        setStatus("error");
      })
      .finally(() => setIsSeeding(false));
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Transactions</h1>
          <p className="text-sm text-slate-500">{total} total</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleSeedDemoData}
            disabled={isSeeding}
            title="Development/demo only — seeds sample merchants and transactions"
            className="rounded-md border border-dashed border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-500 hover:border-slate-400 hover:text-slate-700 disabled:opacity-50"
          >
            {isSeeding ? "Loading demo data..." : "🧪 Load Demo Data"}
          </button>
          <select
            value={statusFilter}
            onChange={(e) => updateStatusFilter(e.target.value)}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700"
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option === "all" ? "All statuses" : option}
              </option>
            ))}
          </select>
        </div>
      </div>

      {status === "loading" && <LoadingState label="Loading transactions..." />}
      {status === "error" && <ErrorState message={errorMessage} onRetry={load} />}
      {status === "success" && transactions.length === 0 && (
        <EmptyState message="No transactions match this filter. Try 'Load Demo Data' for sample transactions." />
      )}
      {status === "success" && transactions.length > 0 && (
        <>
          <TransactionTable transactions={transactions} />
          <div className="flex items-center justify-between text-sm text-slate-500">
            <button
              disabled={page === 0}
              onClick={() => setSearchParams({ status: statusFilter, page: String(page - 1) })}
              className="rounded-md border border-slate-300 px-3 py-1.5 disabled:opacity-40"
            >
              Previous
            </button>
            <span>
              Page {page + 1} of {totalPages}
            </span>
            <button
              disabled={page + 1 >= totalPages}
              onClick={() => setSearchParams({ status: statusFilter, page: String(page + 1) })}
              className="rounded-md border border-slate-300 px-3 py-1.5 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
