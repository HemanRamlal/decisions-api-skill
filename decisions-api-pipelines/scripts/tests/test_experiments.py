"""Unit tests verifying all open experiments offline."""

import pytest
from runtime.fake_client import FakeDecisionsClient
from experiments.caching_experiment import run_caching_experiment
from experiments.interference_experiment import run_interference_experiment
from experiments.paraphrase_experiment import run_paraphrase_experiment
from experiments.question_cost_experiment import run_question_cost_experiment
from experiments.reranking_experiment import run_reranking_experiment
from experiments.cascade_simulation import simulate_cascade_economics
from experiments.split_payload_defense import run_split_payload_test
from experiments.gateway_refusal_test import test_gateway_recovery_mechanism as run_gateway_recovery_test

def test_experiment_runners_offline():
    client = FakeDecisionsClient()

    # 1. Caching
    res1 = run_caching_experiment(client, "test contract text")
    assert "round1_tokens" in res1

    # 2. Interference
    res2 = run_interference_experiment(client, ["test item 1", "test item 2"])
    assert res2["acceptable"] is True

    # 3. Paraphrase
    res3 = run_paraphrase_experiment(client, ["test item 1"])
    assert "avg_shift" in res3

    # 4. Question cost
    res4 = run_question_cost_experiment(client, "sample input")
    assert "per_question_tokens" in res4

    # 5. Reranking
    res5 = run_reranking_experiment(client, [("query", "doc")])
    assert len(res5["predicate_probabilities"]) == 1

    # 6. Cascade simulation
    res6 = simulate_cascade_economics()
    assert len(res6) > 0

    # 7. Split payload
    res7 = run_split_payload_test(client)
    assert "multi_turn_payload_detected" in res7

    # 8. Gateway recovery
    res8 = run_gateway_recovery_test()
    assert res8["recovery_successful"] is True
