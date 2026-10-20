"""Experiment 4: Token Cost Regression Analysis."""

from typing import Any

def run_question_cost_experiment(client: Any, sample_text: str) -> dict[str, Any]:
    question_template = {
        "type": "choice",
        "name": "topic",
        "instructions": "Which team handles this customer request?",
        "choices": [
            {"value": "billing", "description": "Payments, card errors, invoices, refunds."},
            {"value": "tech", "description": "Software bugs, unexpected errors, API timeouts."},
            {"value": "shipping", "description": "Package tracking, deliveries, carrier delays."},
            {"value": "other", "description": "General topics fitting none of the above."},
        ]
    }

    ks = (1, 2, 4, 8)
    measured = []
    for k in ks:
        questions = [dict(question_template, name=f"topic_{i}") for i in range(k)]
        resp = client.create_decision(model="gpt-6-luna", input_payload=sample_text, questions=questions)
        measured.append((k, resp.usage.input_tokens))

    # Linear regression
    n = len(measured)
    sum_k = sum(m[0] for m in measured)
    sum_t = sum(m[1] for m in measured)
    sum_kt = sum(m[0] * m[1] for m in measured)
    sum_k2 = sum(m[0] ** 2 for m in measured)

    denom = (n * sum_k2 - sum_k ** 2)
    per_q = (n * sum_kt - sum_k * sum_t) / denom if denom != 0 else 0.0
    shared = (sum_t - per_q * sum_k) / n

    return {
        "measured_points": measured,
        "per_question_tokens": round(per_q, 2),
        "shared_tokens": round(shared, 2),
    }

if __name__ == "__main__":
    import sys, os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from runtime import FakeDecisionsClient
    client = FakeDecisionsClient()
    res = run_question_cost_experiment(client, "I need help with my monthly invoice payment.")
    print("Cost regression results:", res)
