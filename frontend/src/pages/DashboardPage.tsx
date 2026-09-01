import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  getDashboardSummary,
  getTransactions,
  getRecoveryAnalytics,
  getAnomalies,
  ApiError,
} from "../api/client";
import type { DashboardSummary, TransactionRead, RecoveryAnalytics, Anomaly } from "../api/types";
import MetricCard from "../components/MetricCard";
import TransactionTable from "../components/TransactionTable";
import RevenueImpactCard from "../components/RevenueImpactCard";
import StrategyPerformanceTable from "../components/StrategyPerformanceTable";
import CategoryPerformanceTable from "../components/CategoryPerformanceTable";
import SystemIntelligenceSection from "../components/SystemIntelligenceSection";
import StrategySuccessChart from "../components/charts/StrategySuccessChart";
import CategoryRecoveryChart from "../components/charts/CategoryRecoveryChart";
import RevenueBarChart from "../components/charts/RevenueBarChart";
import { LoadingState, ErrorState, EmptyState } from "../components/StateViews";
import { titleCase } from "../utils/format";

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [recentFailed, setRecentFailed] = useState<TransactionRead[]>([]);
  const [analytics, setAnalytics] = useState<RecoveryAnalytics | null>(null);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [errorMessage, setErrorMessage] = useState("");

  const load = () => {
    setStatus("loading");
    Promise.all([
      getDashboardSummary(),
      getTransactions({ status: "failed", limit: 5 }),
      getRecoveryAnalytics(),
      getAnomalies(),
    ])
      .then(([summaryData, failedData, analyticsData, anomalyData]) => {
        setSummary(summaryData);
        setRecentFailed(failedData.items);
        setAnalytics(analyticsData);
        setAnomalies(anomalyData.anomalies);
        setStatus("success");
      })
      .catch((err) => {
        setErrorMessage(err instanceof ApiError ? err.message : "Failed to load dashboard data");
        setStatus("error");
      });
  };

  useEffect(load, []);

  if (status === "loading") return <LoadingState label="Loading dashboard..." />;
  if (status === "error") return <ErrorState message={errorMessage} onRetry={load} />;
  if (!summary || !analytics) return null;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Dashboard</h1>
        <p className="text-sm text-slate-500">Overview of payment health and recovery performance</p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
        <MetricCard label="Total Transactions" value={String(summary.total_transactions)} />
        <MetricCard label="Failed Payments" value={String(summary.total_failed)} accent="danger" />
        <MetricCard label="Captured Payments" value={String(summary.total_captured)} />
      </div>

      <RevenueImpactCard summary={summary} analytics={analytics} />

      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">Recovery Analytics</h2>
        <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-3">
          <MetricCard label="Total Recovery Attempts" value={String(analytics.total_recovery_attempts)} />
          <MetricCard label="Avg Attempts / Recovered" value={analytics.average_attempts_per_recovered_transaction.toFixed(2)} />
          <MetricCard
            label="Most Successful Strategy"
            value={analytics.most_successful_strategy ? titleCase(analytics.most_successful_strategy) : "—"}
          />
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-900">Success Rate by Strategy</h3>
          <div className="mt-3">
            <StrategySuccessChart data={analytics.strategy_performance} />
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-900">Recovery Rate by Category</h3>
          <div className="mt-3">
            <CategoryRecoveryChart data={analytics.category_performance} />
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-2">
          <h3 className="text-sm font-semibold text-slate-900">Revenue at Risk vs Recovered</h3>
          <div className="mt-3">
            <RevenueBarChart revenueAtRisk={summary.revenue_at_risk} revenueRecovered={summary.revenue_recovered} />
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-900">Strategy Performance</h3>
          <div className="mt-3">
            <StrategyPerformanceTable data={analytics.strategy_performance} />
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-900">Category Performance</h3>
          <div className="mt-3">
            <CategoryPerformanceTable data={analytics.category_performance} />
          </div>
        </div>
      </div>

      <SystemIntelligenceSection anomalies={anomalies} />

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900">Recent Failed Transactions</h2>
          <Link to="/transactions?status=failed" className="text-xs font-medium text-slate-600 hover:text-slate-900">
            View all →
          </Link>
        </div>
        {recentFailed.length === 0 ? (
          <EmptyState message="No failed transactions right now." />
        ) : (
          <TransactionTable transactions={recentFailed} />
        )}
      </div>
    </div>
  );
}
