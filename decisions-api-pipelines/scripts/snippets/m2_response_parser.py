"""Module 2 snippets: Defensive parsing and score ranking."""

import math
from typing import Any

def parse_decision(resp: Any) -> dict[str, Any]:
    """
    Topic 2 defensive parser with two-decimal rounding tolerance.
    Keeps original names from course transcripts.
    """
    answers = resp.answers if hasattr(resp, "answers") else resp.get("answers", [])
    parsed = {}
    for a in answers:
        name = a.name if hasattr(a, "name") else a.get("name")
        ans_type = a.type if hasattr(a, "type") else a.get("type")

        if ans_type == "refusal":
            parsed[name] = {"type": "refusal", "name": name}
            continue

        if ans_type == "predicate":
            prob = a.probability if hasattr(a, "probability") else a.get("probability")
            parsed[name] = {"type": "predicate", "probability": float(prob)}

        elif ans_type == "choice":
            choice_val = a.choice if hasattr(a, "choice") else a.get("choice")
            conf = a.confidence if hasattr(a, "confidence") else a.get("confidence")
            dist = a.distribution if hasattr(a, "distribution") else a.get("distribution")
            tol = 0.005 * len(dist) + 1e-9
            if abs(sum(dist.values()) - 1.0) > tol:
                raise ValueError(f"Distribution sum outside tolerance: {sum(dist.values())}")
            parsed[name] = {
                "type": "choice",
                "choice": choice_val,
                "confidence": float(conf) if conf is not None else float(dist[choice_val]),
                "distribution": {k: float(v) for k, v in dist.items()},
            }

        elif ans_type == "score":
            score_val = a.score if hasattr(a, "score") else a.get("score")
            lvl = a.level if hasattr(a, "level") else a.get("level")
            dist = a.distribution if hasattr(a, "distribution") else a.get("distribution")
            tol = 0.005 * len(dist) + 1e-9
            if abs(sum(dist.values()) - 1.0) > tol:
                raise ValueError(f"Score distribution sum outside tolerance: {sum(dist.values())}")
            parsed[name] = {
                "type": "score",
                "score": float(score_val),
                "level": lvl,
                "distribution": {k: float(v) for k, v in dist.items()},
            }
    return parsed

def assigned_level(dist: dict[str, float]) -> str:
    """Returns the argmax level from a distribution."""
    return max(dist.items(), key=lambda x: x[1])[0]

def expected_cost(dist: dict[str, float], cost_per_level: dict[str, float] | None = None) -> float:
    """Calculates continuous expected cost from score distribution."""
    if cost_per_level is None:
        # Default unit indexing 0, 1, 2...
        return sum(i * p for i, (lbl, p) in enumerate(dist.items()))
    return sum(cost_per_level.get(lbl, 0.0) * p for lbl, p in dist.items())

def rank_key(dist: dict[str, float], cost_per_level: dict[str, float] | None = None) -> tuple[str, float]:
    """Coarse level first, continuous expected cost second to break ties."""
    return (assigned_level(dist), expected_cost(dist, cost_per_level))
