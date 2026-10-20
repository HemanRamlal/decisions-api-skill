"""Offline fake client for unit testing Decisions API pipelines."""

import time
from typing import Any
from .protocol import Answer, DecisionResponse, DecisionsClientProtocol, Usage, UsageDetails

class FakeDecisionsClient(DecisionsClientProtocol):
    """
    Offline implementation of DecisionsClientProtocol.
    Permits canned answers, latency simulation, and fault injection.
    """

    def __init__(
        self,
        canned_answers: dict[str, Answer] | None = None,
        latency_seconds: float = 0.0,
        inject_refusals: set[str] | None = None,
        inject_error: Exception | None = None,
        inject_contract_violation: bool = False,
    ):
        self.canned_answers = canned_answers or {}
        self.latency_seconds = latency_seconds
        self.inject_refusals = inject_refusals or set()
        self.inject_error = inject_error
        self.inject_contract_violation = inject_contract_violation
        self.call_history: list[dict[str, Any]] = []

    def create_decision(
        self,
        model: str,
        input_payload: str | list[dict[str, Any]],
        questions: list[dict[str, Any]],
        safety_identifier: str | None = None,
        timeout: float | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> DecisionResponse:
        call_record = {
            "model": model,
            "input": input_payload,
            "questions": questions,
            "safety_identifier": safety_identifier,
            "timeout": timeout,
            "extra_body": extra_body,
            "timestamp": time.time(),
        }
        self.call_history.append(call_record)

        if self.latency_seconds > 0:
            if timeout is not None and self.latency_seconds > timeout:
                raise TimeoutError(f"Client timeout of {timeout}s exceeded by simulated latency.")
            time.sleep(min(self.latency_seconds, 0.05))

        if self.inject_error:
            raise self.inject_error

        answers: list[Answer] = []
        for q in questions:
            q_name = q.get("name", "unnamed")
            q_type = q.get("type", "predicate")

            # Injected refusal
            if q_name in self.inject_refusals:
                answers.append(Answer(name=q_name, type="refusal"))
                continue

            # Canned answer
            if q_name in self.canned_answers:
                answers.append(self.canned_answers[q_name])
                continue

            # Default generation based on type
            if q_type == "predicate":
                answers.append(Answer(name=q_name, type="predicate", probability=0.85))
            elif q_type == "choice":
                choices = q.get("choices", [{"value": "opt1"}, {"value": "opt2"}])
                val0 = choices[0]["value"]
                dist = {c["value"]: (0.80 if i == 0 else round(0.20 / (len(choices) - 1), 2)) for i, c in enumerate(choices)}
                if self.inject_contract_violation:
                    dist[val0] = 0.99  # sum clearly > 1.0 + tol
                answers.append(Answer(name=q_name, type="choice", choice=val0, confidence=0.80, distribution=dist))
            elif q_type == "score":
                levels = q.get("levels", [{"label": "Low"}, {"label": "High"}])
                lbl = levels[-1]["label"]
                dist = {l["label"]: (0.75 if i == len(levels)-1 else 0.25 / (len(levels)-1)) for i, l in enumerate(levels)}
                answers.append(Answer(name=q_name, type="score", score=float(len(levels)-1), confidence=0.75, level=lbl, distribution=dist))
            else:
                answers.append(Answer(name=q_name, type="predicate", probability=0.50))

        # Estimate simple token usage
        est_tokens = 140 + (len(str(input_payload)) // 4) + sum(len(str(q)) // 4 for q in questions)
        usage = Usage(input_tokens=est_tokens, output_tokens=0, reasoning_tokens=0, input_tokens_details=UsageDetails())

        return DecisionResponse(
            id=f"dec_fake_{len(self.call_history)}",
            created=int(time.time()),
            model=model,
            object="decision",
            usage=usage,
            answers=answers,
        )
