# Communication Templates: Intake, Ledgers, Plans, Reports & Tests

## Contents
1. [Stakeholder Intake Checklist](#1-stakeholder-intake-checklist)
2. [Batch Question Proposal Template](#2-batch-question-proposal-template)
3. [Numbered Assumption Ledger Template](#3-numbered-assumption-ledger-template)
4. [Checkpoint Plan Template](#4-checkpoint-plan-template)
5. [Checkpoint Report Template (One-Page)](#5-checkpoint-report-template-one-page)
6. [ROI-Scored Test Selection Template](#6-roi-scored-test-selection-template)
7. [Rules, Reasons, and Counter-Examples](#7-rules-reasons-and-counter-examples)

---

## 1. Stakeholder Intake Checklist
Use this structured intake checklist before beginning pipeline architecture or prompt design:

```markdown
### Decisions API Pipeline Intake
1. **Inputs**:
   - Shape & format: [e.g. plain text customer email / image attachment / scanned PDF]
   - Expected volume: [e.g. 50,000 calls / month]
   - Trust level: [e.g. untrusted public internet users / authenticated employees]
   - Sensitive data: [e.g. customer PII present; requires SHA-256 ID hashing]
2. **Outputs & Downstream Actions**:
   - Primary consumer: [e.g. automated routing engine, Zendesk queue, fraud database]
   - Automated actions triggered: [e.g. direct dispatch, account suspension, refund credit]
3. **Operational Constraints**:
   - Latency SLA: [e.g. p50 < 300ms, p99 < 800ms]
   - Cost budget: [e.g. < $0.001 per evaluated ticket]
   - Human review capacity: [e.g. max 15% of total volume routed to manual review]
4. **Error Costs**:
   - Cost of False Positive ($C_{FP}$): [e.g. $150 customer churn risk if wrongly banned]
   - Cost of False Negative ($C_{FN}$): [e.g. $25 chargeback fee if fraudulent return accepted]
   - Cost of Human Review ($C_R$): [e.g. $2.50 per ticket for manual triage]
5. **Existing Labeled Assets**:
   - Available historical data: [e.g. 2,000 human-tagged support tickets from Q3]
```

---

## 2. Batch Question Proposal Template
Present all design queries in structured batches with explicit defaults:

```markdown
### Proposed Clarifications & Defaults (Batch #1)

1. **Question Phrasing**: For detecting urgent infrastructure outages, we propose:
   - *Proposed Text*: `"Does the customer report that our SaaS platform is completely unreachable or unusable for their entire team right now?"`
   - *Options*: `predicate`
   - **Recommended Default**: **Approve proposed phrasing**. (One-word confirmation: `1: approve`).

2. **Refusal Handling on Paging Gate**: If the model declines to evaluate `outage`:
   - *Options*: (A) Fail open (page on-call); (B) Route to human support queue; (C) Fail closed (silence alert).
   - **Recommended Default**: **(B) Route to human support queue**.

3. **Human Review Band Limit**:
   - *Proposed Cap*: Maximum 15% of total tickets routed to manual review.
   - **Recommended Default**: **Confirm 15% cap**.
```

---

## 3. Numbered Assumption Ledger Template
Maintain an updated ledger in every technical artifact:

```markdown
### Assumption Ledger
1. *[confirmed by stakeholder]*: Monthly volume is estimated at 100,000 tickets, with peak burst of 25 RPS.
2. *[confirmed by stakeholder]*: Cost of False Positive ($C_{FP}$) is $50.00; Cost of False Negative ($C_{FN}$) is $10.00; Review Cost ($C_R$) is $2.00.
3. *[verified by test]*: Image token estimator yields 308 tokens for all $512\times 512$ thumbnail crops under `low` detail.
4. *[assumed]*: Upstream API model `gpt-6-luna` maintains stable ranking over the next 30 days.
5. *[assumed]*: Incoming PDFs will be pre-rasterized to PNG by the existing ingestion service before reaching the pipeline.
```

---

## 4. Checkpoint Plan Template

```markdown
### Checkpoint Plan: [Intake / Design / First Draft / Test Selection / Handoff]
- **Goal**: [Clear statement of target deliverable]
- **Proposed Architecture**: [What we will build and why]
- **Alternatives Considered**: [Other options explored and why discarded]
- **Assumptions**: [Reference entries in Assumption Ledger]
- **Open Questions**: [Reference Batch Question Proposal]
- **Estimated Cost & Time**: [API test budget and execution timeline]
```

---

## 5. Checkpoint Report Template (One-Page)

```markdown
### Checkpoint Report: [Checkpoint Name]
- **Primary Outcome**: [Summary of what was achieved and delivered]
- **Empirical Evidence**:
  - Sample size: $N = 500$ dev items, $N = 300$ test items.
  - AUROC achieved: $0.942$ on primary routing choice.
  - Optimal cutoffs: $lo = 0.38, hi = 0.88$; empirical review share: $11.4\%$.
  - Certified error bound: True error in automated zone $\le 1.8\%$ (95% confidence).
- **Changes from Plan**: [Any architectural deviations from original proposal]
- **Autonomous Decisions**:
  - Decision: Set `detail="original"` for cropped signature evaluations.
  - Rationale: Cropped signature size is $300\times 120$ (< $512\times 512$); native patches cost fewer tokens.
  - How to reverse: Change parameter in `QuestionDef` to `detail="low"`.
- **Deferred Decisions**:
  - Item: Third-tier escalation reasoning model selection (`gpt-6-sol`).
  - Resolving event: Waiting on live escalation cost audit in Stage 5.
  - Safe default meanwhile: Route ambiguous cases directly to human queue.
- **Next Step**: [Immediate subsequent action]
```

---

## 6. ROI-Scored Test Selection Template

```markdown
### Scored Candidate Tests for ROI Prioritization

$$\text{ROI Score} = \frac{P(\text{defect exists}) \times \text{Cost}(\text{defect ships})}{\text{Cost to run (money, time, stakeholder effort)}}$$

| # | Candidate Test | Target Failure Mode | $P(\text{defect})$ | Cost if Ships | Cost to Run | ROI Score | Recommended |
|---|---|---|---|---|---|---|---|
| 1 | Contract parser tolerance test | Two-decimal rounding sum violations | 0.80 | $5,000 | $0.05 (offline) | **80,000** | **Run immediately** |
| 2 | Refusal fallback unit tests | Unhandled refusals crashing pipeline | 0.60 | $10,000 | $0.05 (offline) | **120,000** | **Run immediately** |
| 3 | Probe replay baseline test | Silent upstream model output drift | 0.40 | $2,000 | $0.10 (live API) | **8,000** | **Run (cost-capped)** |
| 4 | Batch interference sweep | Question criteria bleed | 0.20 | $500 | $1.50 (live API) | **66** | Optional |
```

---

## 7. Rules, Reasons, and Counter-Examples

| Rule | Reason | Counter-Example (Anti-Pattern) |
|---|---|---|
| **Always provide recommended defaults with every batch question** | Minimizes stakeholder turnaround time; allows rapid one-word approvals. | Asking an open-ended question: "How would you like to handle refusals across your 7 questions?" |
| **Quote exact text and thresholds in all communication** | Eliminates ambiguity; prevents misunderstanding of historical context. | Writing "We will use the same threshold as the previous email." |
| **Tag every assumption explicitly (*assumed*, *confirmed*, *verified*)** | Prevents unverified assumptions from silently hardening into production architecture. | Building an entire pipeline assuming 1-second SLAs without confirming with infrastructure teams. |
