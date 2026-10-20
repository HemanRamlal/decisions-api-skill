"""Pipeline configuration, thresholds, timeouts, and refusal policies."""

CONFIG = {
    "pipeline_name": "support_triage_template",
    "version": "1.0.0",
    "model": "gpt-6-luna",
    "input_format": "ticket-v1",
    "policy_version": "policy-v1",
    "default_timeout_seconds": 2.5,
    "urgent_threshold": 0.85,
    "escape_threshold": 0.40,
    "auto_route_threshold": 0.80,
    "refusal_policies": {
        "is_urgent": "human_queue",
        "assigned_team": "human_queue",
        "impact_severity": "missing",
    },
    "cost_inputs": {
        "c_fp": 50.0,
        "c_fn": 10.0,
        "c_review": 2.5,
    },
}
