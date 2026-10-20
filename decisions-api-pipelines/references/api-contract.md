# API Contract: Wire Specification, Topography, Limits & Defensive Parsing

## Contents
1. [Wire Specification Overview](#1-wire-specification-overview)
2. [Request Topography](#2-request-topography)
3. [Response Topography](#3-response-topography)
4. [The Four Answer Variants](#4-the-four-answer-variants)
5. [Volatile Limits & Wire Constraints](#5-volatile-limits--wire-constraints)
6. [Defensive Parsing Specification & Tolerances](#6-defensive-parsing-specification--tolerances)
7. [Error Taxonomy & Gateway Wrapping](#7-error-taxonomy--gateway-wrapping)
8. [Rules, Reasons, and Counter-Examples](#8-rules-reasons-and-counter-examples)

---

## 1. Wire Specification Overview
- **Endpoint**: `POST /v1/decisions` [documented]
- **Authentication**: Bearer Token via `Authorization: Bearer <OPENAI_API_KEY>`
- **SDK Support**: Python SDK `>=3.26.0`, JS/TS `>=7.30.0`, Go `>=3.73.0`, Java `>=4.78.0`, Ruby `>=0.101.0` [documented as of 2026-10-09].
- **Protocol**: HTTP/1.1 or HTTP/2, synchronous JSON request and response.

---

## 2. Request Topography

A valid request consists of three top-level fields, plus an optional security identifier:

```json
{
  "model": "gpt-6-luna",
  "input": "Text string or array of user messages",
  "questions": [
    {
      "type": "predicate | choice | score",
      "name": "string",
      "instructions": "string",
      "...": "type-specific fields"
    }
  ],
  "safety_identifier": "optional-hashed-end-user-id"
}
```

### Field Definitions
- **`model` (string, required)**: Must be `"gpt-6-luna"` [documented as of 2026-10-21]. If routing via a proxy/gateway, use the provider's dedicated decisions model identifier (e.g., `openai/gpt-6-luna-decisions`).
- **`input` (string or array of objects, required)**: Shared evidence evaluated by all questions.
  - *Shape A (Text string)*: Plain string payload for text-only evaluations.
  - *Shape B (User message array)*: Multi-part content blocks containing `input_text` and `input_image`. Only `"role": "user"` is supported [documented as of 2026-10-21]. System, assistant, and tool messages are rejected.
- **`questions` (array of objects, required)**: 1 to 200 question definitions [community report]. Each question contains:
  - `type` (string): `"predicate"`, `"choice"`, or `"score"`.
  - `name` (string): Unique identifier for matching the answer. Must be treated as mandatory in production code.
  - `instructions` (string): The observable criterion to evaluate.
  - *Type-specific payload*:
    - `predicate`: No extra fields.
    - `choice`: `choices` array of `{"value": str, "description": str}`.
    - `score`: `levels` array of `{"label": str, "description": str}` (strictly ascending order).
- **`safety_identifier` (string, optional)**: Opaque end-user identifier scoped by verified organization for abuse attribution. Send a stable SHA-256 hash of your internal user ID; never send raw PII [documented].

---

## 3. Response Topography

```json
{
  "id": "dec_8f7b3c21a",
  "created": 1729382400,
  "model": "gpt-6-luna",
  "object": "decision",
  "usage": {
    "input_tokens": 406,
    "output_tokens": 0,
    "reasoning_tokens": 0,
    "input_tokens_details": {
      "cached_tokens": 0,
      "cache_write_tokens": 0
    }
  },
  "answers": [
    { ...answer 1... },
    { ...answer 2... }
  ]
}
```

### Usage Block Semantics
- `input_tokens`: Billed tokens covering fixed request overhead (~137–145 tokens on empty/minimal inputs), input payload tokens, and definitions for all batched questions.
- `output_tokens`: Strictly `0`. Bounded evaluation generates no output text tokens [documented].
- `reasoning_tokens`: Strictly `0`. No autoregressive chain-of-thought is executed [documented].
- `cached_tokens`: Tokens read from prompt prefix cache [documented].

---

## 4. The Four Answer Variants

### Variant 1: `predicate`
```json
{
  "name": "is_urgent",
  "type": "predicate",
  "probability": 0.94
}
```
- `probability`: Float rounded to 2 decimal places [0.00 to 1.00]. Reflects marginal likelihood of the condition being true.

### Variant 2: `choice`
```json
{
  "name": "assigned_team",
  "type": "choice",
  "choice": "billing",
  "confidence": 0.88,
  "distribution": {
    "billing": 0.88,
    "technical": 0.08,
    "other": 0.04
  }
}
```
- `choice`: String value corresponding to the winning choice `value`.
- `confidence`: Float [0.00 to 1.00] representing the winning option's probability or margin.
- `distribution`: Object mapping every declared choice value to its computed probability.

### Variant 3: `score`
```json
{
  "name": "severity_score",
  "type": "score",
  "score": 1.84,
  "confidence": 0.72,
  "level": "Workaround available",
  "distribution": {
    "Cosmetic": 0.08,
    "Workaround available": 0.72,
    "Fully blocked": 0.20
  }
}
```
- `score`: Continuous expected value float: $\text{score} = \frac{\sum_{i=0}^{K-1} i \cdot p_i}{\sum p_i}$.
- `level`: String label corresponding to the level with the highest probability mass (argmax).
- `confidence`: Float [0.00 to 1.00] representing the argmax level's probability.
- `distribution`: Object mapping every declared level label to its probability.

### Variant 4: `refusal`
```json
{
  "name": "tool_destructive",
  "type": "refusal"
}
```
- Occurs when the model declines to evaluate a specific question under safety policies.
- Note: Other questions in the same request can succeed normally.
- Does not disclose a refusal score or reason code [documented].

---

## 5. Volatile Limits & Wire Constraints (as of 2026-10-21)
These limits represent the conservative intersection of official docs and third-party reports:

| Feature / Limit | Status as of 2026-10-21 | Source Tag |
|---|---|---|
| **Supported Model** | `gpt-6-luna` only | [documented] |
| **Max Questions per Request** | 200 questions max | [community report] |
| **Max Options per Choice** | 255 options max | [community report] |
| **Max Images per Request** | 128 images max | [documented] |
| **Image Transport** | Inline base64 data URLs only (`data:image/jpeg;base64,...`). Hosted HTTP/HTTPS URLs and `file_id` are rejected. | [documented] |
| **Accepted Roles** | `role: "user"` only. System/assistant/tool rejected. | [documented] |
| **Request Caching Parameters** | Removed from request schema. `prompt_cache_key` and `prompt_cache_breakpoint` are unsupported. | [documented] |
| **Probability Precision** | Two decimal places (e.g. 0.84) | [documented] |
| **Long-Context Threshold** | Assumed cliff at 272,000 input tokens | [inference/estimate] |

---

## 6. Defensive Parsing Specification & Tolerances

A production response parser must validate the response defensively:

1. **Top-Level Envelope**: Verify `object == "decision"`, `id` is present, and `answers` is a list.
2. **Key Matching by Name**: Map answers by `name`, never by list index. Throw `ContractError` if a requested question name is missing from `answers`.
3. **Probability Sum Tolerance**: Due to two-decimal rounding, distribution probabilities may not sum to exactly 1.0. The allowable tolerance is:
   $$\text{tol} = 0.005 \times N_{\text{options}} + 1\times 10^{-9}$$
   If $|\sum p_i - 1.0| > \text{tol}$, raise `ContractViolationError`.
4. **Declared Option Validation**: Verify that the returned `choice` or `level` strictly belongs to the declared question options.
5. **Score Consistency**: Validate that the returned continuous `score` matches the weighted sum of the distribution within $\pm 0.02$.
6. **Refusal Recognition**: An answer with `type == "refusal"` must be parsed into a typed `RefusalAnswer`, never coerced to `False`, `0.0`, or the lowest level.

---

## 7. Error Taxonomy & Gateway Wrapping

| Error State | HTTP Status | Retryable? | Recommended Action |
|---|---|---|---|
| **Per-Question Refusal** | 200 OK | No | Route to question's declared refusal policy (`block`, `hold_and_review`, `human_queue`, `missing`). |
| **Gateway Refusal Wrapper** | 502 Bad Gateway | Recover | Extract regex `refused to answer question "([^"]+)"`. Mark target question as refused; recover remainder. |
| **Contract Violation** | 200 OK | Once | Quarantine raw payload, alert engineering, log payload fingerprint. |
| **Invalid Request** | 400 Bad Request | Never | Fail immediately; fix question/input schema. |
| **Auth / Permissions** | 401 / 403 | Never | Alert on-call; switch to degraded mode. |
| **Quota / Spend Limit** | 429 (`insufficient_quota`) | Never | Alert on-call; switch to degraded mode. |
| **Rate Limit / Capacity** | 429 (`rate_limit_exceeded`) | Yes | Exponential backoff with jitter; honor `Retry-After`. |
| **Server / Transport** | 500, 503, connection reset | Yes | Up to 2 retries; increment circuit breaker. |
| **Client Deadline Exceeded** | Local timeout | No | Trigger pipeline provisional default. |

---

## 8. Rules, Reasons, and Counter-Examples

| Rule | Reason | Counter-Example (Anti-Pattern) |
|---|---|---|
| **Always give every question a unique `name`** | SDKs make `name` optional, but without names, answers must be matched by array position. Changing question order silently corrupts business logic. | Building questions `[{"type": "predicate", "instructions": "..."}]` without specifying `"name": "is_refund"`. |
| **Never pass image URLs or `file_id`** | The `/v1/decisions` endpoint rejects non-data-URL images with 400 Bad Request. | Passing `{"type": "input_image", "image_url": "https://example.com/item.png"}`. |
| **Always validate distribution sums with rounding tolerance** | Probabilities are rounded to 2 decimals; strict `sum == 1.0` checks cause false-positive production alerts. | Code doing `assert sum(answer.distribution.values()) == 1.0`. |
| **Order `score` levels strictly lowest to highest** | The API maps 0, 1, 2... to the array indices. Reversing levels inverts the mathematical meaning of the expected score. | Submitting `levels: ["Critical", "High", "Medium", "Low"]` (Critical gets index 0, Low gets index 3). |
