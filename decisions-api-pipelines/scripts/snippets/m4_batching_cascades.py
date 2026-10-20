"""Module 4 snippets: Batching economics, interference tests, and cascade simulation."""

from typing import Any

def question_cost(client: Any, input_payload: str, question: dict[str, Any], ks: tuple[int, ...] = (1, 2, 4, 8)) -> tuple[float, float]:
    """
    Measures fixed overhead vs per-question token cost via linear regression.
    Returns (per_question_tokens, shared_tokens).
    """
    measured: list[tuple[int, int]] = []
    for k in ks:
        # Create k copies with unique names
        qs = [dict(question, name=f"{question['name']}_{i}") for i in range(k)]
        resp = client.create_decision(model="gpt-6-luna", input_payload=input_payload, questions=qs)
        measured.append((k, resp.usage.input_tokens))

    # Simple linear fit (Tokens = shared + k * per_q)
    n = len(measured)
    sum_k = sum(m[0] for m in measured)
    sum_t = sum(m[1] for m in measured)
    sum_kt = sum(m[0] * m[1] for m in measured)
    sum_k2 = sum(m[0] ** 2 for m in measured)

    denom = (n * sum_k2 - sum_k ** 2)
    per_q = (n * sum_kt - sum_k * sum_t) / denom if denom != 0 else 0.0
    shared = (sum_t - per_q * sum_k) / n
    return per_q, shared

def interference_test(client: Any, items: list[str], target: dict[str, Any], others: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Evaluates whether adding distractor questions alters the target question's probability.
    """
    shifts = []
    for item in items:
        r_alone = client.create_decision(model="gpt-6-luna", input_payload=item, questions=[target])
        p_alone = r_alone.answers[0].probability or 0.0

        r_batched = client.create_decision(model="gpt-6-luna", input_payload=item, questions=[target] + others)
        p_batched = r_batched.answers[0].probability or 0.0
        shifts.append(abs(p_alone - p_batched))

    max_shift = max(shifts) if shifts else 0.0
    share_shifted = sum(s > 0.02 for s in shifts) / max(1, len(shifts))
    return {"max_shift": max_shift, "share_shifted": share_shifted}

def cascade_or_batch(q_gated: int, p_gate: float, shared_round2: int, detail_surcharge: int = 0) -> tuple[str, float]:
    """
    Compares the expected extra cost of batching vs. cascading a relevance dependency.
    """
    batch_extra = q_gated + detail_surcharge
    cascade_extra = p_gate * (shared_round2 + q_gated)
    decision = "cascade" if cascade_extra < batch_extra else "batch"
    diff = abs(batch_extra - cascade_extra)
    return decision, diff
