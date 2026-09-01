export type TransactionStatus = "created" | "failed" | "captured" | "recovered";

export interface TransactionRead {
  id: number;
  merchant_id: number;
  razorpay_order_id: string;
  razorpay_payment_id: string | null;
  amount: number;
  currency: string;
  status: TransactionStatus;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface TransactionListResponse {
  total: number;
  limit: number;
  offset: number;
  items: TransactionRead[];
}

export interface DashboardSummary {
  total_transactions: number;
  total_failed: number;
  total_captured: number;
  total_recovered: number;
  revenue_at_risk: number;
  revenue_recovered: number;
}

export type DiagnosisCategory =
  | "insufficient_funds"
  | "bank_timeout"
  | "bank_unavailable"
  | "incorrect_otp"
  | "card_declined"
  | "payment_limit_exceeded"
  | "authentication_failure"
  | "technical_error"
  | "fraud_or_risk_flag"
  | "customer_abandoned"
  | "unknown";

export type RecommendedNextStep =
  | "retry_later"
  | "retry_alternate_route"
  | "request_customer_reauth"
  | "notify_customer_update_payment_method"
  | "notify_customer_reminder"
  | "do_not_retry_escalate"
  | "manual_review";

export interface DiagnosisResult {
  category: DiagnosisCategory;
  confidence: number;
  reason: string;
  recommended_next_step: RecommendedNextStep;
}

export type RecoveryStrategy =
  | "retry_same_route"
  | "retry_later"
  | "alternate_payment_method"
  | "payment_link"
  | "customer_reauthentication"
  | "customer_update_payment_method"
  | "reminder"
  | "escalate"
  | "no_action";

export type Urgency = "low" | "medium" | "high";

export interface CandidateStrategy {
  strategy: RecoveryStrategy;
  score: number;
  estimated_success_probability: number;
  reason: string;
}

export interface RecoveryDecision {
  strategy: RecoveryStrategy;
  confidence: number;
  reason: string;
  urgency: Urgency;
  estimated_success_probability: number;
  requires_customer_action: boolean;
  requires_human_review: boolean;
  next_step: string;
  candidate_strategies: CandidateStrategy[];
}

export type ExecutionStatus = "success" | "simulated" | "scheduled" | "blocked" | "failed";

export interface ExecutionResult {
  strategy: RecoveryStrategy;
  execution_status: ExecutionStatus;
  action_taken: string;
  message: string;
  recovery_attempt_id: number | null;
  payment_link_url: string | null;
  requires_customer_action: boolean;
  requires_human_review: boolean;
  evidence: Record<string, unknown> | null;
}

export type RecoveryAttemptStatus = "pending" | "success" | "failed";

export interface RecoveryAttemptRead {
  id: number;
  transaction_id: number;
  strategy: string | null;
  status: RecoveryAttemptStatus;
  created_at: string;
}

export type AnomalySeverity = "low" | "medium" | "high";

export interface Anomaly {
  anomaly_detected: boolean;
  severity: AnomalySeverity;
  pattern: string;
  message: string;
  affected_transaction_count: number;
  recommended_action: string;
}

export interface AnomalyReport {
  generated_at: string;
  anomalies: Anomaly[];
}

export interface StrategyPerformance {
  strategy: string;
  total_attempts: number;
  successful_attempts: number;
  success_rate: number;
}

export interface CategoryPerformance {
  category: string;
  total_failed: number;
  total_recovered: number;
  recovery_rate: number;
}

export interface RecoveryAnalytics {
  total_failed: number;
  total_recovered: number;
  recovery_rate: number;
  revenue_at_risk: number;
  revenue_recovered: number;
  total_recovery_attempts: number;
  average_attempts_per_recovered_transaction: number;
  most_successful_strategy: string | null;
  strategy_performance: StrategyPerformance[];
  category_performance: CategoryPerformance[];
}
