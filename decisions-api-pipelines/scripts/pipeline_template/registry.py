"""Versioned question registry for the pipeline."""

from typing import Any

QUESTIONS: dict[tuple[str, str], dict[str, Any]] = {
    ("is_urgent", "v1"): {
        "name": "is_urgent",
        "version": "v1",
        "type": "predicate",
        "instructions": "In <<MESSAGE>>, does the customer state that the system is completely unavailable right now?",
    },
    ("assigned_team", "v1"): {
        "name": "assigned_team",
        "version": "v1",
        "type": "choice",
        "instructions": "In <<MESSAGE>>, which department owns the customer's stated issue?",
        "choices": [
            {"value": "billing", "description": "Invoices, payment errors, and refund requests."},
            {"value": "technical", "description": "Software bugs, system outages, and API errors."},
            {"value": "out_of_scope", "description": "General marketing inquiries or topics fitting none of the above."},
            {"value": "no_request", "description": "The message expresses sentiment but states no actionable problem."},
        ],
    },
    ("impact_severity", "v1"): {
        "name": "impact_severity",
        "version": "v1",
        "type": "score",
        "instructions": "In <<MESSAGE>>, how severely does this issue obstruct work?",
        "levels": [
            {"label": "None", "description": "General question; no lost work."},
            {"label": "Cosmetic", "description": "Styling or display issue; functionality intact."},
            {"label": "Workaround", "description": "Functionality impaired but an alternative path works."},
            {"label": "Blocked", "description": "Core functionality completely obstructed with no workaround."},
        ],
    },
}

def get_questions() -> list[dict[str, Any]]:
    return [dict(q) for q in QUESTIONS.values()]
