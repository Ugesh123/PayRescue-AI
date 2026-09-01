import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getTransaction,
  getDiagnosis,
  getRecoveryStrategy,
  getRecoveryAttempts,
  executeRecovery,
  agentRecover,
  ApiError,
} from "../api/client";
import type {
  TransactionRead,
  DiagnosisResult,
  RecoveryDecision,
  RecoveryAttemptRead,
  ExecutionResult,
} from "../api/types";
import { formatCurrency, titleCase } from "../utils/format";
import StatusBadge from "../components/StatusBadge";
import DiagnosisCard from "../components/DiagnosisCard";
import StrategySimulator from "../components/StrategySimulator";
import SafetyCheckCard from "../components/SafetyCheckCard";
import ExecutionResultCard from "../components/ExecutionResultCard";
import RecoveryTimeline from "../components/RecoveryTimeline";
import AgentProgressStages from "../components/AgentProgressStages";
import WorkflowStage from "../components/WorkflowStage";
import { LoadingState, ErrorState } from "../components/StateViews";

type PageStatus = "loading" | "success" | "error" | "not_failed";

export default function TransactionRecoveryPage() {
  const { id } = useParams<{ id: string }>();
  const transactionId = Number(id);

  const [transaction, setTransaction] = useState<TransactionRead | null>(null);
  const [diagnosis, setDiagnosis] = useState<DiagnosisResult | null>(null);
  const [decision, setDecision] = useState<RecoveryDecision | null>(null);
  const [attempts, setAttempts] = useState<RecoveryAttemptRead[]>([]);
  const [executionResult, setExecutionResult] = useState<ExecutionResult | null>(null);

  const [pageStatus, setPageStatus] = useState<PageStatus>("loading");
  const [errorMessage, setErrorMessage] = useState("");
  const [isExecuting, setIsExecuting] = useState(false);
  const [isRunningAgent, setIsRunningAgent] = useState(false);
  const [lastActionSource, setLastActionSource] = useState<"manual" | "agent" | null>(null);

  const load = () => {
    setPageStatus("loading");
    setExecutionResult(null);

    getTransaction(transactionId)
      .then((txn) => {
        setTransaction(txn);

        if (txn.status !== "failed") {
          return getRecoveryAttempts(transactionId).then((attemptsData) => {
            setAttempts(attemptsData);
            setPageStatus("not_failed");
          });
        }

        return Promise.all([
          getDiagnosis(transactionId),
          getRecoveryStrategy(transactionId),
          getRecoveryAttempts(transactionId),
        ]).then(([diagnosisData, decisionData, attemptsData]) => {
          setDiagnosis(diagnosisData);
          setDecision(decisionData);
          setAttempts(attemptsData);
          setPageStatus("success");
        });
      })
      .catch((err) => {
        setErrorMessage(err instanceof ApiError ? err.message : "Failed to load transaction");
        setPageStatus("error");
      });
  };

  useEffect(load, [transactionId]);

  const refreshAttempts = () => getRecoveryAttempts(transactionId).then(setAttempts);

  const handleExecute = () => {
    setIsExecuting(true);
    setLastActionSource("manual");
    executeRecovery(transactionId)
      .then((result) => {
        setExecutionResult(result);
        return refreshAttempts();
      })
      .catch((err) => setErrorMessage(err instanceof ApiError ? err.message : "Failed to execute recovery"))
      .finally(() => setIsExecuting(false));
  };

  const handleRunAgent = () => {
    setIsRunningAgent(true);
    setLastActionSource("agent");
    setExecutionResult(null);
    agentRecover(transactionId)
      .then((result) => {
        setExecutionResult(result);
        return refreshAttempts();
      })
      .catch((err) => setErrorMessage(err instanceof ApiError ? err.message : "Failed to run AI agent"))
      .finally(() => setIsRunningAgent(false));
  };

  if (pageStatus === "loading") return <LoadingState label="Loading transaction..." />;
  if (pageStatus === "error") return <ErrorState message={errorMessage} onRetry={load} />;
  if (!transaction) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <Link to="/transactions" className="text-xs font-medium text-slate-500 hover:text-slate-800">
            ← Back to transactions
          </Link>
          <h1 className="mt-1 text-xl font-semibold text-slate-900">Transaction #{transaction.id}</h1>
        </div>
        <StatusBadge status={transaction.status} />
      </div>

      <WorkflowStage icon="💳" title="Payment Failed" showConnector={pageStatus === "success"}>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <SummaryField label="Amount" value={formatCurrency(transaction.amount, transaction.currency)} />
          <SummaryField label="Order ID" value={transaction.razorpay_order_id} mono />
          <SummaryField label="Payment ID" value={transaction.razorpay_payment_id ?? "—"} mono />
          <SummaryField label="Failure Reason" value={transaction.failure_reason ?? "—"} />
        </div>
      </WorkflowStage>

      {pageStatus === "not_failed" && (
        <div
          className={`rounded-xl border p-5 text-sm ${
            transaction.status === "recovered"
              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
              : "border-slate-200 bg-slate-50 text-slate-600"
          }`}
        >
          {transaction.status === "recovered"
            ? "🎉 This transaction was successfully recovered."
            : "This transaction is not in a failed state, so diagnosis and recovery strategy don't apply."}
        </div>
      )}

      {pageStatus === "success" && diagnosis && decision && (
        <>
          <WorkflowStage icon="🔎" title="Diagnosis">
            <DiagnosisCard diagnosis={diagnosis} />
          </WorkflowStage>

          <WorkflowStage icon="🧠" title="Strategy Evaluation">
            <StrategySimulator decision={decision} />
          </WorkflowStage>

          <WorkflowStage icon="🛡" title="Safety Check">
            <SafetyCheckCard decision={decision} />
          </WorkflowStage>

          <WorkflowStage icon="⚡" title="Recovery Action" showConnector={!!executionResult}>
            <p className="text-sm text-slate-600">
              About to execute <span className="font-medium">{titleCase(decision.strategy)}</span>.
              {decision.requires_customer_action && " This requires customer action."}
              {decision.requires_human_review && " This requires human review."}
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <button
                onClick={handleExecute}
                disabled={isExecuting || isRunningAgent}
                className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
              >
                {isExecuting ? "Executing..." : "Execute Recovery"}
              </button>
              <button
                onClick={handleRunAgent}
                disabled={isExecuting || isRunningAgent}
                className="rounded-md border border-slate-900 px-4 py-2 text-sm font-medium text-slate-900 hover:bg-slate-100 disabled:opacity-50"
                title="Runs the same recovery through the LangGraph agent pipeline"
              >
                {isRunningAgent ? "Running AI Agent..." : "🤖 Run AI Agent"}
              </button>
            </div>
            <AgentProgressStages isRunning={isRunningAgent} />
          </WorkflowStage>

          {executionResult && (
            <WorkflowStage icon="✅" title={`Result${lastActionSource === "agent" ? " (via AI Agent)" : ""}`}>
              <ExecutionResultCard result={executionResult} />
            </WorkflowStage>
          )}
        </>
      )}

      <RecoveryTimeline attempts={attempts} />
    </div>
  );
}

function SummaryField({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className={`mt-1 text-sm font-medium text-slate-800 ${mono ? "font-mono text-xs" : ""}`}>{value}</p>
    </div>
  );
}
