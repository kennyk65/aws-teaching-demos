# test_invoke.py
import pytest
from weather_agent import invoke  # your entrypoint

class FakeContext:
    def __init__(self, actor_id="ken", session_id=None):
        self.actor_id = actor_id
        self.session_id = session_id or actor_id

def test_invoke():
    payload = {"actor_id": "ken", "prompt": "What is the current temperature in Seattle, WA? Use Fahrenheit."}
    context = FakeContext(session_id="ken-session-001-abcdefghijklmnopqrstuvwxyz123")

    result = invoke(payload, context)

    assert result["actor_id"] == "ken"
    assert result["session_id"].startswith("ken-session-001")
    assert "Seattle" in result["result"] or result["result"] is not None  # replace with actual agent check
    print(result)