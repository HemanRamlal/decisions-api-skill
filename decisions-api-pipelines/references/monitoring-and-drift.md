# Monitoring & Drift Tracking: Datasets, Gates, Replays & Runbooks

## Contents
1. [The Four Evaluation Set Splits](#1-the-four-evaluation-set-splits)
2. [Candidate Acceptance Gate Rules](#2-candidate-acceptance-gate-rules)
3. [The Paired Bootstrap Test for Cost Differences](#3-the-paired-bootstrap-test-for-cost-differences)
4. [Behavior Fingerprinting & Probe Replay Sets](#4-behavior-fingerprinting--probe-replay-sets)
5. [Distribution Drift: Population Stability Index (PSI)](#5-distribution-drift-population-stability-index-psi)
6. [Concept Drift: Weekly Human Audits](#6-concept-drift-weekly-human-audits)
7. [The Operational Drift Runbook](#7-the-operational-drift-runbook)
8. [Rules, Reasons, and Counter-Examples](#8-rules-reasons-and-counter-examples)

---

## 1. The Four Evaluation Set Splits

An evaluation suite for the Decisions API must be maintained as a version-controlled asset comprising four distinct splits:

1. **Random Production Sample (with weights)**:
   - Drawn randomly from live production traffic.
   - Preserves real-world base rates and class prevalence.
   - Each item carries an importance weight $w_i$ to allow unbiased estimation of production metrics.
2. **Oversamples of Rare Classes & Borderline Cases**:
   - Enriched sample targeting ambiguous examples near decision boundaries (e.g., $p \in [0.40, 0.60]$).
   - Essential for statistically certifying error rates in automated action zones without requiring millions of random draws.
3. **Hard Adversarial Set**:
   - Inputs engineered to break the pipeline: prompt injection overrides, fake delimiters (`<</REVIEW>>`), text rendered into images, split-payload conversation attacks, mixed-language text, and empty inputs.
   - Assesses pipeline robustness against malicious manipulation.
4. **Regression Set**:
   - Every historical production failure, false positive incident, or customer escalation, added to the test suite the day it occurs.
   - Prevents regressions when rephrasing questions or tweaking thresholds.

---

## 2. Candidate Acceptance Gate Rules

Never deploy a modified pipeline (rephrased questions, new choices, updated thresholds) without evaluating against a frozen baseline test set:

```python
def gate(base_results: dict, cand_results: dict, rules: dict) -> tuple[bool, list[str]]:
    """
    Evaluates candidate pipeline against baseline on frozen test split.
    Returns (passed, list_of_failure_reasons).
    """
    reasons = []
    # Rule 1: Expected cost must not increase
    if cand_results["expected_cost"] > base_results["expected_cost"]:
        reasons.append(f"Expected cost increased: {cand_results['expected_cost']:.2f} > {base_results['expected_cost']:.2f}")
        
    # Rule 2: Review rate must not exceed cap
    if cand_results["review_share"] > rules.get("max_review_share", 0.25):
        reasons.append(f"Review capacity exceeded: {cand_results['review_share']:.3f} > {rules['max_review_share']}")
        
    # Rule 3: Zero regressions on hard security set
    if cand_results["hard_failures"] > 0:
        reasons.append(f"Hard set regressions detected: {cand_results['hard_failures']} failed cases")
        
    return len(reasons) == 0, reasons
```

---

## 3. The Paired Bootstrap Test for Cost Differences

Because decision costs vary widely across individual items, a simple difference in sample means can be misleading. Use paired bootstrap sampling to verify that a cost reduction is statistically significant:

```python
import numpy as np

def paired_bootstrap(costs_base: list[float], costs_cand: list[float], n_boot: int = 5000, seed: int = 42) -> float:
    """
    Returns p-value that candidate pipeline has strictly lower expected cost than baseline.
    """
    rng = np.random.default_rng(seed)
    diffs = np.array(costs_base) - np.array(costs_cand)
    n = len(diffs)
    
    boot_means = [np.mean(rng.choice(diffs, size=n, replace=True)) for _ in range(n_boot)]
    # Fraction of bootstrap samples where candidate was worse or equal
    p_value = np.mean([bm <= 0 for bm in boot_means])
    return float(p_value)
```

---

## 4. Behavior Fingerprinting & Probe Replay Sets

Because the Decisions API runs on hosted models that can be updated silently by OpenAI without changing the model string (`gpt-6-luna`), pipelines must detect upstream model drift.

### The Replay Set Pattern
- Curate a frozen set of 50–100 representative production inputs ("probe set").
- Store the recorded output probabilities and answers from the certified baseline run.
- Execute daily probe replays:
  ```python
  def run_replay(probe_items: list, questions: list[dict], baseline_answers: dict) -> bool:
      current_answers = client.decisions.create_batch(probe_items, questions)
      # Check exact match or shift within noise floor
      shifts = [abs(current_answers[i].prob - baseline_answers[i].prob) for i in range(len(probe_items))]
      if max(shifts) > 0.05:
          return False  # Upstream model behavior has shifted
      return True
  ```
- If the replay set outputs shift, `dk replay` exits with code 2, alerting engineering that upstream model behavior has changed.

---

## 5. Distribution Drift: Population Stability Index (PSI)

Track shifts in the incoming distribution of output probabilities over rolling production windows:

$$\text{PSI} = \sum_{b=1}^{B} (P_b - Q_b) \times \ln\left(\frac{P_b + \epsilon}{Q_b + \epsilon}\right)$$

where $P_b$ is the reference window proportion in bin $b$, and $Q_b$ is the current window proportion.

```python
import math

def psi(reference: list[float], current: list[float], bins: int = 10, eps: float = 1e-4) -> float:
    # Bin distributions into deciles [0.0-0.1, 0.1-0.2, ...]
    ref_counts = [0] * bins
    cur_counts = [0] * bins
    
    for v in reference:
        b = min(bins - 1, int(v * bins))
        ref_counts[b] += 1
    for v in current:
        b = min(bins - 1, int(v * bins))
        cur_counts[b] += 1
        
    p = [c / len(reference) for c in ref_counts]
    q = [c / len(current) for c in cur_counts]
    
    val = sum((p[i] - q[i]) * math.log((p[i] + eps) / (q[i] + eps)) for i in range(bins))
    return val
```

### Action Thresholds
- $\text{PSI} < 0.10$: Minimal shift; no action required.
- $0.10 \le \text{PSI} < 0.25$: Moderate shift; investigate input segments.
- $\text{PSI} \ge 0.25$: Significant population drift; audit incoming traffic and re-calibrate thresholds.

---

## 6. Concept Drift: Weekly Human Audits

Distribution metrics (PSI, replay) only detect when numbers move. They cannot detect **concept drift**—when the real-world meaning of an input changes while the model remains falsely confident.
- **Weekly Zone Audits**: Sample 100 items from each operational decision zone (Auto-Act, Auto-Pass, Human-Review) each week.
- Submit samples for blind human ground-truth labeling.
- Calculate weekly confusion matrices and error bounds.
- If true error rate in an automated zone breaches the certified bound, immediately drop that zone back to human review.

---

## 7. The Operational Drift Runbook

When probe replays fail or PSI alerts trigger, execute this 5-step runbook:

1. **Confirm**: Re-run the replay set (`dk replay --twice`) to rule out transient network glitches.
2. **Scope**: Identify which questions, segments, or customer tiers shifted. Check refusal rates and escape frequencies.
3. **Measure**: Run `dk evaluate` on the frozen test set to measure the exact business impact on expected cost and error bounds.
4. **Act**:
   - If ranking (AUROC) held but calibration shifted, re-run `dk calibrate` to recalculate $(lo, hi)$ cutoffs.
   - If ranking degraded, update question instructions and bump versions.
   - Meanwhile, fall back to degraded mode (routing all affected decisions to review).
5. **Re-baseline**: Re-certify on test data and re-baseline probe replays with `dk replay --accept`.

---

## 8. Rules, Reasons, and Counter-Examples

| Rule | Reason | Counter-Example (Anti-Pattern) |
|---|---|---|
| **Never evaluate candidates without a frozen test split** | Evaluating on shifting ad-hoc samples hides regressions and creates survivorship bias. | Testing a new question instruction on whatever 20 tickets arrived this morning. |
| **Run daily probe replays against frozen inputs** | Hosted models change without notification; probe sets detect upstream shifts instantly. | Assuming `gpt-6-luna` outputs will remain numerically identical across months. |
| **Audit automated decision zones with regular human labels** | Only human ground truth can catch confident model hallucinations or changing real-world terms. | Relying solely on PSI distribution monitoring without ever verifying true labels. |
| **Verify cost differences with paired bootstrap testing** | Outlier cases can skew simple averages, causing teams to adopt suboptimal policies. | Switching to a new prompt because its raw average cost was $0.002$ lower on 50 samples. |
