"""Experiment 8: Gateway Refusal Recovery."""

import re
from typing import Any

GATEWAY_ERR_SAMPLE = 'HTTP 502 Bad Gateway: upstream model refused to answer question "sensitive_attr_check"'

def test_gateway_recovery_mechanism() -> dict[str, Any]:
    match = re.search(r'refused to answer question [\\"]*([^"\\\\]+)[\\"]*', GATEWAY_ERR_SAMPLE)
    refused_name = match.group(1) if match else None

    # Original requested questions
    original_questions = ["is_urgent", "sensitive_attr_check", "assigned_team"]

    # Filter out refused question to recover surviving answers
    surviving_questions = [q for q in original_questions if q != refused_name]

    return {
        "detected_refused_question": refused_name,
        "recovered_questions": surviving_questions,
        "recovery_successful": refused_name == "sensitive_attr_check" and len(surviving_questions) == 2,
    }

if __name__ == "__main__":
    res = test_gateway_recovery_mechanism()
    print("Gateway recovery test results:", res)
