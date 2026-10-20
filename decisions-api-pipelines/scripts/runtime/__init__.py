"""Runtime support package for Decisions API pipelines."""

from .protocol import (
    Answer,
    DecisionResponse,
    DecisionsClientProtocol,
    QuestionDef,
    Usage,
    UsageDetails,
)
from .fake_client import FakeDecisionsClient
from .resilience import Breaker, CircuitBreakerOpenError, execute_with_resilience
from .decision_record import DecisionRecord, config_fingerprint, make_evidence_hash
from .refusal import RefusalAction, recover_gateway_refusal, resolve_refusal_action

__all__ = [
    "Answer",
    "DecisionResponse",
    "DecisionsClientProtocol",
    "QuestionDef",
    "Usage",
    "UsageDetails",
    "FakeDecisionsClient",
    "Breaker",
    "CircuitBreakerOpenError",
    "execute_with_resilience",
    "DecisionRecord",
    "config_fingerprint",
    "make_evidence_hash",
    "RefusalAction",
    "recover_gateway_refusal",
    "resolve_refusal_action",
]
