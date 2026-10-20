"""Deterministic policy rules operating on profile judgments and database facts."""

from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class CustomerContext:
    customer_id: str
    tier: str  # 'enterprise', 'growth', 'standard'
    sla_hours: int
    is_active: bool

def evaluate_policy(parsed_answers: dict[str, Any], customer: CustomerContext, config: dict[str, Any]) -> dict[str, Any]:
    """
    Applies deterministic code policies to parsed answers.
    Judgment comes from the model; policy, thresholds, routing, and actions come from code.
    """
    actions: list[str] = []
    status = "routed"

    urgent_ans = parsed_answers.get("is_urgent", {})
    team_ans = parsed_answers.get("assigned_team", {})
    impact_ans = parsed_answers.get("impact_severity", {})

    # Check for refusals
    if urgent_ans.get("type") == "refusal" or team_ans.get("type") == "refusal":
        return {
            "status": "human_review",
            "destination_queue": "triage_refusal_queue",
            "priority": "P2",
            "actions": ["hold_for_human_triage"],
        }

    # Outage paging policy
    is_urgent_prob = urgent_ans.get("probability", 0.0)
    if is_urgent_prob >= config.get("urgent_threshold", 0.85) and customer.tier == "enterprise":
        actions.append("page_oncall_engineer")

    # Team assignment with escape handling
    team_dist = team_ans.get("distribution", {})
    escape_prob = team_dist.get("out_of_scope", 0.0) + team_dist.get("no_request", 0.0)

    if escape_prob >= config.get("escape_threshold", 0.40):
        destination = "general_human_triage"
        actions.append("flag_unclear_category")
    else:
        # Renormalize legitimate teams
        legit_teams = {k: v for k, v in team_dist.items() if k not in ("out_of_scope", "no_request")}
        sum_legit = sum(legit_teams.values())
        if sum_legit > 0:
            best_team = max(legit_teams.items(), key=lambda x: x[1])[0]
            renorm_prob = legit_teams[best_team] / sum_legit
            if renorm_prob >= config.get("auto_route_threshold", 0.80):
                destination = f"queue_{best_team}"
            else:
                destination = "queue_tier1_review"
                actions.append("low_confidence_review")
        else:
            destination = "general_human_triage"

    # Priority determination
    impact_score = impact_ans.get("score", 0.0)
    if impact_score >= 2.5 or customer.tier == "enterprise":
        priority = "P1" if impact_score >= 2.5 and customer.tier == "enterprise" else "P2"
    else:
        priority = "P3"

    return {
        "status": status,
        "destination_queue": destination,
        "priority": priority,
        "actions": actions,
    }
