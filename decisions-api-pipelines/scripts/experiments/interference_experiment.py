"""Experiment 2: Question Batching Interference."""

from typing import Any

def run_interference_experiment(client: Any, items: list[str]) -> dict[str, Any]:
    target_q = {
        "type": "predicate",
        "name": "is_urgent",
        "instructions": "Does the customer state that the system is completely unavailable right now?"
    }
    distractor_qs = [
        {"type": "predicate", "name": f"distractor_{i}", "instructions": f"Does the text mention topic #{i}?"}
        for i in range(10)
    ]

    shifts = []
    for item in items:
        r_alone = client.create_decision(model="gpt-6-luna", input_payload=item, questions=[target_q])
        p_alone = r_alone.answers[0].probability or 0.0

        r_batched = client.create_decision(model="gpt-6-luna", input_payload=item, questions=[target_q] + distractor_qs)
        p_batched = r_batched.answers[0].probability or 0.0
        shifts.append(abs(p_alone - p_batched))

    max_shift = max(shifts) if shifts else 0.0
    return {
        "max_shift": max_shift,
        "mean_shift": sum(shifts) / max(1, len(shifts)),
        "acceptable": max_shift <= 0.05,
    }

if __name__ == "__main__":
    import sys, os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from runtime import FakeDecisionsClient
    client = FakeDecisionsClient()
    res = run_interference_experiment(client, ["Ticket 1", "Ticket 2", "Ticket 3"])
    print("Interference experiment results:", res)
