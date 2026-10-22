# PayRescue AI: Agentic Payment Recovery

**A failed payment is a lost customer, unless you know *why* it failed.**
PayRescue turns failed payments from a dead end into a recovery pipeline: it diagnoses each failure, picks the safest way to win the payment back, and tracks the result, instead of just asking the customer to "please retry."

🏆 Built for the **Razorpay AI Buildathon**, *"AI Growth & Agentic Commerce"* theme.

<img width="2876" height="1582" alt="PayRescue merchant dashboard" src="https://github.com/user-attachments/assets/cf6d898d-3308-439c-8b95-bae81c931a63" />

**At a glance:** 11 failure categories · 9 recovery strategies · 6-node LangGraph agent · 13 REST endpoints · 58 automated tests

---

## 🧭 Understanding the Problem

### 1️⃣ Context

| | |
|---|---|
| **About the company** | Built for **Razorpay**, one of India's leading payment gateways, as part of the Razorpay AI Buildathon (*AI Growth & Agentic Commerce* theme). |
| **About the industry** | Online payments: every failed transaction at checkout is a sale the merchant may never get back. |
| **Stakeholders** | **Merchants** (lose revenue), their **operations teams** (handle failures), **customers** (frustrated at checkout) and the **payment gateway** (merchant success = gateway success). |
| **Research** | Studied the failure reasons Razorpay returns in its webhooks (`payment.failed` and others) and grouped them into **11 failure categories**, from `bank_timeout` and `incorrect_otp` to `fraud_or_risk_flag`. |

### 2️⃣ Diagnosis

| | |
|---|---|
| **Pain points** | When a payment fails, most checkouts show a generic error and hope the customer retries. Recoverable failures (a bank timeout, a wrong OTP, a declined card that would work another way) silently become lost revenue. |
| **Key takeaways** | Different failures need different responses: retrying *insufficient funds* is useless, retrying a *bank timeout* often works, and a *fraud flag* must **never** be retried. |
| **Competitor analysis** | The common approach is a one-size-fits-all "please retry" message or blind automatic retries. Neither explains *why* a payment failed or chooses a different action for different failures. PayRescue's edge is **diagnosis first, explainable action second**. |
| **Trade-off** | Recover revenue fast vs. stay safe. PayRescue deliberately chooses **safety first**: risky and high-value cases go to a human, even if that recovers less automatically. |

### 3️⃣ Strategy

| | |
|---|---|
| **User persona** | **Priya, a merchant operations manager** *(illustrative persona)*. She handles failed payments every day and needs to know *what failed, why, and what to do next*, without reading logs. |
| **Key decisions** | Rule-based, explainable decisions over a black-box model (every action can be justified to a merchant), and real Razorpay payment links over simulated recovery wherever an API exists. |
| **Solution** | A pipeline that runs **Detect → Diagnose → Decide → Recover → Verify → Escalate → Measure** for every failed payment, choosing among **9 recovery strategies** with visible scores on a merchant dashboard. |
| **Implementation** | FastAPI + PostgreSQL services, an optional **6-node LangGraph** agent, a React dashboard, and **58 automated tests**. Details in the engineering section below. |

### 4️⃣ Impact

| | |
|---|---|
| **Business impact** | Turns a dead-end error into a recovery path. A paid recovery link closes the loop on the original order, and the dashboard tracks **Revenue at Risk** and **Recovery Rate**. |
| **Financial impact** | Recovery analytics report recovered revenue **by strategy and by failure category**, so a merchant can see which actions actually earn money back. *(Built on Razorpay test-mode data, so no live revenue figures are claimed.)* |
| **Risk & mitigation** | Fraud or risk flags **never** auto-retry · high-value and repeated failures go to **human review** · **HMAC signature checks** and **idempotent updates** stop a duplicate webhook from ever processing a payment twice · automatic charging is intentionally **not** implemented. |
| **Annexures** | [What is Real vs Simulated](#-what-is-real-vs-simulated) · [How it works](#%EF%B8%8F-how-it-works) · [Tests](#-tests) · [Demo flow](#-demo-flow-23-minutes) |

### 🗺️ What's Next
- Real WhatsApp, SMS and email channels for customer-action strategies
- A safe, rate-limited automatic retry mechanism
- Specialist sub-agents per recovery channel
- Multi-merchant support keyed on Razorpay `account_id`

---

## ⚙️ How It Works

```
Payment fails (Razorpay webhook, HMAC-verified)
      │
Diagnosis ─ rule-based classifier with layered fallback → 11 categories
      │
Strategy ─ candidate generation → explainable scoring → selection (9 strategies)
      │
Safety check ─ fraud / high-value / repeated-failure guardrails
      │
Execution ─ real Razorpay payment link / escalation with evidence
      │
Recorded as a RecoveryAttempt → a paid link marks the original transaction "recovered"
```

The pipeline runs two ways with identical results: direct service calls (`POST /transactions/{id}/recover`) or a **6-node LangGraph** agent (`POST /transactions/{id}/agent-recover`). LangGraph is a thin orchestration layer; all business logic stays in independently testable services.

<img width="2640" height="1332" alt="Recovery strategy evaluation" src="https://github.com/user-attachments/assets/63d65bb9-a662-4cb1-a5da-271fcf769da9" />

## ✨ Key Features

- Webhook-driven failure detection with **idempotent, closed-loop** transaction updates
- **11-category** diagnosis with layered fallback logic
- Explainable strategy engine with a visible candidate comparison (**Recovery Strategy Simulator**)
- Real **Razorpay Payment Link** generation, tracked back to the original transaction
- Rule-based **anomaly detection**: spikes, category concentration, time bursts, repeated failures
- **Recovery analytics** per strategy, per category and by revenue impact
- A lightweight learning loop that improves strategy scores from historical outcomes
- Merchant dashboard with charts, a system intelligence panel and a step-by-step agent view

<img width="2848" height="1438" alt="Agent workflow and execution result" src="https://github.com/user-attachments/assets/39bbaf4e-a399-4152-a795-266de59abf16" />

## ✅ What Is Real vs Simulated

| Component | Status |
|---|---|
| Webhook ingestion & HMAC signature verification | Real |
| Failure diagnosis | Real (rule-based, deterministic) |
| Recovery strategy scoring | Real (deterministic engine + historical data) |
| Payment Link generation | Real (Razorpay API, test mode) |
| Closed-loop recovery tracking | Real |
| Escalation with evidence payload | Real |
| Anomaly detection & recovery analytics | Real (computed from live database data) |
| Learning loop | Real (computed from recovery history, no persisted model) |
| LangGraph orchestration | Real (wraps the same services as nodes) |
| Reminder / re-authentication / update-payment-method | Simulated (no messaging channel connected) |
| Alternate payment route | Simulated (no such Razorpay API exists) |
| Automatic retry charging | Not implemented (intent only, never charges) |

## 🏗️ Architecture

- **Backend:** FastAPI + SQLModel + PostgreSQL, organised into `models/`, `schemas/`, `services/`, `api/` and `agents/` (LangGraph).
- **Frontend:** React + Vite + TypeScript + Tailwind CSS + Recharts, using a single API client with no business logic duplicated on the client.
- **Data flow:** Razorpay webhook → `transactions` → diagnosis → strategy (informed by `recovery_attempts` history) → execution → new `recovery_attempts` row → a paid payment link closes the loop.

## 🧰 Tech Stack

Python · FastAPI · SQLModel · PostgreSQL · Alembic · LangGraph · Razorpay Python SDK · React · Vite · TypeScript · Tailwind CSS · Recharts · pytest

## ▶️ How to Run

```bash
# Backend
cd backend
docker run --name payrescue-postgres -e POSTGRES_USER=payrescue -e POSTGRES_PASSWORD=payrescue_pass -e POSTGRES_DB=payrescue_db -p 5432:5432 -d postgres:16
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env  — add Razorpay TEST-mode keys
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
cp .env.example .env        # Windows: copy .env.example .env
npm run dev
```

## 🧪 Tests

```bash
cd backend
pytest tests/ -v
```

**58 tests** cover diagnosis, strategy scoring (including safety rules), execution, closed-loop recovery tracking, anomaly detection, recovery analytics, the learning loop and the full LangGraph pipeline. Frontend: `npm run build` for type-checking.

## 🎬 Demo Flow (2–3 minutes)

1. Open the dashboard and look at **Revenue at Risk** and **Recovery Rate**
2. Open a recent failed transaction
3. Walk through **Payment Failed → Diagnosis → Strategy Evaluation → Safety Check**
4. Click **Run AI Agent** and watch the LangGraph stages
5. See the real execution result (payment link or escalation evidence)
6. Return to the dashboard to see updated recovery analytics
