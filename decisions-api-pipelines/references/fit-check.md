# Fit Check: Bounded Evaluation vs. Generation & System 1 Partitioning

## Contents
1. [The Core Question](#1-the-core-question)
2. [Generation vs. Bounded Evaluation](#2-generation-vs-bounded-evaluation)
3. [The Constrained Softmax Mental Model](#3-the-constrained-softmax-mental-model)
4. [Empirical Speed & Accuracy Comparison](#4-empirical-speed--accuracy-comparison)
5. [Decisions API vs. Structured Outputs](#5-decisions-api-vs-structured-outputs)
6. [Gateway Pitfalls](#6-gateway-pitfalls)
7. [System 1 Determinism & Policy Splitting](#7-system-1-determinism--policy-splitting)
8. [Rules, Reasons, and Counter-Examples](#8-rules-reasons-and-counter-examples)

---

## 1. The Core Question
Before writing any code or prompting a model, determine what the system is fundamentally being asked to do:
- **Autoregressive Generation (Mode 1)**: Produce new text, code, translations, or summaries by sampling tokens one by one.
- **Bounded Evaluation (Mode 2)**: Select from a fixed, pre-declared set of discrete states or evaluate an observable condition over provided evidence.

If the output consists of content that must be generated, use the Responses API. If the output is a judgment over a fixed set of options where confidence and probability distribution are required, use the Decisions API.

---

## 2. Generation vs. Bounded Evaluation

| Attribute | Autoregressive Generation (Responses / Chat API) | Bounded Evaluation (Decisions API) |
|---|---|---|
| **Primary Task** | Writing tokens sequentially based on context. | Evaluating pre-defined options over evidence in a single pass. |
| **Output Shape** | Unstructured or structured text string. | Typed primitive (`probability`, `choice` + `confidence`, `score`). |
| **Parsing** | Must parse text/JSON; failure modes include syntax errors and invalid values. | Direct typed object in response; schema violations impossible. |
| **Probabilities** | Model-generated self-reported confidence is an unreliable text token. | Native probability distribution over discrete declared states. |
| **Tokens Billed** | Input tokens + Output tokens (often including reasoning tokens). | Input tokens only; `output_tokens: 0`, `reasoning_tokens: 0` [documented]. |
| **Latency Profile** | Hundreds of milliseconds to tens of seconds (scales with output length). | Fast single forward pass (~255ms median in benchmark) [community report]. |

---

## 3. The Constrained Softmax Mental Model
- **Mental Model**: Instead of projecting the final hidden representation across the entire 100k+ token vocabulary across autoregressive decode steps, probability mass is evaluated directly over the declared discrete candidate options.
- **Internal Reality Caveat**: This is a *conceptual* mental model, not a confirmed proprietary architecture description [inference/estimate]. Public documentation describes the outputs (probabilities, choices with confidence, score levels) rather than the underlying internal weights or heads.
- **Computation Without Output Tokens**: The model computes during the forward prefill pass. It performs deep non-linear transformations across all layers, but does not execute token-by-token chain-of-thought [documented]. The usage block reports `reasoning_tokens: 0`.

---

## 4. Empirical Speed & Accuracy Comparison
- **Speed**: OpenAI claims `/v1/decisions` produces answers ~10x faster than the Responses API [vendor claim]. Third-party benchmarks (Classmethod, 2026-10-09) show ~255ms median latency on 3-question requests [community report].
- **Accuracy Benchmarks**:
  - *nic-esp/luna-jev-benchmark* (4,785 cases across BoolQ, RTE, WiC): Jev had higher label agreement on BoolQ and ran 5x faster serially; Luna had lower error on synthetic probabilities; cached Luna cost 35.4% less than Jev on long-rulebook tasks [community report]. (Note: Tested Luna via structured output, not the Decisions endpoint).
  - *ML6 Benchmark* (10,000 phishing, 5,728 spam emails): Jev scored 99.99% on phishing and 95.06% on spam; GPT-6 Luna scored 99.96% on phishing and 92.82% on spam. The difference was statistically negligible [community report].
  - *matsonj/eval-connections* (NYT Connections puzzle): Jev won 14.8/20 at $0.06/run vs. Luna Decisions at 9.7/20 at $0.20/run (biased toward Jev's tuning) [community report].
- **Engineering Guidance**: Do not rely on public leaderboards. Construct a domain-specific evaluation set (Module 5) with several hundred human-labeled examples from real traffic to evaluate accuracy directly.

---

## 5. Decisions API vs. Structured Outputs
An enum schema via Structured Outputs (`{"department": {"type": "string", "enum": [...]}}`) does not replace the Decisions API.

### The Three Real Differences
1. **Full Distribution vs. Point Argmax**: Structured Outputs samples a single token sequence (the argmax or sampled choice). The Decisions API returns probabilities for *all* declared options, allowing margin computation, entropy tracking, and threshold sweeps.
2. **True Probabilities vs. Self-Reported Tokens**: Asking a generative model to return `{"confidence": 0.95}` outputs a generated string of characters. LLMs have poor calibration when predicting their own confidence as text tokens. The Decisions API provides normalized forward-pass probabilities.
3. **Billing and Token Generation**: Structured Outputs bills for every generated token (and schema constraint tokens). Decisions API generates zero output tokens (`output_tokens: 0`) and bills strictly for input tokens.

### When Structured Outputs is Still the Right Tool
- **Extraction**: Extracting dates, order IDs, account numbers, names, or addresses from unstructured text.
- **Unbounded Sets**: When candidate values cannot be listed in advance.
- **Free-Form Generation**: Summaries, customer-facing draft responses, explanations.

---

## 6. Gateway Pitfalls
When routing requests through third-party AI gateways (e.g., Vercel AI Gateway, LiteLLM):
- **Model ID Confusion**: Gateways often maintain distinct model IDs. For example, Vercel maps `openai/gpt-6-luna-decisions` to the Decisions endpoint, while `openai/gpt-6-luna` routes to autoregressive chat generation [documented].
- **Symptom**: Calling `openai/gpt-6-luna` on a gateway defaults to structured output generation, incurring output token costs, multi-second latency, and losing full probability distributions.
- **Refusal Transformation**: Some gateways convert per-question refusals into top-level HTTP 502 errors [community report]. The client must inspect error bodies to recover surviving answers.

---

## 7. System 1 Determinism & Policy Splitting
The core architecture pattern: **Let the model perceive; let code decide.**

### The System 1 / System 2 Division
- **System 1 (Model)**: Fast, intuitive, perception-only judgment over observable evidence (e.g., "Does this image show water damage?", "Which team handles this topic?").
- **System 2 (Deterministic Application Code)**: Thresholds, policy evaluation, strike counting, arithmetic, calendar math, routing, database side effects.

### The Anti-Pattern: Policy Hidden in Prompts
- *Bad Prompt*: "Review this comment. If the user has 3 or more strikes, issue a permanent ban. If they are a verified premium user, only issue a warning unless the violation is severe."
- *Consequences*:
  - The model must perform counter tracking and multi-condition branch logic.
  - Policy changes require re-prompting and risk hallucinated rules.
  - Business rules cannot be audited or unit-tested offline.
- *Correct Refactor*:
  - Model Question 1: `predicate` for `violates_conduct_rules`.
  - Model Question 2: `score` for `severity` (Cosmetic, Minor, Major, Egregious).
  - Code reads customer tier and prior strike count from CRM/database, applies versioned Python logic, and issues the appropriate sanction.

---

## 8. Rules, Reasons, and Counter-Examples

| Rule | Reason | Counter-Example (Anti-Pattern) |
|---|---|---|
| **Never ask the model for facts your code already owns** | Saves tokens, eliminates hallucination of database facts, prevents policy corruption. | Asking the model: "Is this user an enterprise customer with an active premium SLA?" when the user ID is in the session database. |
| **Separate intent from entitlement** | A customer's expressed desire is perception; whether they qualify for an action is business policy. | Question: "Is this customer eligible for a $50 refund?" instead of "Does the customer ask for money back?" combined with code checking return window dates. |
| **Never instruct the model to reason step-by-step** | Decisions API runs a single prefill pass with no autoregressive decoding; "think step by step" adds prompt tokens with zero effect. | Instruction: "Think carefully step by step, evaluate the pros and cons, and then decide if this ticket is billing." |
| **Decompose compound criteria into atomic questions** | Conjunctions ("and", "or") conflate independent signals, obscuring why a judgment was made and preventing partial reuse. | Instruction: "Is this review promotional or does it contain personal contact information?" |
