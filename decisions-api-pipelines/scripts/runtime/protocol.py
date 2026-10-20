"""Client protocol and standard data transfer objects for Decisions API."""

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

@dataclass(frozen=True)
class QuestionDef:
    name: str
    version: str
    type: Literal["predicate", "choice", "score"]
    instructions: str
    choices: tuple[dict[str, str], ...] | None = None
    levels: tuple[dict[str, str], ...] | None = None
    refusal_policy: str = "hold_and_review"

    def to_wire_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name": self.name,
            "type": self.type,
            "instructions": self.instructions,
        }
        if self.type == "choice" and self.choices:
            d["choices"] = list(self.choices)
        elif self.type == "score" and self.levels:
            d["levels"] = list(self.levels)
        return d

@dataclass
class Answer:
    name: str
    type: Literal["predicate", "choice", "score", "refusal"]
    probability: float | None = None
    choice: str | None = None
    confidence: float | None = None
    distribution: dict[str, float] | None = None
    score: float | None = None
    level: str | None = None

@dataclass
class UsageDetails:
    cached_tokens: int = 0
    cache_write_tokens: int = 0

@dataclass
class Usage:
    input_tokens: int
    output_tokens: int = 0
    reasoning_tokens: int = 0
    input_tokens_details: UsageDetails = field(default_factory=UsageDetails)

@dataclass
class DecisionResponse:
    id: str
    created: int
    model: str
    object: str
    usage: Usage
    answers: list[Answer]

    def answer_by_name(self, name: str) -> Answer:
        for a in self.answers:
            if a.name == name:
                return a
        raise KeyError(f"Answer with name '{name}' not found in response.")

@runtime_checkable
class DecisionsClientProtocol(Protocol):
    """Protocol for Decisions API clients (both real and fake)."""

    def create_decision(
        self,
        model: str,
        input_payload: str | list[dict[str, Any]],
        questions: list[dict[str, Any]],
        safety_identifier: str | None = None,
        timeout: float | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> DecisionResponse:
        ...
