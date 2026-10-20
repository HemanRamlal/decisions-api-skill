"""Immutable decision records and cryptographic fingerprinting."""

from dataclasses import asdict, dataclass
import hashlib
import json
import time
from typing import Any

@dataclass(frozen=True)
class DecisionRecord:
    item_id: str
    timestamp: float
    evidence_hash: str
    question_versions: tuple[tuple[str, str], ...]  # ((name, version), ...)
    schema_version: str
    raw_answers: dict[str, Any]
    actions_taken: tuple[str, ...]
    provisional: bool

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

def make_evidence_hash(evidence: str | list[dict[str, Any]]) -> str:
    """Generates a reproducible SHA-256 hash of the evidence payload."""
    if isinstance(evidence, str):
        data = evidence.encode("utf-8")
    else:
        data = json.dumps(evidence, sort_keys=True).encode("utf-8")
    return hashlib.sha256(data).hexdigest()

def config_fingerprint(
    questions: list[dict[str, Any]],
    input_format: str,
    policy_version: str,
    sdk_version: str = "3.26.0",
    model: str = "gpt-6-luna",
) -> str:
    """Computes a deterministic fingerprint of pipeline configuration."""
    canonical = {
        "questions": sorted(
            [{"name": q.get("name"), "type": q.get("type"), "instructions": q.get("instructions")} for q in questions],
            key=lambda x: str(x.get("name"))
        ),
        "input_format": input_format,
        "policy_version": policy_version,
        "sdk_version": sdk_version,
        "model": model,
    }
    payload = json.dumps(canonical, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
