"""Opt-in live tests for the OpenAI Decisions API."""

import os
import pytest

@pytest.mark.live
def test_live_decisions_api():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not configured. Skipping live test.")

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    resp = client.decisions.create(
        model="gpt-6-luna",
        input="Ping test.",
        questions=[{
            "type": "predicate",
            "name": "is_ping",
            "instructions": "Is this a ping test?"
        }]
    )

    assert resp.usage.output_tokens == 0
    assert len(resp.answers) == 1
    assert resp.answers[0].name == "is_ping"
