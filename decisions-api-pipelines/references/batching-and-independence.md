# Batching & Question Independence: Multi-Question Requests & Amortization

## Contents
1. [Single-Context Parallel Evaluation Overview](#1-single-context-parallel-evaluation-overview)
2. [Cost Amortization Mathematics](#2-cost-amortization-mathematics)
3. [The Amortization Ceiling](#3-the-amortization-ceiling)
4. [Question Interference & Independence Testing](#4-question-interference--independence-testing)
5. [Batch Size Limits & Wire Realities](#5-batch-size-limits--wire-realities)
6. [The Centralized Question Registry Pattern](#6-the-centralized-question-registry-pattern)
7. [Rules, Reasons, and Counter-Examples](#7-rules-reasons-and-counter-examples)

---

## 1. Single-Context Parallel Evaluation Overview
The Decisions API evaluates up to 200 questions against a single shared `input` payload in a single forward pass [community report]. This capability unlocks massive economic and latency advantages:
- The input tokens (evidence, documents, images) are prefilled and billed **once**.
- All question answers are returned in parallel in a single round-trip (~255ms).
- Eliminates the need for multiple serial network calls to gather orthogonal signals about the same entity.

---

## 2. Cost Amortization Mathematics

Every request incurs a token cost structured as:
$$\text{Tokens}_{\text{total}} = \text{Overhead}_{\text{fixed}} + \text{Tokens}_{\text{input}} + \sum_{j=1}^{K} \text{Tokens}_{\text{question}_j}$$

- $\text{Overhead}_{\text{fixed}}$: Fixed API scaffolding (~137 to 145 tokens on minimal text) [community report].
- $\text{Tokens}_{\text{input}}$: Billed length of the shared evidence (text + image patches).
- $\text{Tokens}_{\text{question}_j}$: Instruction text, plus choice/score definitions for question $j$ (typically 40–120 tokens).

### Economic Comparison: Batched vs. Separate
Consider an input of 3,000 tokens (e.g., a product review with an image) evaluated against $K=6$ questions averaging 60 tokens each, with a fixed overhead of 100 tokens:
- **6 Separate Requests**:
  $$\text{Tokens} = 6 \times (100 + 3{,}000 + 60) = 6 \times 3{,}160 = 18{,}960 \text{ tokens}$$
- **1 Batched Request**:
  $$\text{Tokens} = 100 + 3{,}000 + (6 \times 60) = 3{,}460 \text{ tokens}$$

**Savings**: $18{,}960 \to 3{,}460$ tokens ($5.48\times$ reduction in cost). At 1,000,000 requests/month at $\$0.10/\text{1M}$, monthly spend drops from $\$1{,}896$ to $\$346$.

---

## 3. The Amortization Ceiling

The maximum possible theoretical cost reduction from batching has an upper limit determined by the ratio of shared context to per-question overhead:

$$\text{Ratio}(K) = \frac{K \cdot (S + Q)}{S + K \cdot Q}$$

where $S = \text{Overhead}_{\text{fixed}} + \text{Tokens}_{\text{input}}$ and $Q$ is average question definition tokens.

As $K \to \infty$, the maximum savings ratio approaches:
$$\lim_{K \to \infty} \text{Ratio}(K) = 1 + \frac{S}{Q}$$

- When input is very small ($S \approx 150$, $Q \approx 50$), the maximum possible savings ratio is $1 + 150/50 = 4\times$.
- When input is large (e.g. 5-page PDF text, $S \approx 5{,}000$, $Q \approx 50$), the maximum savings ratio is $1 + 5{,}000/50 = 101\times$.

---

## 4. Question Interference & Independence Testing

While batching is economically compelling, adding questions to a request can introduce **attention interference** or criteria bleed, slightly shifting probability distributions.

### The Interference Testing Protocol
Before deploying a new batched request to production, execute `interference_test(items, target, others)`:

```python
def interference_test(items: list, target_q: dict, other_qs: list[dict], max_shift_tol: float = 0.05):
    """
    Evaluates target_q in isolation vs. target_q batched alongside other_qs.
    Verifies that max probability shift is <= max_shift_tol across all items.
    """
    shifts = []
    for item in items:
        p_alone = client.decisions.create(input=item, questions=[target_q]).answers[0].probability
        p_batched = client.decisions.create(input=item, questions=[target_q] + other_qs).answers[0].probability
        shifts.append(abs(p_alone - p_batched))
    
    max_shift = max(shifts)
    share_shifted = sum(s > 0.02 for s in shifts) / len(shifts)
    assert max_shift <= max_shift_tol, f"Interference detected: max shift {max_shift:.3f} > {max_shift_tol}"
    return {"max_shift": max_shift, "share_shifted": share_shifted}
```

If interference exceeds tolerance, group questions into separate orthogonal requests or simplify instructions.

---

## 5. Batch Size Limits & Wire Realities
- **Maximum Questions per Request**: 200 questions [community report].
- **Maximum Options per Choice**: 255 options [community report].
- **Practical Sweet Spot**: In real-world production systems (support triage, review moderation), requests typically batch **4 to 12 questions**. Batching beyond 25–30 questions increases latency variance and risk of partial refusal.

---

## 6. The Centralized Question Registry Pattern

To prevent configuration drift across microservices and ensure version stability, all questions must be registered in a centralized, versioned registry:

```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class QuestionDef:
    name: str
    version: str
    type: Literal["predicate", "choice", "score"]
    instructions: str
    choices: tuple[dict, ...] | None = None
    levels: tuple[dict, ...] | None = None
    refusal_policy: str = "hold_and_review"

REGISTRY: dict[tuple[str, str], QuestionDef] = {
    ("urgent", "v1"): QuestionDef(
        name="urgent", version="v1", type="predicate",
        instructions="Does the customer report that the service is completely broken right now?",
        refusal_policy="human_queue"
    ),
    ("team", "v4"): QuestionDef(
        name="team", version="v4", type="choice",
        instructions="Which department owns the customer's stated issue?",
        choices=(
            {"value": "billing", "description": "Invoices and payments."},
            {"value": "technical", "description": "Software bugs and errors."},
            {"value": "out_of_scope", "description": "Requests fitting none of these."}
        ),
        refusal_policy="human_queue"
    )
}
```

- When constructing requests, look up questions by `(name, version)`.
- Always log both `name` and `version` in the resulting `DecisionRecord`.

---

## 7. Rules, Reasons, and Counter-Examples

| Rule | Reason | Counter-Example (Anti-Pattern) |
|---|---|---|
| **Batch all questions sharing the same evidence into one request** | Amortizes input token prefill cost; reduces end-to-end latency to a single round-trip. | Making 4 sequential API calls for `is_spam`, `is_toxic`, `is_urgent`, and `language` on the same customer comment. |
| **Always version questions in a centralized registry** | Prevents subtle prompt drift; ensures decisions can be audited against exact historical question schemas. | Defining inline question JSON dictionaries directly inside Flask/FastAPI route handlers. |
| **Never batch questions past 200 items** | Exceeds API limits; leads to attention dilution and gateway connection timeouts. | Submitting 300 line-item verification questions in a single request. |
| **Test for batching interference before deploying** | Cross-attention across unrelated questions can skew marginal probabilities. | Adding a harsh harassment question to a billing router without verifying whether billing accuracy shifts. |
