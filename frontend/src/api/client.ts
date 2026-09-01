import type {
  DashboardSummary,
  TransactionRead,
  TransactionListResponse,
  TransactionStatus,
  DiagnosisResult,
  RecoveryDecision,
  ExecutionResult,
  RecoveryAttemptRead,
  AnomalyReport,
  RecoveryAnalytics,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL as string;

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // No JSON body on this error response.
    }
    throw new ApiError(response.status, detail);
  }

  return response.json() as Promise<T>;
}

export function getDashboardSummary(): Promise<DashboardSummary> {
  return request<DashboardSummary>("/dashboard/summary");
}

export function getTransactions(
  params: { limit?: number; offset?: number; status?: TransactionStatus } = {}
): Promise<TransactionListResponse> {
  const search = new URLSearchParams();
  if (params.limit !== undefined) search.set("limit", String(params.limit));
  if (params.offset !== undefined) search.set("offset", String(params.offset));
  if (params.status) search.set("status", params.status);
  const query = search.toString();
  return request<TransactionListResponse>(`/transactions${query ? `?${query}` : ""}`);
}

export function getTransaction(id: number): Promise<TransactionRead> {
  return request<TransactionRead>(`/transactions/${id}`);
}

export function getDiagnosis(id: number): Promise<DiagnosisResult> {
  return request<DiagnosisResult>(`/transactions/${id}/diagnosis`);
}

export function getRecoveryStrategy(id: number): Promise<RecoveryDecision> {
  return request<RecoveryDecision>(`/transactions/${id}/recovery-strategy`);
}

export function executeRecovery(id: number): Promise<ExecutionResult> {
  return request<ExecutionResult>(`/transactions/${id}/recover`, { method: "POST" });
}

export function agentRecover(id: number): Promise<ExecutionResult> {
  return request<ExecutionResult>(`/transactions/${id}/agent-recover`, { method: "POST" });
}

export function getRecoveryAttempts(id: number): Promise<RecoveryAttemptRead[]> {
  return request<RecoveryAttemptRead[]>(`/transactions/${id}/recovery-attempts`);
}

export function seedTransactions(): Promise<{ merchants_seeded: number; transactions_seeded: number }> {
  return request(`/transactions/seed`, { method: "POST" });
}

export function getAnomalies(): Promise<AnomalyReport> {
  return request<AnomalyReport>("/analytics/anomalies");
}

export function getRecoveryAnalytics(): Promise<RecoveryAnalytics> {
  return request<RecoveryAnalytics>("/analytics/recovery");
}
