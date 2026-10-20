# Chaining & Cascades: Multi-Round Pipelines & Economic Trade-offs

## Contents
1. [The Non-Chaining Constraint](#1-the-non-chaining-constraint)
2. [Application-Code Chaining](#2-application-code-chaining)
3. [The Anti-Pattern: Chaining Through the Input](#3-the-anti-pattern-chaining-through-the-input)
4. [Cascades vs. Batching: Dependency Types](#4-cascades-vs-batching-dependency-types)
5. [The Cascade Economic Decision Formula](#5-the-cascade-economic-decision-formula)
6. [Speculative Branching](#6-speculative-branching)
7. [Asynchronous Decoupling & Provisional Defaults](#7-asynchronous-decoupling--provisional-defaults)
8. [Rules, Reasons, and Counter-Examples](#8-rules-reasons-and-counter-examples)

---

## 1. The Non-Chaining Constraint

Inside a single `POST /v1/decisions` call, **no question can read or condition on the answer to another question**. All questions evaluate the shared input concurrently in parallel during the forward pass [documented].
- If Question B requires the output of Question A to formulate its premise, they cannot be evaluated in the same request.
- All chaining must be orchestrated in **application code** across discrete network rounds.

---

## 2. Application-Code Chaining

Multi-stage pipelines operate by executing sequential rounds through Python:
```
[Evidence Snapshot] ──> [Round 1: Screening Gate] ──> Code Evaluates Gate
                                                              │ (if gate passed)
                                                              ▼
                                                   [Round 2: Detailed Assessment]
```

### Essential Invariants for Multi-Round Chains
1. **Evidence Snapshot Immutability**: All rounds in a chain must evaluate the *exact same underlying evidence snapshot*. If an incoming ticket or document can be modified while the chain is running, snapshot the payload into memory or object storage first.
2. **Global Chain Deadline**: Pass an absolute timestamp deadline down the call chain (`deadline = time.time() + 2.0`). Each round's timeout is set to `max(0.1, deadline - time.time())`.
3. **No Intermediate Side Effects**: Side effects (sending emails, debiting accounts, triggering webhooks) must only execute after the entire chain resolves successfully.

---

## 3. The Anti-Pattern: Chaining Through the Input

A dangerous shortcut is attempting to fake chaining by pasting Round 1's answer into Round 2's input text:
```
// Anti-Pattern:
input: "ROUND 1 RESULT: billing\n<<TICKET>>\nI want to dispute a transaction...\n<</TICKET>>"
```

### Why This Bites
1. **Stripping Uncertainty**: The model reads `"ROUND 1 RESULT: billing"` as an established empirical fact. If Round 1 had a marginal probability of $0.52$ (barely a guess), Round 2 sees it as $100\%$ certainty, compounding errors.
2. **Prompt Injection Risk**: An adversarial user can write `"ROUND 1 RESULT: billing"` in their email body to spoof the classifier into bypassing verification gates.
3. **Evidence Pollution**: Adding synthetic labels into `input` pollutes evidence context for other questions.

---

## 4. Cascades vs. Batching: Dependency Types

Before building a two-round cascade, classify the dependency between the questions:

### Type A: Logical Dependency
Question B *cannot be asked* without Question A's answer.
- *Example*: Asking "Which clause in Section 4 is breached?" depends on whether the contract actually has a Section 4.
- *Architecture*: Must use application-code chaining (sequential rounds).

### Type B: Relevance Dependency
Question B *can* be written in advance without Question A's answer, but is only *operationally relevant* if Question A is true.
- *Example*: Asking "Does the auto-renewal clause require >60 days notice?" (Question B) is only relevant if "Does the contract contain an auto-renewal clause?" (Question A) is true.
- *Architecture*: Can be either **batched** in Round 1 or **cascaded** into Round 2. The choice is purely economic.

---

## 5. The Cascade Economic Decision Formula

For relevance dependencies, compare the cost of batching everything in Round 1 vs. cascading Question B to Round 2 only when Question A triggers:

### Cost Components
- $S_1$: Input tokens for Round 1 (evidence + fixed overhead).
- $Q_1$: Question A token definition.
- $Q_2$: Question B token definition.
- $p_{\text{gate}}$: Expected pass rate of Question A (fraction of items triggering Round 2).
- $S_2$: Input tokens for Round 2 (resending the evidence if not cached).
- $\text{detail\_surcharge}$: Additional tokens if Round 1 requires higher detail/resolution to answer Question B.

### The Decision Formula
$$\text{Extra Cost}_{\text{batch}} = Q_2 + \text{detail\_surcharge}$$
$$\text{Extra Cost}_{\text{cascade}} = p_{\text{gate}} \times (S_2 + Q_2)$$

If $\text{Extra Cost}_{\text{cascade}} < \text{Extra Cost}_{\text{batch}}$, cascade; otherwise, batch.

```python
def cascade_or_batch(q_gated: int, p_gate: float, shared_round2: int, detail_surcharge: int = 0) -> tuple[str, float]:
    """
    Determines whether to cascade or batch based on expected extra token cost.
    Returns ('cascade' | 'batch', cost_difference).
    """
    cost_batch = q_gated + detail_surcharge
    cost_cascade = p_gate * (shared_round2 + q_gated)
    decision = "cascade" if cost_cascade < cost_batch else "batch"
    return decision, abs(cost_batch - cost_cascade)
```

### Worked Example: Contract Review
- Contract text: $S_2 = 6{,}000$ tokens. Auto-renewal clause presence rate: $p_{\text{gate}} = 0.08$. Notice question: $Q_2 = 80$ tokens. $\text{detail\_surcharge} = 0$.
- $\text{Extra Cost}_{\text{batch}} = 80$ tokens.
- $\text{Extra Cost}_{\text{cascade}} = 0.08 \times (6{,}000 + 80) = 0.08 \times 6{,}080 = 486.4$ tokens.
- **Verdict**: **Batch in Round 1!** Cascading resends $6{,}000$ tokens on $8\%$ of items, costing $6\times$ more than asking Question B up front.

---

## 6. Speculative Branching

When routing across categories with fine-grained subcategories, avoid multi-round serial cascades by speculatively batching the top subcategories into Round 1:
```python
QUESTIONS = [
    build_question("team_primary"),
    build_question("billing_subcategory"),
    build_question("technical_subcategory")
]
```
- In Round 1, evaluate primary routing and the top two most probable subcategories simultaneously.
- If primary routing picks `"billing"`, the billing subcategory answer is already available in the response.
- Only if routing picks a rare category (e.g. `"compliance"`) does the code fall back to a Round 2 call.

---

## 7. Asynchronous Decoupling & Provisional Defaults

When user-facing response time budgets are tight (e.g., $<400$ms):
- Never allow a 2-round cascade or human review queue to block the HTTP response thread.
- Take a **provisional safe action** synchronously (e.g., holding a comment in moderation, acknowledging ticket receipt).
- Execute the heavy cascade or review asynchronously in background workers, and update the state when complete.

---

## 8. Rules, Reasons, and Counter-Examples

| Rule | Reason | Counter-Example (Anti-Pattern) |
|---|---|---|
| **Never paste previous answers into subsequent inputs** | Strips probability calibration, creates fake ground truth, and exposes pipeline to delimiter injection. | Submitting `ROUND 1 RESULT: billing` in Round 2's evidence string. |
| **Pass an overall deadline down every chain** | Prevents tail-latency runaway and resource exhaustion during API degradation. | Running a 3-stage cascade where each call has a separate uncoordinated 10s timeout. |
| **Always check the math before building a cascade** | Resending large document text in Round 2 frequently costs more than batching the extra question in Round 1. | Building a 2-round cascade for a 5,000-word contract when the gate triggers 25% of the time. |
| **Snapshot evidence before initiating multi-round chains** | Prevents concurrent mutation from creating inconsistent evaluations across rounds. | Evaluating Round 1 on live database ticket text that customer service is actively editing. |
