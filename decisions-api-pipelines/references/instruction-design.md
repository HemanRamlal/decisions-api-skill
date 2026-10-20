# Instruction Design: Observables, Proof Depth & Criteria Bleed

## Contents
1. [Instruction Anatomy for System 1 Evaluation](#1-instruction-anatomy-for-system-1-evaluation)
2. [The Proof Depth Taxonomy (Depth 0 to 5)](#2-the-proof-depth-taxonomy-depth-0-to-5)
3. [Criteria Bleed in Batched Requests](#3-criteria-bleed-in-batched-requests)
4. [Observable Questions vs. Verdict Words](#4-observable-questions-vs-verdict-words)
5. [DRY Instruction Architecture in Code](#5-dry-instruction-architecture-in-code)
6. [Wording Sensitivity vs. Model Uncertainty](#6-wording-sensitivity-vs-model-uncertainty)
7. [Rules, Reasons, and Counter-Examples](#7-rules-reasons-and-counter-examples)

---

## 1. Instruction Anatomy for System 1 Evaluation

An effective instruction in the Decisions API specifies a single, glance-level observation over the evidence.

### Structural Requirements
- **Anchor to Delimiters**: Explicitly direct attention to the sanitized boundary (e.g., `"In <<TICKET>>, does the customer report..."`).
- **Define Positive Presence**: Frame the instruction around what visible evidence confirms the condition.
- **Explicit Exclusion Clauses**: State boundary conditions directly (e.g., `"Excludes automated confirmations and routine status checks"`).
- **No Thinking Directives**: Exclude prompt engineering boilerplate ("You are an expert", "Think step by step", "Be thorough").

---

## 2. The Proof Depth Taxonomy (Depth 0 to 5)

Proof depth measures the number of logical deduction steps required to move from the provided facts to the target proposition [documented based on ProofWriter benchmark analysis]:

| Depth | Definition | Decisions API Reliability | Implementation Guidance |
|---|---|---|---|
| **Depth 0** | The fact is stated directly in the text verbatim. | **Near 100%** | Ideal for Decisions API. Direct fact-matching. |
| **Depth 1** | One deductive rule applied to stated facts ("If A then B"). | **High (>90%)** | Reliable for straightforward single-clause rules. |
| **Depth 2** | Two rules chained sequentially ("A $\to$ B $\to$ C"). | **Degrades (~65–75%)** | Borderline. Decompose into two questions or move logic to code. |
| **Depth 3** | Three deduction steps chained with distractors. | **Unreliable (<50%)** | **Forbidden**. Model fails without scratchpad/reasoning tokens. |
| **Depth 4–5** | Deep multi-step deduction over complex distractors. | **Fails completely** | Must use a reasoning model (Responses API) or deterministic Python solver. |

### The Decomposition Mandate
When a business rule requires Depth $\ge 2$, decompose it into Depth 0 or 1 questions, then chain them in Python.
- *Example*: Checking if an insurance claim is valid requires: (1) damage occurred during policy period, (2) deductible is met, (3) peril is covered, (4) claimant is named insured.
- *Flawed Design*: One prompt asking "Is this claim valid and covered under Policy Section 4?" (Depth 3+ deduction).
- *Correct Design*: Model evaluates observable questions (`peril_matches_water`, `damage_photo_authentic`); application code checks policy dates, deductible arithmetic, and coverage limits.

---

## 3. Criteria Bleed in Batched Requests

When multiple questions are batched in a single request, the model's self-attention layers compute cross-attention across all question instructions.

### The Mechanism of Bleed
- If Question A asks about "harassment and hostility" and Question B asks about "urgency", the harsh framing of Question A can artificially inflate the perceived urgency in Question B.
- If Question C includes detailed exclusions, Question D may inadvertently incorporate those exclusions.

### Defending Against Criteria Bleed
1. **Neutral Phrasing**: Keep question instructions objective and matter-of-fact. Avoid emotive language.
2. **Isolation Testing**: Run the `interference_test` (Module 4) during pipeline validation: test Question B in isolation, then in the full batch. If its probability distribution shifts significantly ($|\Delta p| > 0.05$), decouple the questions or rephrase.

---

## 4. Observable Questions vs. Verdict Words

Subjective verdict words introduce high variance and poor calibration because they require unstated normative judgments.

| Subjective Verdict Word | Why It Fails | Observable Alternative |
|---|---|---|
| **"Spam"** | Differs widely between users; conflates self-promotion, phishing, and off-topic posts. | "Does the text contain promotional links, discount codes, or offers for unrelated products?" |
| **"Angry"** | Internal emotional state; model hallucinates aggression from formal complaints. | "Does the message contain profanity, all-caps yelling, insults, or explicit threats to cancel/sue?" |
| **"Toxic"** | Vague umbrella term that triggers over-eager model safety filters. | "Does the comment use slurs, dehumanizing language, or incite physical violence?" |
| **"Urgent"** | Every customer believes their issue is urgent. | "Does the customer report complete service unavailability for all users right now?" |

---

## 5. DRY Instruction Architecture in Code

Never duplicate category definitions across multiple question objects. Keep definitions single-sourced in code:

```python
# DRY definition repository
TEAM_DEFINITIONS = {
    "billing": "Payments, credit card charges, invoices, and refund status.",
    "technical": "Errors, unexpected exceptions, API failures, and broken functionality.",
    "shipping": "Tracking numbers, lost packages, physical damage in transit.",
    "out_of_scope": "Partnership inquiries, marketing solicitations, or irrelevant topics.",
    "no_request": "The message expresses frustration or confusion but states no actionable issue."
}

def build_team_choices() -> list[dict]:
    return [{"value": k, "description": v} for k, v in TEAM_DEFINITIONS.items()]
```

If a definition changes, updating `TEAM_DEFINITIONS` automatically updates the router, escalation logic, and documentation.

---

## 6. Wording Sensitivity vs. Model Uncertainty

When evaluating edge-case performance, do not mistake wording sensitivity for inherent model uncertainty:

- **True Model Uncertainty**: The evidence itself is ambiguous (e.g. an image is blurry). Changing the question's wording slightly leaves the distribution uncertain.
- **Wording Sensitivity**: Two instructions that mean the exact same thing produce wildly different probability distributions (e.g. $p=0.35$ vs. $p=0.88$).

### Paraphrase Testing Protocol
Run `paraphrase_test(items, base_q, paraphrases, threshold)` before deploying:
1. Generate 3–5 semantically identical paraphrases of the instruction.
2. Evaluate all paraphrases over a validation set.
3. If the average probability shift exceeds 0.05, the instruction is brittle and must be rewritten with more explicit observable constraints.

---

## 7. Rules, Reasons, and Counter-Examples

| Rule | Reason | Counter-Example (Anti-Pattern) |
|---|---|---|
| **Never submit Depth $\ge 2$ questions to Decisions API** | Without autoregressive scratchpad tokens, multi-step deductive reasoning accuracy drops below 60%. | Instruction: "Based on the lease agreement, calculate if the tenant gave sufficient notice to avoid automatic renewal." |
| **Never use verdict words as question targets** | High variance, uncalibrated probabilities, and unpredictable threshold behavior. | Question: "Is this user communication toxic?" |
| **Always centralize option definitions in code constants** | Duplicated inline strings diverge over time, corrupting classification consistency. | Hardcoding choice descriptions in 4 different pipeline files with slightly different wording. |
| **Validate instruction robustness with paraphrase sweeps** | Detects prompt brittleness before shipping to production traffic. | Shipping an instruction tested on only 5 examples without checking semantic variants. |
