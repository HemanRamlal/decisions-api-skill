"""Experiment 1: Prompt Caching Behavior."""

import time
from typing import Any

def run_caching_experiment(client: Any, doc_text: str) -> dict[str, Any]:
    """
    Executes 2-round caching experiment over byte-identical contract document.
    Measures cached_tokens, latency, and determinism.
    """
    stage1_questions = [
        {"type": "predicate", "name": "has_auto_renewal", "instructions": "Does the document contain an auto-renewal clause?"}
    ]
    stage2_questions = [
        {"type": "predicate", "name": "has_indemnity", "instructions": "Does the document contain an indemnity clause?"}
    ]

    # Round 1
    t0 = time.time()
    r1 = client.create_decision(model="gpt-6-luna", input_payload=doc_text, questions=stage1_questions)
    lat1 = time.time() - t0

    u1 = r1.usage
    cached1 = getattr(u1.input_tokens_details, "cached_tokens", 0)

    # Round 2: same input bytes
    t1 = time.time()
    r2 = client.create_decision(model="gpt-6-luna", input_payload=doc_text, questions=stage2_questions)
    lat2 = time.time() - t1

    u2 = r2.usage
    cached2 = getattr(u2.input_tokens_details, "cached_tokens", 0)

    return {
        "round1_tokens": u1.input_tokens,
        "round1_cached": cached1,
        "round1_latency": lat1,
        "round2_tokens": u2.input_tokens,
        "round2_cached": cached2,
        "round2_latency": lat2,
        "cache_reused": cached2 > 0,
        "latency_delta": lat1 - lat2,
    }

if __name__ == "__main__":
    import sys, os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from runtime import FakeDecisionsClient
    client = FakeDecisionsClient()
    res = run_caching_experiment(client, "SAMPLE CONTRACT TEXT " * 500)
    print("Caching experiment results:", res)
