# Reliability & Error Handling: Refusals, Retries, Deadlines & Circuit Breakers

## Contents
1. [Failure State Taxonomy](#1-failure-state-taxonomy)
2. [Refusals: Causes & The Three Non-Negotiable Rules](#2-refusals-causes--the-three-non-negotiable-rules)
3. [Gateway Refusal Recovery](#3-gateway-refusal-recovery)
4. [Whole-Request Retries with Backoff & Jitter](#4-whole-request-retries-with-backoff--jitter)
5. [Global Deadlines & Provisional Actions](#5-global-deadlines--provisional-actions)
6. [Circuit Breaker Specification](#6-circuit-breaker-specification)
7. [The Immutable Decision Record](#7-the-immutable-decision-record)
8. [Rules, Reasons, and Counter-Examples](#8-rules-reasons-and-counter-examples)

---

## 1. Failure State Taxonomy

A production Decisions API client must distinguish between distinct failure modes that dictate operational recovery:

| Failure State | Arrives As | Retryable? | Immediate Action |
|---|---|---|---|
| **Per-Question Refusal** | HTTP 200, answer has `type: "refusal"` | **No** | Execute question's declared refusal policy (`block`, `hold_and_review`, `human_queue`, `missing`). |
| **Gateway Refusal Wrapper** | HTTP 502 error body naming refused question | **No** (for that question) | Parse regex to identify refused question; mark it refused and recover surviving answers. |
| **Contract Violation** | HTTP 200, invalid JSON shape / missing keys | Once | Quarantine raw body, log fingerprint, alert engineering. |
| **Invalid Request** | HTTP 400 Bad Request | **Never** | Fail immediately; fix schema/input bug. |
| **Auth / Permissions** | HTTP 401 Unauthorized / 403 Forbidden | **Never** | Alert on-call; switch to degraded offline mode. |
| **Quota / Billing Exceeded** | HTTP 429 (`insufficient_quota`) | **Never** | Alert on-call; switch to degraded mode. |
| **Rate Limit / Capacity** | HTTP 429 (`rate_limit_exceeded`) | **Yes** | Exponential backoff with jitter; honor `Retry-After`. |
| **Transport / 5xx Error** | HTTP 500, 503, connection reset | **Yes** (up to 2) | Back off; increment circuit breaker failure count. |
| **Deadline Exceeded** | Local execution timeout elapsed | **No** | Trigger pipeline's safe provisional default action. |

---

## 2. Refusals: Causes & The Three Non-Negotiable Rules

A refusal occurs when the model declines to evaluate a specific question under safety policies [documented].

### Key Empirical Facts
- **No Refusal Score**: The API indicates *that* a question refused, but does not disclose a reason code or confidence score [documented].
- **Adversarial Spillover**: Hostile text in one section of an input can cause the model to refuse an unrelated benign question batched in the same request [documented].
- **Persistent on Benign Inputs**: Ordinary logic puzzles can trigger persistent refusals across all retry attempts (e.g., etsabary benchmark: 17 benign items refused 5 consecutive times) [community report].

### The Three Rules
1. **Never retry a refusal identically**: The endpoint is deterministic in testing. An identical retry consumes latency and money without resolving the refusal.
2. **Never build automated rephrasing loops at runtime**: Looping through synonyms to bypass a safety refusal violates safety policies and introduces uncalibrated runtime behavior. Rephrasing belongs offline in your dev set.
3. **Declare an explicit refusal policy for every question**:
   Store the refusal policy in the centralized question registry:
   ```python
   REFUSAL_POLICIES = {
       "tool_destructive": "block",            # Fail closed on safety gates
       "threatens_harm":   "hold_and_review",  # Human review required
       "team":             "human_queue",      # Route to manual triage
       "mentions_delivery":"missing"           # Non-critical: policy uses fallback
   }
   ```
   *Never coerce a refusal to `False`, `0.0`, or the lowest score level.*

---

## 3. Gateway Refusal Recovery

Some gateways (e.g. OpenRouter) convert a single per-question refusal into a top-level HTTP 502 error, destroying surviving answers in the batch.
- Extract the refused question name using regex:
  ```python
  import re
  GATEWAY_REFUSAL_RE = re.compile(r'refused to answer question [\\"]*([^"\\\\]+)[\\"]*')

  def recover_gateway_refusal(error_message: str) -> str | None:
      match = GATEWAY_REFUSAL_RE.search(error_message)
      return match.group(1) if match else None
  ```
- If a gateway refusal is identified, re-issue the request excluding the refused question to recover answers for remaining questions, while marking the target question as refused in the decision record.

---

## 4. Whole-Request Retries with Backoff & Jitter

Retries are safe because `POST /v1/decisions` is a pure read operation with **no server-side side effects**.

### Implementation Rules
- Retry **only whole requests**. Never attempt partial resubmissions unless executing gateway recovery.
- Maximum attempts:
  - Transport errors (500, 503, network reset): **2 attempts**.
  - Rate limits (429): **3 attempts**.
  - Contract violations: **1 attempt**.
- Apply exponential backoff with full jitter:
  $$t_{\text{sleep}} = \text{random.uniform}(0, \min(t_{\text{max}}, t_{\text{base}} \times 2^{\text{attempt}}))$$
  If `Retry-After` header is present, honor it strictly.

---

## 5. Global Deadlines & Provisional Actions

In real-time systems, multi-round cascades must respect a global SLA deadline:

```python
import time

def execute_with_deadline(deadline_timestamp: float):
    remaining = deadline_timestamp - time.time()
    if remaining <= 0.05:
        # Time exhausted: take safe provisional default
        return trigger_provisional_action("deadline_exceeded")
    
    # Pass remaining timeout to client
    return client.decisions.create(..., timeout=remaining)
```

### Provisional Actions
- **User-Facing Comment**: Provisionally hold comment in moderation queue (`status = "hold_provisional"`).
- **Customer Support Ticket**: Acknowledge ticket receipt immediately; perform detailed routing and escalation asynchronously in background workers.

---

## 6. Circuit Breaker Specification

When the API or network suffers severe degradation, continuing to issue requests amplifies latency and queue pileups. Use a sliding-window circuit breaker:

```python
import time

class Breaker:
    def __init__(self, failure_threshold: float = 0.50, window_size: int = 50, cooldown: float = 30.0):
        self.threshold = failure_threshold
        self.window_size = window_size
        self.cooldown = cooldown
        self.calls: list[tuple[float, bool]] = []
        self.tripped_until = 0.0

    def allow_request(self) -> bool:
        now = time.time()
        if now < self.tripped_until:
            return False  # Open: reject immediately
        return True

    def record_result(self, success: bool):
        now = time.time()
        self.calls.append((now, success))
        # Trim window
        if len(self.calls) > self.window_size:
            self.calls.pop(0)
            
        if len(self.calls) >= 10:
            failures = sum(1 for _, ok in self.calls if not ok)
            if (failures / len(self.calls)) >= self.threshold:
                self.tripped_until = now + self.cooldown
```

When tripped, pipelines instantly fail over to local degraded modes (routing to general queue, holding for manual review).

---

## 7. The Immutable Decision Record

Every pipeline execution must emit a complete, immutable audit record:

```python
import hashlib, json, time
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class DecisionRecord:
    item_id: str
    timestamp: float
    evidence_hash: str
    question_versions: list[tuple[str, str]]  # [(name, version), ...]
    schema_version: str
    raw_answers: dict
    actions_taken: list[str]
    provisional: bool

def make_evidence_hash(evidence_payload: str | list) -> str:
    raw_bytes = json.dumps(evidence_payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw_bytes).hexdigest()
```

Logging `evidence_hash` and `(name, version)` pairs allows exact offline recreation and debugging of any historical automated action.

---

## 8. Rules, Reasons, and Counter-Examples

| Rule | Reason | Counter-Example (Anti-Pattern) |
|---|---|---|
| **Never retry an identical refusal** | The Decisions API is deterministic; an identical call persists in refusing while wasting money and latency. | Wrapping an API call in `while attempt < 5` when the answer is a safety refusal. |
| **Never coerce refusals to false or zero** | A refusal represents an unmade judgment; treating it as negative disables safety guardrails. | Setting `is_toxic = False` when the toxicity question returns `type: "refusal"`. |
| **Pass an absolute deadline down multi-round chains** | Prevents serial cascade calls from exceeding upstream web-request timeouts. | Calling stage 1 (timeout 5s), then stage 2 (timeout 5s), on an HTTP endpoint with an 8s client SLA. |
| **Log evidence hashes in decision records** | Enables exact auditing and reproduction of decisions without duplicating massive document bodies. | Storing only the final routing choice without recording the evidence hash or question versions. |
