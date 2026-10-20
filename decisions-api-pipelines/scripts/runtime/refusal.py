"""Refusal policies, parsing, and gateway error recovery."""

import re
from typing import Any

GATEWAY_REFUSAL_RE = re.compile(r'refused to answer question [\\"]*([^"\\\\]+)[\\"]*', re.IGNORECASE)

class RefusalAction:
    BLOCK = "block"
    HOLD_AND_REVIEW = "hold_and_review"
    HUMAN_QUEUE = "human_queue"
    MISSING = "missing"

def recover_gateway_refusal(error_message: str) -> str | None:
    """
    Inspects gateway error string (e.g. from OpenRouter 502) to identify
    the specific question that was refused.
    """
    match = GATEWAY_REFUSAL_RE.search(error_message)
    if match:
        return match.group(1).strip()
    return None

def resolve_refusal_action(question_name: str, policy_mapping: dict[str, str]) -> str:
    """
    Resolves the operational action for a refused question.
    Defaults to 'hold_and_review' if not explicitly configured.
    """
    return policy_mapping.get(question_name, RefusalAction.HOLD_AND_REVIEW)
