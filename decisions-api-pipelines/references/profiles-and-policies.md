# Profiles & Policies: Composite Signals & Deterministic Logic

## Contents
1. [What a Composite Profile Is](#1-what-a-composite-profile-is)
2. [The Profile Pattern: Shared Perception](#2-the-profile-pattern-shared-perception)
3. [Policy as Code](#3-policy-as-code)
4. [Handling Missing and Refused Profile Fields](#4-handling-missing-and-refused-profile-fields)
5. [Worked Example: Support Triage Profile](#5-worked-example-support-triage-profile)
6. [Cross-Check Consistency Rules](#6-cross-check-consistency-rules)
7. [Rules, Reasons, and Counter-Examples](#7-rules-reasons-and-counter-examples)

---

## 1. What a Composite Profile Is
A **composite profile** evaluates multiple orthogonal dimensions of a single entity (customer ticket, product review, loan application) in a single batched Decisions API request.
Instead of each downstream service calling the API independently with bespoke questions, a single request builds a comprehensive perception record that all downstream policies consume.

---

## 2. The Profile Pattern: Shared Perception
- **Billed Once**: The evidence context (customer history, ticket body, attachments) is prefilled and billed only once.
- **Consistent Ground Truth**: All consuming systems (routing, SLA prioritization, on-call paging, fraud screening) evaluate their policies against the exact same timestamped perception snapshot.
- **Decoupled Policies**: Policies change frequently (e.g. holiday SLA adjustments); perception changes rarely. Separating them means policy updates never require re-prompting or API model re-evaluations.

---

## 3. Policy as Code
All business rules are implemented in deterministic, versioned Python functions. The policy receives:
1. The parsed profile answers (probabilities, choices, scores).
2. Business state from internal databases (customer tier, SLA entitlement, order history, prior strike count).

```python
def evaluate_triage_policy(profile: dict, customer: Customer) -> str:
    # Deterministic rule 1: Outage paging for enterprise customers only
    if profile["outage"].probability >= 0.85 and customer.tier == "enterprise":
        return "page_oncall_lead"
    
    # Deterministic rule 2: High impact + enterprise -> P1 priority
    if profile["impact"].score >= 3.0 and customer.tier == "enterprise":
        return "queue_p1_urgent"
        
    return "queue_standard"
```

---

## 4. Handling Missing and Refused Profile Fields
In production, individual questions within a profile may be refused by safety filters, or fields may be omitted during partial degradation.
- **Never Coerce Refusals to False**: An unanswered question must never default to `probability = 0.0` or `level = 0`.
- **Declare Required Fields per Policy**:
  Each policy function declares its mandatory prerequisites. If a required field is missing or refused, the policy immediately falls back to its declared fallback path:
  ```python
  POLICY_REQUIREMENTS = {
      "sla_priority": ["impact", "scope"],
      "routing": ["team"],
      "paging": ["outage"]
  }
  ```
- **Fallback Execution**: If `outage` is refused, the paging policy cannot evaluate; it routes the item to a human on-call triage queue rather than assuming no outage.

---

## 5. Worked Example: Support Triage Profile

The canonical support triage profile gathers 7 orthogonal signals in one call:

| Question | Primitive | Purpose | Consumed By |
|---|---|---|---|
| `team` (v4) | `choice` (3 teams + 2 escapes) | Determine operational owner | Router |
| `outage` (v3) | `predicate` | System completely unusable right now | Paging system |
| `impact` (v3) | `score` (5 levels: None $\to$ Blocked) | Degree of task obstruction | SLA Priority engine |
| `scope` (v2) | `score` (3 levels: One $\to$ Organization) | Number of affected users | SLA Priority engine |
| `frustrated` (v2) | `predicate` | Hostile language, threats to cancel | Account Management |
| `refund_requested` (v1) | `predicate` | Customer expresses desire for money back | Billing triage (intent only) |
| `mentions_delivery` (v1) | `predicate` | Mentions packages, carriers, tracking | Cross-check validator |

---

## 6. Cross-Check Consistency Rules
Application code enforces sanity checks across questions to detect contradictory model judgments:
- **Contradiction A**: If `team == "shipping"` but `mentions_delivery.probability < 0.10`, the route is suspicious.
- **Contradiction B**: If `outage.probability >= 0.85` but `impact.score <= 1.0` (Cosmetic), the judgments conflict.
- **Resolution**: Route contradictory profiles directly to human review (`status = "review_conflict"`). Never allow contradictory automated actions to fire.

---

## 7. Rules, Reasons, and Counter-Examples

| Rule | Reason | Counter-Example (Anti-Pattern) |
|---|---|---|
| **Never authorize financial actions directly from intent predicates** | Expressed customer intent (`wants_refund`) is not contractual entitlement; code must verify ledger dates. | Automatically issuing a $100 credit because `refund_requested.probability > 0.90`. |
| **Always declare fallback paths for refused profile fields** | Coercing a refused question to false creates silent failures in safety and security pipelines. | Assuming a refused `contains_exploit` predicate means the code is safe to execute. |
| **Centralize customer tier and SLA data in code** | The database holds ground-truth contract status; asking the model hallucinates user tiers. | Asking the Decisions API: "Is this user entitled to a 15-minute response SLA?" |
