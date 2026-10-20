"""Main pipeline orchestrator with injected client and decision record emission."""

import time
from typing import Any

from .builder import build_input
from .config import CONFIG
from .parser import parse_decision_response
from .policy import CustomerContext, evaluate_policy
from .registry import get_questions

# We import runtime utilities using absolute or relative import depending on install
try:
    from runtime import (
        Breaker,
        DecisionRecord,
        DecisionsClientProtocol,
        execute_with_resilience,
        make_evidence_hash,
    )
except ImportError:
    import sys, os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from runtime import (
        Breaker,
        DecisionRecord,
        DecisionsClientProtocol,
        execute_with_resilience,
        make_evidence_hash,
    )

class TriagePipeline:
    """Isolated, production-ready pipeline package."""

    def __init__(self, client: DecisionsClientProtocol, breaker: Breaker | None = None, config_override: dict[str, Any] | None = None):
        self.client = client
        self.breaker = breaker or Breaker()
        self.config = dict(CONFIG)
        if config_override:
            self.config.update(config_override)

    def process_ticket(
        self,
        item_id: str,
        message_body: str,
        customer: CustomerContext,
        deadline: float | None = None,
    ) -> tuple[dict[str, Any], DecisionRecord]:
        """
        Processes a ticket through input building, resilient API execution,
        defensive parsing, and deterministic policy evaluation.
        """
        # 1. Build sanitized input
        input_payload = build_input(message_body, {"account_type": customer.tier})
        questions = get_questions()

        # 2. Resilient API execution
        timeout = self.config["default_timeout_seconds"]
        resp = execute_with_resilience(
            func=self.client.create_decision,
            deadline=deadline,
            breaker=self.breaker,
            model=self.config["model"],
            input_payload=input_payload,
            questions=questions,
            timeout=timeout,
        )

        # 3. Defensive parsing
        parsed = parse_decision_response(resp, questions)

        # 4. Evaluate deterministic policy
        result = evaluate_policy(parsed, customer, self.config)

        # 5. Emit decision record
        evidence_hash = make_evidence_hash(input_payload)
        q_versions = tuple((q["name"], q.get("version", "v1")) for q in questions)
        actions = tuple(result.get("actions", []))

        record = DecisionRecord(
            item_id=item_id,
            timestamp=time.time(),
            evidence_hash=evidence_hash,
            question_versions=q_versions,
            schema_version=self.config["version"],
            raw_answers=parsed,
            actions_taken=actions,
            provisional=False,
        )

        return result, record
