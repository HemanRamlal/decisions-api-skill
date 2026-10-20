# Open Experiments: Empirical Protocols & Test Scripts

## Contents
1. [Overview of Open Empirical Experiments](#1-overview-of-open-empirical-experiments)
2. [Experiment 1: Prompt Caching Behavior](#2-experiment-1-prompt-caching-behavior)
3. [Experiment 2: Question Batching Interference](#3-experiment-2-question-batching-interference)
4. [Experiment 3: Paraphrase Wording Sensitivity](#4-experiment-3-paraphrase-wording-sensitivity)
5. [Experiment 4: Token Cost Regression Analysis](#5-experiment-4-token-cost-regression-analysis)
6. [Experiment 5: Predicate vs. Score Reranking](#6-experiment-5-predicate-vs-score-reranking)
7. [Experiment 6: Cascade vs. Batch Cost Simulation](#7-experiment-6-cascade-vs-batch-cost-simulation)
8. [Experiment 7: Multi-Turn Split-Payload Defense](#8-experiment-7-multi-turn-split-payload-defense)
9. [Experiment 8: Gateway Refusal Recovery](#8-experiment-8-gateway-refusal-recovery)

---

## 1. Overview of Open Empirical Experiments
Several aspects of the Decisions API involve undocumented, volatile, or model-dependent behaviors. Rather than relying on guesswork, the skill maintains dedicated runnable Python scripts in `scripts/experiments/` to verify these properties empirically against the live API.

---

## 2. Experiment 1: Prompt Caching Behavior
- **Script**: `scripts/experiments/caching_experiment.py`
- **Question**: Does resending the exact same document prefix within 30 minutes reduce latency or billed tokens on the Decisions API endpoint?
- **Protocol**:
  1. Load a 6,000-token contract document.
  2. Round 1: Send request with Stage 1 questions and optional cache breakpoint parameters.
  3. Round 2: Within 30 minutes, send Stage 2 questions with identical input bytes.
  4. Measure: `usage.input_tokens_details.cached_tokens`, actual billed usage, latency difference, and answer determinism.
- **Status as of 2026-10-21**: Request schema dropped explicit caching parameters; script tests whether automatic prefix caching occurs or if passing parameters via `extra_body` is accepted [documented].

---

## 3. Experiment 2: Question Batching Interference
- **Script**: `scripts/experiments/interference_experiment.py`
- **Question**: Does adding unrelated questions into a single request shift the target question's probability?
- **Protocol**:
  1. Select a validation set of 100 items.
  2. Measure target question probability $p_{\text{alone}}$ in isolation.
  3. Measure target question probability $p_{\text{batched}}$ when co-located with 5, 10, and 20 distractors.
  4. Compute $\Delta p = |p_{\text{alone}} - p_{\text{batched}}|$. Flag if $\max(\Delta p) > 0.05$.

---

## 4. Experiment 3: Paraphrase Wording Sensitivity
- **Script**: `scripts/experiments/paraphrase_experiment.py`
- **Question**: Is model uncertainty caused by ambiguous evidence or brittle instruction phrasing?
- **Protocol**:
  1. Generate 4 semantic paraphrases of a question instruction.
  2. Evaluate all paraphrases over the evaluation set.
  3. Measure inter-paraphrase variance: if identical items yield high probability swings ($>0.10$), rewrite the instruction with more observable factual criteria.

---

## 5. Experiment 4: Token Cost Regression Analysis
- **Script**: `scripts/experiments/question_cost_experiment.py`
- **Question**: What is the exact fixed request overhead and marginal per-question token cost?
- **Protocol**:
  1. Evaluate an identical input with $k \in \{1, 2, 4, 8, 16\}$ duplicate copies of a question.
  2. Fit a linear regression line: $\text{Tokens}(k) = \text{Shared} + k \times \text{Cost}_{\text{question}}$.
  3. Extract empirical base overhead and marginal question cost.

---

## 6. Experiment 5: Predicate vs. Score Reranking
- **Script**: `scripts/experiments/reranking_experiment.py`
- **Question**: Do ordered `score` rubrics outperform binary `predicate` questions for document retrieval/reranking?
- **Background**: Adrian Raudaschl's benchmark on 200 NFCorpus queries showed that binary predicates suffered from coarse probability saturation (documents clustering at 0.0 or 1.0), whereas a 4-level relevance `score` primitive produced fine-grained ranking with higher NDCG.
- **Protocol**: Evaluates search query relevance using both primitives and computes Kendall's tau correlation against ground-truth human relevance.

---

## 7. Experiment 6: Cascade vs. Batch Cost Simulation
- **Script**: `scripts/experiments/cascade_simulation.py`
- **Question**: At what gate pass rate $p_{\text{gate}}$ does a 2-stage cascade become cheaper than batching?
- **Protocol**: Runs a parametric sweep across document sizes ($1\text{k}$ to $50\text{k}$ tokens) and gating frequencies ($0.01$ to $0.50$) to produce an optimal architectural boundary curve.

---

## 8. Experiment 7: Multi-Turn Split-Payload Defense
- **Script**: `scripts/experiments/split_payload_defense.py`
- **Question**: Can an adversarial injection split across 3 turns evade a single-turn guardrail, and does a 6-turn sliding window with a `defines_payload` predicate neutralize it?
- **Protocol**: Executes a simulated multi-turn injection attack; verifies that the multi-turn guard detects the payload while single-turn fails.

---

## 9. Experiment 8: Gateway Refusal Recovery
- **Script**: `scripts/experiments/gateway_refusal_test.py`
- **Question**: When a gateway wraps a refusal in an HTTP 502 error, can the client cleanly recover the unrefused questions?
- **Protocol**: Simulates a 502 gateway error body containing `refused to answer question "X"`. Verifies regex extraction and retry recovery of remaining questions.
