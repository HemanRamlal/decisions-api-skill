"""Defensive response parser with two-decimal rounding tolerance."""

from typing import Any

class ContractViolationError(Exception):
    """Raised when an API response violates protocol contract."""

def parse_decision_response(raw_resp: Any, expected_questions: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Parses and defensively validates a decision response object or dict.
    Returns a dictionary mapping question name to parsed answer object/dict.
    """
    if hasattr(raw_resp, "answers"):
        answers = raw_resp.answers
    elif isinstance(raw_resp, dict) and "answers" in raw_resp:
        answers = raw_resp["answers"]
    else:
        raise ContractViolationError("Response envelope missing 'answers' field.")

    parsed: dict[str, Any] = {}
    for a in answers:
        name = getattr(a, "name", None) or (a.get("name") if isinstance(a, dict) else None)
        ans_type = getattr(a, "type", None) or (a.get("type") if isinstance(a, dict) else None)
        if not name:
            raise ContractViolationError("Encountered answer missing required 'name' field.")

        if ans_type == "refusal":
            parsed[name] = {"type": "refusal", "name": name}
            continue

        if ans_type == "predicate":
            prob = getattr(a, "probability", None) if not isinstance(a, dict) else a.get("probability")
            if prob is None or not (0.0 <= prob <= 1.0):
                raise ContractViolationError(f"Predicate '{name}' missing valid probability: {prob}")
            parsed[name] = {"type": "predicate", "name": name, "probability": float(prob)}

        elif ans_type == "choice":
            choice_val = getattr(a, "choice", None) if not isinstance(a, dict) else a.get("choice")
            conf = getattr(a, "confidence", None) if not isinstance(a, dict) else a.get("confidence")
            dist = getattr(a, "distribution", None) if not isinstance(a, dict) else a.get("distribution")
            if not choice_val or dist is None:
                raise ContractViolationError(f"Choice '{name}' missing choice value or distribution.")

            # Validate distribution sum with two-decimal rounding tolerance
            tol = 0.005 * len(dist) + 1e-9
            dist_sum = sum(dist.values())
            if abs(dist_sum - 1.0) > tol:
                raise ContractViolationError(f"Choice '{name}' distribution sum {dist_sum:.4f} outside tolerance {tol:.4f}")

            parsed[name] = {
                "type": "choice",
                "name": name,
                "choice": choice_val,
                "confidence": float(conf) if conf is not None else float(dist[choice_val]),
                "distribution": {k: float(v) for k, v in dist.items()},
            }

        elif ans_type == "score":
            score_val = getattr(a, "score", None) if not isinstance(a, dict) else a.get("score")
            lvl = getattr(a, "level", None) if not isinstance(a, dict) else a.get("level")
            dist = getattr(a, "distribution", None) if not isinstance(a, dict) else a.get("distribution")
            if score_val is None or not lvl or dist is None:
                raise ContractViolationError(f"Score '{name}' missing score, level, or distribution.")

            tol = 0.005 * len(dist) + 1e-9
            dist_sum = sum(dist.values())
            if abs(dist_sum - 1.0) > tol:
                raise ContractViolationError(f"Score '{name}' distribution sum {dist_sum:.4f} outside tolerance {tol:.4f}")

            parsed[name] = {
                "type": "score",
                "name": name,
                "score": float(score_val),
                "level": lvl,
                "distribution": {k: float(v) for k, v in dist.items()},
            }
        else:
            raise ContractViolationError(f"Unknown answer type '{ans_type}' for question '{name}'.")

    # Verify all expected questions are accounted for
    for q in expected_questions:
        q_name = q["name"]
        if q_name not in parsed:
            raise ContractViolationError(f"Expected question '{q_name}' missing from response.")

    return parsed
