# PayRescue AI

**Agentic Payment Recovery & Optimization Platform** — built for the Razorpay AI Buildathon, "AI Growth & Agentic Commerce" theme.

## 1. Project Overview
PayRescue AI turns failed payments from a dead end into an autonomous recovery pipeline: detect the failure, understand why it happened, decide the best recovery strategy, act on it, and track the outcome — instead of just asking the customer to "please retry."
<img width="2876" height="1582" alt="Screenshot 2026-09-01 083542" src="https://github.com/user-attachments/assets/cf6d898d-3308-439c-8b95-bae81c931a63" />

## 2. Problem Statement
When a payment fails, merchants typically show a generic error and hope the customer retries. This silently costs real revenue, especially for failures that are recoverable (transient bank timeouts, wrong OTP, a declined card that would work via a different route).

## 3. Solution
An agentic pipeline — **Detect → Diagnose → Decide → Recover → Verify → Escalate → Measure** — that inspects each failed payment's real Razorpay webhook data, classifies the failure, evaluates multiple recovery strategies with explainable scoring (including a lightweight learning loop from historical outcomes), executes the safest viable action, and surfaces everything on a merchant dashboard.
<img width="2640" height="1332" alt="Screenshot 2026-09-01 083806" src="https://github.com/user-attachments/assets/63d65bb9-a662-4cb1-a5da-271fcf769da9" />

## 4. Agentic Workflow
```
Payment Fails (Razorpay webhook)
      |
Diagnosis (rule-based classifier -> 11 categories)
      |
Recovery Strategy Decision (candidate generation -> scoring -> selection)
      |
Safety Check (fraud / high-value / repeated-failure guardrails)
      |
Execution (real payment link / escalation / simulated actions)
      |
Recorded as a RecoveryAttempt -> closes the loop back to "recovered"
```
Available two ways: direct service calls (`POST /transactions/{id}/recover`) or orchestrated through a LangGraph state graph (`POST /transactions/{id}/agent-recover`) — both produce identical results.

## 5. Architecture
- **Backend**: FastAPI + SQLModel + PostgreSQL, organized into `models/`, `schemas/`, `services/`, `api/`, and `agents/` (LangGraph orchestration).
- **Frontend**: React + Vite + TypeScript + Tailwind CSS + Recharts, consuming the backend via a centralized API client — no business logic duplicated client-side.
- **Data flow**: Razorpay webhook -> `transactions` table -> diagnosis (computed on demand) -> strategy decision (informed by `recovery_attempts` history) -> execution -> new `recovery_attempts` row -> a successful payment-link payment closes the loop back to the original transaction.

## 6. Tech Stack
Python, FastAPI, SQLModel, PostgreSQL, Alembic, LangGraph, Razorpay Python SDK, React, Vite, TypeScript, Tailwind CSS, Recharts, pytest.

## 7. Razorpay Integration
- **Real**: order/payment lifecycle via test-mode webhooks (`payment.failed`, `payment.captured`, `order.paid`, `payment_link.paid`) with HMAC signature verification; real Payment Link generation via the Razorpay SDK.
- **Simulated**: alternate payment route selection, customer notifications (reminder/reauthentication/update-payment-method), automatic retry charging (intent only — never charges).
<img width="2848" height="1438" alt="Screenshot 2026-09-01 091310" src="https://github.com/user-attachments/assets/39bbaf4e-a399-4152-a795-266de59abf16" />

## 8. What Is Real vs Simulated
| Component | Status |
|---|---|
| Webhook ingestion & signature verification | Real |
| Failure diagnosis | Real (rule-based, deterministic) |
| Recovery strategy scoring | Real (deterministic engine + real historical data) |
| Payment Link generation | Real (Razorpay API) |
| Closed-loop recovery tracking | Real (payment-link payments mark the original transaction `recovered`) |
| Escalation + evidence payload | Real |
| Reminder / update-payment-method / reauthentication | Simulated (no real channel wired up) |
| Alternate payment route | Simulated (no such Razorpay API exists) |
| Automatic retry charging | Not implemented — intent only, never charges |
| Anomaly detection | Real (statistics over live DB data) |
| Recovery analytics | Real (computed from live DB data) |
| Learning loop | Real (computed from live `recovery_attempts`, no persisted model) |
| LangGraph orchestration | Real (wraps the same real services as nodes) |

## 9. LangGraph's Role
Pure **orchestration layer** over independently-usable service functions (`diagnose_transaction`, `decide_recovery_strategy`, `execute_recovery`). Every node is a thin wrapper — no business logic lives in the graph itself.

## 10. Key Features
- Real webhook-driven failure detection with idempotent, closed-loop transaction updates
- 11-category rule-based diagnosis with layered fallback logic
- Explainable recovery strategy engine with a visible candidate comparison ("Recovery Strategy Simulator")
- Safety guarantees: fraud/risk never auto-retries; high-value and repeated-failure cases favor human review
- Real Razorpay Payment Link generation with closed-loop tracking back to the original transaction
- Rule-based anomaly detection (spikes, category concentration, time bursts, repeated failures)
- Recovery analytics (per-strategy, per-category, revenue impact)
- Lightweight, non-ML learning loop from historical outcomes
- LangGraph-orchestrated alternative execution path
- Full merchant dashboard with charts, system intelligence panel, and a guided per-transaction agent workflow view

## 11. Demo Flow (2-3 minutes)
1. Open Dashboard — show Revenue at Risk and Recovery Rate
2. Show a recent failed transaction
3. Open it — walk down Payment Failed -> Diagnosis -> Strategy Evaluation -> Safety Check
4. Click "Run AI Agent" — watch the LangGraph progress stages
5. Show the real Execution Result (payment link / escalation evidence)
6. Show Recovery History
7. Return to Dashboard — show updated Recovery Analytics and charts

## 12. Setup Instructions
```bash
# Backend
cd backend
docker run --name payrescue-postgres -e POSTGRES_USER=payrescue -e POSTGRES_PASSWORD=payrescue_pass -e POSTGRES_DB=payrescue_db -p 5432:5432 -d postgres:16
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # fill in real Razorpay TEST-mode keys
alembic revision --autogenerate -m "create initial tables"
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
copy .env.example .env
npm run dev
```

## 13. Testing Instructions
```bash
cd backend
pytest tests/ -v
```
Covers diagnosis, recovery strategy scoring (including safety rules), execution, closed-loop recovery tracking, anomaly detection, recovery analytics, the learning loop, and the full LangGraph pipeline.
Frontend: `npm run build` for a type-check, manual walkthrough of the demo flow above.

## 14. Future Improvements
- Real WhatsApp/SMS/email integration for customer-action strategies
- A safe, rate-limited automatic retry execution mechanism
- Specialist sub-agents per recovery channel (LangGraph nodes are already structured for this)
- Persisted learning signals instead of recomputing from raw attempts each time
- Multi-merchant support keyed on Razorpay `account_id`
