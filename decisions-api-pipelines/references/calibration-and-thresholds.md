# Calibration & Thresholds: Cost Sweeps, Certification & Review Bands

## Contents
1. [Discrimination (AUROC) vs. Calibration (ECE)](#1-discrimination-auroc-vs-calibration-ece)
2. [Selecting the Decision Signal](#2-selecting-the-decision-signal)
3. [Deriving Cutoffs from Business Error Costs](#3-deriving-cutoffs-from-business-error-costs)
4. [The Empirical Three-Zone Sweep](#4-the-empirical-three-zone-sweep)
5. [The Base Rate & Precision Trap](#5-the-base-rate--precision-trap)
6. [Sample Size Certification: Rule of Three & Binomial Bounds](#6-sample-size-certification-rule-of-three--binomial-bounds)
7. [Recalibration in Code](#7-recalibration-in-code)
8. [Threshold Specifications & Auto-Expiration](#8-threshold-specifications--auto-expiration)
9. [Rules, Reasons, and Counter-Examples](#9-rules-reasons-and-counter-examples)

---

## 1. Discrimination (AUROC) vs. Calibration (ECE)

A model output can be evaluated along two completely distinct axes:

- **Discrimination (Ranking / AUROC)**: Do positive/correct cases consistently receive higher probability values than negative/incorrect cases?
  - Measured via Area Under the ROC Curve (AUROC). An AUROC of $0.5$ is pure random guessing; $1.0$ is perfect separation.
  - *Key Property*: Monotonic transformations preserve AUROC. If ranking is high, an empirical threshold cutoff can separate decisions cleanly even if the raw numbers are uncalibrated.
- **Calibration (Expected Calibration Error / ECE)**: Does a stated probability of $0.80$ correspond to an empirical true frequency of $80\%$ in the real world?
  - Decisions API raw probabilities are frequently uncalibrated out of the box [documented].
  - Setting thresholds by theoretical formulas assuming $p$ is an exact frequency will fail unless the signal is empirically calibrated.

---

## 2. Selecting the Decision Signal

For `choice` questions, multiple signals are available for thresholding:
1. `selected_probability`: The probability of the argmax choice.
2. `confidence`: The raw confidence score returned by the API.
3. `margin`: The difference between the top choice and runner-up: $p_{\text{top}} - p_{\text{runner\_up}}$.

### Selection Rule
Always measure AUROC across all three candidate signals on labeled validation data:
```python
from sklearn.metrics import roc_auc_score

def compare_signals(rows, labels):
    for sig in ("selected_probability", "confidence", "margin"):
        score = roc_auc_score(labels, [r[sig] for r in rows])
        print(f"AUROC for {sig}: {score:.4f}")
```
Choose the signal with the highest AUROC. Margin frequently outperforms raw probability when disambiguating closely competing categories.

---

## 3. Deriving Cutoffs from Business Error Costs

When probabilities *are* calibrated, optimal decision cutoffs are derived from the relative business costs of errors:
- $C_{\text{FP}}$: Cost of a False Positive (e.g. wrongly banning a legitimate user).
- $C_{\text{FN}}$: Cost of a False Negative (e.g. allowing toxic spam to be published).
- $C_R$: Cost of Human Review.

Under expected cost minimization, the theoretical decision policy is:
- **Pass (Auto-Approve)**: when $p < \frac{C_R}{C_{\text{FN}}}$
- **Act (Auto-Flag / Sanction)**: when $p > 1 - \frac{C_R}{C_{\text{FP}}}$
- **Review (Human Queue)**: when $\frac{C_R}{C_{\text{FN}}} \le p \le 1 - \frac{C_R}{C_{\text{FP}}}$

---

## 4. The Empirical Three-Zone Sweep

Because raw probabilities are rarely perfectly calibrated, use an empirical grid sweep over labeled development data (`sweep_three_zone`). This optimizes cutoffs $(lo, hi)$ directly against expected business cost under human review capacity constraints:

```python
def sweep_three_zone(scores: list[float], labels: list[int],
                     c_fp: float, c_fn: float, c_review: float,
                     weights: list[float] | None = None,
                     review_cap: float = 0.20) -> tuple[float, float, float]:
    """
    Finds (lo, hi) cutoffs that minimize total expected cost on dev data:
      - pass: score < lo
      - review: lo <= score < hi
      - act: score >= hi
    Constraint: fraction routed to review must be <= review_cap.
    """
    n = len(scores)
    w = weights if weights is not None else [1.0] * n
    total_w = sum(w)
    
    best_cost = float("inf")
    best_cutoffs = (0.0, 1.0)
    
    unique_scores = sorted(set(scores))
    for i, lo in enumerate(unique_scores):
        for hi in unique_scores[i:]:
            # Calculate review fraction
            review_share = sum(w[k] for k, s in enumerate(scores) if lo <= s < hi) / total_w
            if review_share > review_cap:
                continue
                
            # Compute empirical error costs
            cost = 0.0
            for k, (s, y) in enumerate(zip(scores, labels)):
                weight = w[k]
                if s >= hi: # Act
                    if y == 0: cost += weight * c_fp
                elif s < lo: # Pass
                    if y == 1: cost += weight * c_fn
                else: # Review
                    cost += weight * c_review
                    
            if cost < best_cost:
                best_cost = cost
                best_cutoffs = (lo, hi)
                
    return best_cutoffs[0], best_cutoffs[1], best_cost
```

---

## 5. The Base Rate & Precision Trap

Evaluating accuracy on a balanced development set (50% positive, 50% negative) creates a dangerous illusion of precision when deployed to production with low base rates:

### The Mathematical Trap
Assume a spam classifier has $95\%$ sensitivity and $95\%$ specificity on a balanced dev set:
- In production, the actual base rate of spam is $1\%$ ($1{,}000$ spam in $100{,}000$ messages).
- True Positives: $1{,}000 \times 0.95 = 950$.
- False Positives: $99{,}000 \times (1 - 0.95) = 4{,}950$.
- **Real-World Precision**: $\frac{950}{950 + 4{,}950} = \frac{950}{5{,}900} \approx 16.1\%$.

Over $83\%$ of auto-flagged items in production will be false positives!
- **Guidance**: Always re-weight dev sets back to real production base rates using importance weighting ($w_i$).

---

## 6. Sample Size Certification: Rule of Three & Binomial Bounds

A subset of dev data with zero observed errors does not prove zero risk:

### The Rule of Three
If $N$ items in an automated zone are tested and zero errors are observed, the 95% confidence upper bound on the true error rate is:
$$\text{Error Upper Bound} \approx \frac{3}{N}$$
- To certify that an automated zone has an error rate $< 1\%$ with 95% confidence, you must evaluate at least $N = \frac{3}{0.01} = 300$ error-free samples in that zone.

### Exact Binomial Bound (Clopper-Pearson / Beta)
For $k$ observed errors in $N$ samples at confidence level $\alpha=0.95$:
```python
from scipy.stats import beta

def error_upper_bound(errors: int, n: int, conf: float = 0.95) -> float:
    """Exact upper bound of binomial confidence interval."""
    if n == 0:
        return 1.0
    return float(beta.ppf(conf, errors + 1, n - errors))
```

---

## 7. Recalibration in Code
When a probability must directly represent a true physical frequency (e.g., when passing to an external actuarial risk model):
- Fit an **Isotonic Regression** model on labeled dev probabilities:
  ```python
  from sklearn.isotonic import IsotonicRegression
  calibrator = IsotonicRegression(out_of_bounds="clip")
  calibrator.fit(dev_scores, dev_labels)
  calibrated_p = calibrator.predict([raw_p])[0]
  ```
- *Note*: If the goal is simply routing items into discrete operational queues, the empirical three-zone sweep is preferred because it requires no distribution assumptions.

---

## 8. Threshold Specifications & Auto-Expiration

Never hardcode magic floating-point thresholds in application code. Store them in versioned `ThresholdSpec` objects:

```python
from dataclasses import dataclass
import time

@dataclass(frozen=True)
class ThresholdSpec:
    pipeline: str
    target_question: str
    signal: str
    lo: float
    hi: float
    c_fp: float
    c_fn: float
    c_review: float
    fingerprint: str
    certified_error_bound: float
    created_at: float
    ttl_seconds: float = 30 * 86400  # 30 days

    def is_valid(self, current_fingerprint: str) -> bool:
        if self.fingerprint != current_fingerprint:
            return False  # Configuration or model drift detected
        if time.time() > self.created_at + self.ttl_seconds:
            return False  # Spec expired
        return True
```

If a spec expires or the configuration fingerprint shifts, the pipeline falls back to **shadow mode**: all automated decisions route to human review until recalibrated.

---

## 9. Rules, Reasons, and Counter-Examples

| Rule | Reason | Counter-Example (Anti-Pattern) |
|---|---|---|
| **Never hardcode uncalibrated thresholds from intuition** | Intuitive cutoffs ($0.85$, $0.90$) bear no relationship to real false-positive costs or model calibration. | Setting `if p > 0.85: ban_user()` without empirical error cost modeling. |
| **Always adjust dev set metrics for production base rates** | Balanced dev sets dramatically inflate apparent precision when production prevalence is low. | Deploying an abuse classifier that had 98% precision on balanced data, only to find 80% false positives in production. |
| **Certify zone error bounds with binomial confidence intervals** | Observing 0 errors on 15 samples leaves a true error rate as high as 18% ($3/15$). | Claiming an automated route is 100% accurate because the last 20 test cases succeeded. |
| **Auto-expire threshold specs on pipeline configuration changes** | Modifying question wording or model versions silently invalidates calibrated cutoffs. | Changing question instructions from v1 to v2 while leaving old numeric thresholds active. |
