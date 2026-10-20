"""Unit tests for runtime protocol, fake client, resilience, and records."""

import pytest
import time
from runtime.protocol import Answer, DecisionResponse, QuestionDef, Usage, UsageDetails
from runtime.fake_client import FakeDecisionsClient
from runtime.resilience import Breaker, CircuitBreakerOpenError, execute_with_resilience, is_retryable_error
from runtime.decision_record import DecisionRecord, config_fingerprint, make_evidence_hash
from runtime.refusal import recover_gateway_refusal, resolve_refusal_action

def test_question_def_to_wire():
    q = QuestionDef(
        name="test_q",
        version="v1",
        type="choice",
        instructions="Choose option",
        choices=({"value": "a", "description": "opt a"}, {"value": "b", "description": "opt b"}),
    )
    wire = q.to_wire_dict()
    assert wire["name"] == "test_q"
    assert wire["type"] == "choice"
    assert len(wire["choices"]) == 2

def test_fake_client_canned_and_refusal():
    canned = Answer(name="q1", type="predicate", probability=0.92)
    client = FakeDecisionsClient(canned_answers={"q1": canned}, inject_refusals={"q2"})

    resp = client.create_decision(
        model="gpt-6-luna",
        input_payload="hello",
        questions=[
            {"name": "q1", "type": "predicate"},
            {"name": "q2", "type": "predicate"},
            {"name": "q3", "type": "choice", "choices": [{"value": "v1"}, {"value": "v2"}]}
        ]
    )

    assert resp.answer_by_name("q1").probability == 0.92
    assert resp.answer_by_name("q2").type == "refusal"
    assert resp.answer_by_name("q3").choice == "v1"
    assert resp.usage.output_tokens == 0

def test_breaker_trips():
    breaker = Breaker(failure_threshold=0.5, window_size=10, cooldown_seconds=5.0)
    for _ in range(5):
        breaker.record_result(success=True)
    for _ in range(6):
        breaker.record_result(success=False)
    assert not breaker.allow_request()

def test_execute_with_resilience_retries():
    calls = 0
    def flaky_func(timeout=None):
        nonlocal calls
        calls += 1
        if calls < 2:
            raise ConnectionError("Connection reset by peer")
        return "success"

    res = execute_with_resilience(flaky_func, max_retries=2, base_backoff=0.01)
    assert res == "success"
    assert calls == 2

def test_execute_with_resilience_deadline_expired():
    def slow_func(timeout=None):
        time.sleep(0.1)
        return "done"

    with pytest.raises(TimeoutError):
        execute_with_resilience(slow_func, deadline=time.time() + 0.02)

def test_decision_record_and_hash():
    h = make_evidence_hash("sample evidence")
    assert len(h) == 64

    fp = config_fingerprint(
        questions=[{"name": "q1", "type": "predicate", "instructions": "test"}],
        input_format="format_v1",
        policy_version="pol_v1",
    )
    assert len(fp) == 64

    rec = DecisionRecord(
        item_id="item-1",
        timestamp=time.time(),
        evidence_hash=h,
        question_versions=(("q1", "v1"),),
        schema_version="1.0",
        raw_answers={"q1": 0.9},
        actions_taken=("page",),
        provisional=False,
    )
    json_str = rec.to_json()
    assert "item-1" in json_str

def test_gateway_refusal_recovery():
    err = 'HTTP 502: Model refused to answer question "sensitive_check"'
    q_name = recover_gateway_refusal(err)
    assert q_name == "sensitive_check"
    action = resolve_refusal_action("sensitive_check", {"sensitive_check": "block"})
    assert action == "block"
