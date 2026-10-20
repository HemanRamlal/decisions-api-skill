"""Module 5 snippets: Calibration sweeps, error bounds, gate rules, bootstrap, and PSI."""

import hashlib
import json
import math
import numpy as np
from scipy.stats import beta
from sklearn.metrics import roc_auc_score
from typing import Any

def compare_signals(rows: list[dict[str, float]], labels: list[int], signals: tuple[str, ...] = ("selected_probability", "confidence", "margin")) -> dict[str, float]:
    """Compares AUROC discrimination across candidate threshold signals."""
    results = {}
    for sig in signals:
        vals = [r[sig] for r in rows]
        try:
            results[sig] = float(roc_auc_score(labels, vals))
        except Exception:
            results[sig] = 0.5
    return results

def sweep_three_zone(
    scores: list[float],
    labels: list[int],
    c_fp: float,
    c_fn: float,
    c_review: float,
    weights: list[float] | None = None,
    review_cap: float = 0.20,
) -> tuple[float, float, float]:
    """
    Finds lowest cost (lo, hi) cutoffs on labeled dev data under review capacity constraint:
      - pass: score < lo
      - review: lo <= score < hi
      - act: score >= hi
    """
    n = len(scores)
    w = weights if weights is not None else [1.0] * n
    total_w = sum(w)

    best_cost = float("inf")
    best_cutoffs = (0.0, 1.0)

    unique_scores = sorted(set(scores))
    if not unique_scores:
        return (0.0, 1.0, 0.0)

    for i, lo in enumerate(unique_scores):
        for hi in unique_scores[i:]:
            # Check review share
            rev_share = sum(w[k] for k, s in enumerate(scores) if lo <= s < hi) / total_w
            if rev_share > review_cap:
                continue

            cost = 0.0
            for k, (s, y) in enumerate(zip(scores, labels)):
                weight = w[k]
                if s >= hi:
                    if y == 0: cost += weight * c_fp
                elif s < lo:
                    if y == 1: cost += weight * c_fn
                else:
                    cost += weight * c_review

            if cost < best_cost:
                best_cost = cost
                best_cutoffs = (lo, hi)

    return best_cutoffs[0], best_cutoffs[1], best_cost

def error_upper_bound(errors: int, n: int, conf: float = 0.95) -> float:
    """Exact upper bound of binomial confidence interval using Beta distribution."""
    if n == 0:
        return 1.0
    return float(beta.ppf(conf, errors + 1, n - errors))

def paired_bootstrap(cost_a: list[float], cost_b: list[float], n_boot: int = 5000, seed: int = 0) -> float:
    """Computes bootstrap p-value that pipeline B has lower expected cost than A."""
    rng = np.random.default_rng(seed)
    diffs = np.array(cost_a) - np.array(cost_b)
    n = len(diffs)
    boot_means = [np.mean(rng.choice(diffs, size=n, replace=True)) for _ in range(n_boot)]
    p_val = np.mean([bm <= 0 for bm in boot_means])
    return float(p_val)

def config_fingerprint(questions: list[dict[str, Any]], input_format: str, policy: str, sdk_version: str = "3.26.0", endpoint: str = "/v1/decisions") -> str:
    """Generates unique SHA-256 fingerprint for pipeline configuration."""
    canonical = {
        "questions": sorted([{"name": q.get("name"), "type": q.get("type"), "instructions": q.get("instructions")} for q in questions], key=lambda x: str(x.get("name"))),
        "input_format": input_format,
        "policy": policy,
        "sdk_version": sdk_version,
        "endpoint": endpoint,
    }
    raw = json.dumps(canonical, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def gate(base: dict[str, Any], cand: dict[str, Any], rules: dict[str, Any]) -> tuple[bool, list[str]]:
    """Evaluates candidate pipeline metrics against baseline on frozen test set."""
    reasons = []
    if cand.get("expected_cost", 0) > base.get("expected_cost", 0):
        reasons.append("Candidate expected cost exceeded baseline.")
    if cand.get("review_share", 0) > rules.get("max_review_share", 0.25):
        reasons.append("Review share exceeded operational capacity.")
    if cand.get("hard_failures", 0) > 0:
        reasons.append("Regression detected on hard security test set.")
    return len(reasons) == 0, reasons

def psi(reference: list[float], current: list[float], bins: int = 10, eps: float = 1e-4) -> float:
    """Calculates Population Stability Index between reference and current windows."""
    ref_counts = [0] * bins
    cur_counts = [0] * bins

    for v in reference:
        b = min(bins - 1, max(0, int(v * bins)))
        ref_counts[b] += 1
    for v in current:
        b = min(bins - 1, max(0, int(v * bins)))
        cur_counts[b] += 1

    p = [c / max(1, len(reference)) for c in ref_counts]
    q = [c / max(1, len(current)) for c in cur_counts]

    total_psi = sum((p[i] - q[i]) * math.log((p[i] + eps) / (q[i] + eps)) for i in range(bins))
    return float(total_psi)
