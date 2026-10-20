# Primitives: Predicate, Choice, Score & Probability Math

## Contents
1. [Overview of the Three Primitives](#1-overview-of-the-three-primitives)
2. [The `predicate` Primitive](#2-the-predicate-primitive)
3. [The `choice` Primitive](#3-the-choice-primitive)
4. [The `score` Primitive](#4-the-score-primitive)
5. [Distribution Math & Expected Values](#5-distribution-math--expected-values)
6. [Primitive Selection Decision Matrix](#6-primitive-selection-decision-matrix)
7. [Rules, Reasons, and Counter-Examples](#7-rules-reasons-and-counter-examples)

---

## 1. Overview of the Three Primitives

The Decisions API offers exactly three primitives:

| Primitive | Target Problem | Output Fields | Key Properties |
|---|---|---|---|
| **`predicate`** | Binary condition checking | `probability` | 0.00 to 1.00; calibrated probability of proposition. |
| **`choice`** | Categorization across unordered options | `choice`, `confidence`, `distribution` | Categorical argmax; margin; full probability distribution over discrete values. |
| **`score`** | Ordered severity, progression, or rubric rating | `score`, `confidence`, `level`, `distribution` | Expected value float; argmax label; full mass across ordinal indices. |

---

## 2. The `predicate` Primitive

A `predicate` tests whether a specific proposition is supported by the input evidence.

### What the Number Means
- `probability`: The model's estimated likelihood that the proposition is true, conditioned on the evidence.
- *What it is NOT*: It is not a measure of severity, not the percentage of the document affected, and not the fraction of users complaining. A predicate returning `0.5` does not mean "the input is 50% toxic"; it means the model estimates a 50% chance the document is toxic.

### Five Phrasing Rules
1. **Positive Polarity**: State the proposition positively ("Is the shipment delayed?"). Negations ("Is the shipment not delayed?") invert probability interpretation and cause reasoning errors. Use negation only in specific exclusion clauses.
2. **Single Atomic Condition**: Test exactly one condition. Avoid conjunctions ("and", "or"). For compound policies, evaluate separate predicates and combine them in code.
3. **Observable Cues Over Verdict Words**: Avoid subjective verdict words ("spam", "toxic", "angry"). Describe observable symptoms:
   - *Weak*: "Is this review spam?"
   - *Strong*: "Does this review contain promotional links, discount codes, or offers for unrelated products?"
4. **No Instructions About Thinking**: Strip out "think carefully", "justify your answer", or "evaluate step-by-step". Bounded evaluation runs a single forward pass; reasoning directives waste tokens without affecting judgment.
5. **Separate the Evidence Gate**: If an image or text can be unusable, test an explicit gate predicate first (`photo_usable`), rather than allowing missing evidence to silently collapse the main predicate to false.

---

## 3. The `choice` Primitive

A `choice` categorizes input into one of several mutually exclusive, unordered options.

### Option Structure
Each option in `choices` requires:
- `value`: Stable, machine-readable string returned to application code (e.g., `"billing"`). Never use UI labels, URLs, or dynamic actions as values.
- `description`: Explains precisely when this option applies, including explicit boundaries and exclusions. Descriptions are technically optional in the SDK, but mandatory in production: they are the only place option semantics are defined.

### Phrasing & Escape Options
- **Fixed Order in Production**: Maintain a fixed, versioned order for choices in production. Shuffle choices only during offline bias evaluation.
- **Escape Options (`out_of_scope` vs. `no_request`)**:
  - Every `choice` must include an escape option if the categories do not cover 100% of inputs [documented].
  - Distinguish between "fits no category" (`out_of_scope`) and "insufficient evidence" (`no_request`). Merging them into a single `"other"` obscures the correct operational response (routing to general queue vs. asking customer for clarification).
  - Do NOT provide an `"unsure"` option. Model uncertainty is already captured in the probability distribution. An `"unsure"` option acts as an attractor, absorbing mass from valid categories.

### Renormalization Over Active Categories
When evaluating the winning option among legitimate business categories (ignoring escape options), renormalize probabilities in code:

$$p_{\text{renorm}}(c) = \frac{p(c)}{\sum_{k \in \text{Categories}} p(k)}$$

Only apply the classification threshold to $p_{\text{renorm}}(c)$ after verifying that the total escape mass $P(\text{escapes}) = p(\text{out\_of\_scope}) + p(\text{no\_request})$ is below the escape threshold.

---

## 4. The `score` Primitive

A `score` evaluates input against an ordered scale of severity, maturity, or impact.

### Level Ordering
- Levels must be listed strictly from **lowest to highest** (e.g., Cosmetic $\to$ Minor $\to$ Major $\to$ Blocked).
- The API maps indices $0, 1, \dots, K-1$ to levels by array position. Reversing levels silently inverts the expected score.
- Levels must differ by observable factual differences, not vague adjectives.

### "Three Numbers, Three Jobs"
The response returns three distinct fields, each suited for a specific task:
1. **`score` (Expected Value)**: A continuous float. Ideal for global queue ranking, priority sorting, and aggregate telemetry.
2. **`level` (Argmax Label)**: The single level with the highest probability. Useful for SLA assignment when uncertainty is low.
3. **`distribution` (Full Mass)**: Required for safety checks and escalation. Two identical expected scores can represent completely different operational states.

---

## 5. Distribution Math & Expected Values

### The Expected Score Formula
$$\text{score} = \frac{\sum_{i=0}^{K-1} i \cdot p_i}{\sum_{i=0}^{K-1} p_i}$$

### Bimodal Distributions vs. Unimodal Certainty
Consider two responses for a 5-level score (levels 0 to 4):
- **Case A**: Distribution `[0.0, 0.0, 1.0, 0.0, 0.0]`. Score = $2.0$, Confidence = $1.0$.
  - *Diagnosis*: Unambiguous moderate severity. Safe for automated handling.
- **Case B**: Distribution `[0.5, 0.0, 0.0, 0.0, 0.5]`. Score = $0 \times 0.5 + 4 \times 0.5 = 2.0$, Confidence = $0.5$.
  - *Diagnosis*: Extreme bimodal disagreement. The model finds equal evidence for "no issue" and "catastrophic failure".
  - *Action*: Never automate based on the expected score $2.0$ alone. Inspect the distribution; route bimodal or split distributions directly to human review or higher-tier escalation.

### Composite Queue Ranking
When ordering items in an operational queue, rank by the coarse level first, then break ties using expected cost:

$$\text{rank\_key} = (\text{assigned\_level}, \mathbb{E}[\text{cost}])$$

$$\mathbb{E}[\text{cost}] = \sum_{i=0}^{K-1} p_i \cdot \text{Cost}(i)$$

---

## 6. Primitive Selection Decision Matrix

```
                    ┌─────────────────────────┐
                    │ What is the evaluation? │
                    └────────────┬────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
   Binary Condition      Categorical State        Ordered Progression
   ("yes / no",          ("which department?",    ("severity", "impact",
    "present / absent")   "which team?")           "quality rubric")
         │                       │                       │
         ▼                       ▼                       ▼
    `predicate`               `choice`                `score`
(Threshold on prob)    (Argmax + Renormalized   (Expected value + Bimodal
                        Margin + Escapes)        variance check)
```

- If options can co-occur (e.g., a review is both "promotional" and "contains PII"), use **multiple independent `predicate`s**, not a `choice`.
- If categories represent ordered steps, use a **`score`**, not a `choice`.
- If an entity belongs to an unbounded set (e.g., extracting names or order numbers), use **Structured Outputs** via Responses API, not Decisions API.

---

## 7. Rules, Reasons, and Counter-Examples

| Rule | Reason | Counter-Example (Anti-Pattern) |
|---|---|---|
| **Never use `choice` for multi-label tagging** | A `choice` forces the model to distribute probability mass across mutually exclusive buckets, obscuring co-occurring tags. | Asking a `choice` between `"spam"`, `"toxic"`, and `"profanity"`. If a post is both toxic and profanity, one tag loses its probability mass. |
| **Never use a two-option `choice` for yes/no** | A `choice` with `["yes", "no"]` costs more tokens, requires boilerplate parsing, and complicates threshold tuning. Use a `predicate`. | Creating a `choice` question: `"Is this claim fraudulent?"` with options `[{"value": "yes"}, {"value": "no"}]`. |
| **Always place escape options at the end of `choices`** | Options listed first can act as unintended attractors; keeping escapes at the end clarifies the primary taxonomy. | Choice list: `[{"value": "other"}, {"value": "billing"}, {"value": "shipping"}]`. |
| **Always check for bimodal spread in `score` questions** | Averaging bimodal extremes produces a deceptive middle score that masks critical risk. | Escalating tickets only when `score >= 3.0`, allowing a ticket with `[0.5, 0, 0, 0, 0.5]` (score 2.0) to pass unreviewed. |
