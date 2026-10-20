"""Module 3 snippets: Evidence boundaries, sliding windows, and image token math."""

import math
from typing import Any

def guard_input(turns: list[dict[str, str]], n: int = 6) -> str:
    """
    Constructs a sliding window of recent conversation turns with speaker labels.
    Prevents single-turn evasion in split-payload attacks.
    """
    recent = turns[-n:]
    formatted = []
    for t in recent:
        role = t.get("role", "user").upper()
        content = t.get("content", "").replace("<<", "< <").replace(">>", "> >")
        formatted.append(f"{role}: {content}")
    return "\n".join(formatted)

def sanitize_evidence(raw_text: str) -> str:
    """Escapes pseudo-XML delimiter tokens."""
    return raw_text.replace("<<", "< <").replace(">>", "> >")

def estimate_image_tokens(width: int, height: int, multiplier: float = 1.2) -> int:
    """
    Deterministic pre-flight image token estimator based on 32x32 patch grid.
    """
    patches_w = math.ceil(width / 32)
    patches_h = math.ceil(height / 32)
    return math.ceil((patches_w * patches_h) * multiplier)

def paraphrase_test(client: Any, items: list[str], base_q: dict[str, Any], paraphrases: list[dict[str, Any]], threshold: float = 0.05) -> dict[str, Any]:
    """
    Measures instruction wording sensitivity across semantic variants.
    """
    shifts = []
    for item in items:
        # Base probability
        r_base = client.create_decision(model="gpt-6-luna", input_payload=item, questions=[base_q])
        p_base = r_base.answers[0].probability or 0.0
        for para in paraphrases:
            r_para = client.create_decision(model="gpt-6-luna", input_payload=item, questions=[para])
            p_para = r_para.answers[0].probability or 0.0
            shifts.append(abs(p_base - p_para))

    avg_shift = sum(shifts) / max(1, len(shifts))
    max_shift = max(shifts) if shifts else 0.0
    return {
        "avg_shift": avg_shift,
        "max_shift": max_shift,
        "is_fragile": max_shift > threshold,
    }
