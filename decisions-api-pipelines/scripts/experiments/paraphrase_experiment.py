"""Experiment 3: Paraphrase Wording Sensitivity."""

from typing import Any

def run_paraphrase_experiment(client: Any, items: list[str]) -> dict[str, Any]:
    base_q = {
        "type": "predicate",
        "name": "is_promotional",
        "instructions": "Does the review contain promotional links, discount codes, or offers for unrelated products?"
    }
    paraphrases = [
        {"type": "predicate", "name": "is_promotional_v2", "instructions": "Does this text include affiliate links, promotional vouchers, or external product advertisements?"},
        {"type": "predicate", "name": "is_promotional_v3", "instructions": "Does the author promote external commercial websites, coupons, or third-party deals?"},
        {"type": "predicate", "name": "is_promotional_v4", "instructions": "Is there promotional advertising, affiliate codes, or external product marketing in this review?"},
    ]

    shifts = []
    for item in items:
        r_base = client.create_decision(model="gpt-6-luna", input_payload=item, questions=[base_q])
        p_base = r_base.answers[0].probability or 0.0

        for para in paraphrases:
            r_para = client.create_decision(model="gpt-6-luna", input_payload=item, questions=[para])
            p_para = r_para.answers[0].probability or 0.0
            shifts.append(abs(p_base - p_para))

    avg_shift = sum(shifts) / max(1, len(shifts)) if shifts else 0.0
    max_shift = max(shifts) if shifts else 0.0
    return {
        "avg_shift": avg_shift,
        "max_shift": max_shift,
        "is_fragile": max_shift > 0.08,
    }

if __name__ == "__main__":
    import sys, os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from runtime import FakeDecisionsClient
    client = FakeDecisionsClient()
    res = run_paraphrase_experiment(client, ["Review 1: buy at http://deals.com", "Review 2: great blender!"])
    print("Paraphrase experiment results:", res)
