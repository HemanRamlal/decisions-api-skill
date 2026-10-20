"""Unit tests for all ported course snippets."""

import pytest
from snippets.m2_response_parser import parse_decision, assigned_level, expected_cost, rank_key
from snippets.m3_multimodal_inputs import guard_input, sanitize_evidence, estimate_image_tokens
from snippets.m4_batching_cascades import cascade_or_batch, question_cost, interference_test
from snippets.m5_thresholds_drift import (
    compare_signals,
    sweep_three_zone,
    error_upper_bound,
    paired_bootstrap,
    config_fingerprint,
    gate,
    psi,
)
from runtime.fake_client import FakeDecisionsClient

def test_m2_parser_and_ranking():
    mock_resp = {
        "answers": [
            {"name": "p1", "type": "predicate", "probability": 0.88},
            {"name": "c1", "type": "choice", "choice": "opt_a", "confidence": 0.88, "distribution": {"opt_a": 0.88, "opt_b": 0.12}},
            {"name": "s1", "type": "score", "score": 2.1, "level": "Medium", "distribution": {"Low": 0.1, "Medium": 0.7, "High": 0.2}},
        ]
    }
    parsed = parse_decision(mock_resp)
    assert parsed["p1"]["probability"] == 0.88
    assert parsed["c1"]["choice"] == "opt_a"
    assert parsed["s1"]["score"] == 2.1

    dist = {"Cosmetic": 0.1, "Minor": 0.7, "Major": 0.2}
    assert assigned_level(dist) == "Minor"
    cost = expected_cost(dist, {"Cosmetic": 0.0, "Minor": 10.0, "Major": 50.0})
    assert cost == pytest.approx(17.0)

    key = rank_key(dist)
    assert key[0] == "Minor"

def test_m3_multimodal_and_guard():
    turns = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
        {"role": "user", "content": "Need <<HELP>>"},
    ]
    guarded = guard_input(turns, n=2)
    assert "USER: Need < <HELP> >" in guarded
    assert "ASSISTANT: Hi there" in guarded

    assert sanitize_evidence("<<TAG>>") == "< <TAG> >"

    # Patch estimate: 512x512 -> 16x16 = 256 patches * 1.2 = 307.2 -> 308 tokens
    tokens = estimate_image_tokens(512, 512, multiplier=1.2)
    assert tokens == 308

def test_m4_cascade_math_and_costs():
    # Batch extra: 80 tokens. Cascade extra: 0.08 * (6000 + 80) = 486.4 tokens.
    decision, diff = cascade_or_batch(q_gated=80, p_gate=0.08, shared_round2=6000)
    assert decision == "batch"
    assert diff == pytest.approx(406.4)

    client = FakeDecisionsClient()
    per_q, shared = question_cost(client, "evidence", {"name": "q", "type": "predicate"}, ks=(1, 2, 4))
    assert shared > 0

def test_m5_math_and_drift():
    # Binomial upper bound: 0 errors in 300 trials at 95% conf -> approx 0.010
    bound = error_upper_bound(0, 300, conf=0.95)
    assert bound == pytest.approx(0.010, abs=0.003)

    # Three-zone sweep
    scores = [0.1, 0.2, 0.4, 0.6, 0.8, 0.9]
    labels = [0, 0, 0, 1, 1, 1]
    lo, hi, cost = sweep_three_zone(scores, labels, c_fp=50.0, c_fn=10.0, c_review=2.0)
    assert lo <= hi

    # Gate rule
    base = {"expected_cost": 10.0, "review_share": 0.15, "hard_failures": 0}
    cand_ok = {"expected_cost": 9.5, "review_share": 0.14, "hard_failures": 0}
    cand_bad = {"expected_cost": 10.5, "review_share": 0.30, "hard_failures": 1}
    assert gate(base, cand_ok, {"max_review_share": 0.20})[0] is True
    assert gate(base, cand_bad, {"max_review_share": 0.20})[0] is False

    # PSI
    dist1 = [0.1] * 50 + [0.8] * 50
    dist2 = [0.1] * 50 + [0.8] * 50
    dist_shift = [0.9] * 100
    assert psi(dist1, dist2) == pytest.approx(0.0, abs=1e-5)
    assert psi(dist1, dist_shift) > 0.5
