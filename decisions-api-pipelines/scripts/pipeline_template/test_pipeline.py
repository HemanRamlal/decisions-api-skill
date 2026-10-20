"""Offline unit tests for the pipeline template."""

import pytest
import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from runtime import Answer, FakeDecisionsClient
from pipeline_template.pipeline import TriagePipeline
from pipeline_template.policy import CustomerContext
from pipeline_template.parser import ContractViolationError

def test_pipeline_happy_path_offline():
    client = FakeDecisionsClient()
    pipeline = TriagePipeline(client=client)
    customer = CustomerContext(customer_id="c_123", tier="enterprise", sla_hours=1, is_active=True)

    result, record = pipeline.process_ticket(
        item_id="t-001",
        message_body="System is down and completely failing for all users!",
        customer=customer,
    )

    assert result["status"] == "routed"
    assert "page_oncall_engineer" in result["actions"]
    assert record.item_id == "t-001"
    assert len(record.evidence_hash) == 64
    assert len(client.call_history) == 1

def test_pipeline_handles_refusal():
    # Inject refusal on is_urgent
    client = FakeDecisionsClient(inject_refusals={"is_urgent"})
    pipeline = TriagePipeline(client=client)
    customer = CustomerContext(customer_id="c_123", tier="standard", sla_hours=24, is_active=True)

    result, record = pipeline.process_ticket(
        item_id="t-002",
        message_body="Can I get a refund?",
        customer=customer,
    )

    assert result["status"] == "human_review"
    assert "hold_for_human_triage" in result["actions"]

def test_pipeline_catches_contract_violation():
    # Inject corrupted distribution sum
    client = FakeDecisionsClient(inject_contract_violation=True)
    pipeline = TriagePipeline(client=client)
    customer = CustomerContext(customer_id="c_123", tier="standard", sla_hours=24, is_active=True)

    with pytest.raises(ContractViolationError):
        pipeline.process_ticket(
            item_id="t-003",
            message_body="Hello support",
            customer=customer,
        )
