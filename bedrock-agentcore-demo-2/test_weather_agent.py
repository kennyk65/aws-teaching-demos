# test_invoke.py
import pytest
import random
from weather_agent import invoke  # your entrypoint

class FakeContext:
    def __init__(self, session_id=None):
        self.session_id = session_id

def _random_suffix() -> str:
    return f"{random.randint(1000, 9999)}"


def test_invoke():
    ken_session_id = f"ken-session-001-abcdefghijklmnopqrstuvwxyz{_random_suffix()}"

    payload = {"actor_id": "ken", "prompt": "What is the current temperature in Seattle, WA? Use Fahrenheit."}
    context = FakeContext(session_id=ken_session_id)

    result = invoke(payload, context)

    assert not str(result["result"]).startswith("[Error invoking model:"), result["result"]
    assert "Seattle" in result["result"]
    assert "23" in result["result"]
    print(result)

    payload = {"actor_id": "ken", "prompt": "Do you think water will freeze there?"}
    context = FakeContext(session_id=ken_session_id)

    result = invoke(payload, context)

    assert result["actor_id"] == "ken"
    assert result["session_id"].startswith("ken-session-001")
    assert not str(result["result"]).startswith("[Error invoking model:"), result["result"]

    response_text = str(result["result"]).lower()
    positive_indicators = [
        "will freeze",
        "would freeze",
        "water will freeze",
        "below freezing",
        "under 32",
        "below 32",
    ]
    uncertainty_or_failure_indicators = [
        "need to know the location",
        "need the location",
        "need a location",
        "without a location",
        "cannot determine",
        "can't determine",
        "not enough information",
        "need more information",
        "which location",
        "what location",
    ]

    assert any(indicator in response_text for indicator in positive_indicators), result["result"]
    assert not any(indicator in response_text for indicator in uncertainty_or_failure_indicators), result["result"]
    print(result)


def test_memory_isolation_across_users_and_sessions():
    alice_session_id = f"alice-session-001-abcdefghijklmnopqrstuvwxyz{_random_suffix()}"
    bob_session_id = f"bob-session-001-abcdefghijklmnopqrstuvwxyz{_random_suffix()}"


    important_fact_1 = "Beavers mate for life."
    important_fact_2 = "Saturn is less dense than water."
    important_fact_3 = "Tom Brady won the super bowl 7 times."

    # Session A/User A: write a specific fact that should be remembered only in this session.
    payload_a = {
        "actor_id": "alice",
        "prompt": f"Please remember these important facts: {important_fact_1} {important_fact_2} {important_fact_3}",
    }
    context_a = FakeContext(
        session_id=alice_session_id,
    )

    result_a = invoke(payload_a, context_a)
    print(result_a)

    # See if it remembers these simple facts.
    payload_a = {      
        "actor_id": "alice",
        "prompt": "What are the important facts I asked you to remember?",
    }   
    
    result_a = invoke(payload_a, context_a)
    print(result_a)

    assert not str(result_a["result"]).startswith("[Error invoking model:"), result_a["result"]
    response_a = str(result_a["result"]).lower()
    assert important_fact_1.lower() in response_a, result_a["result"]
    assert important_fact_2.lower() in response_a, result_a["result"]
    assert important_fact_3.lower() in response_a, result_a["result"]


    # Session B/User B: ask for the passphrase and verify it cannot access Session A memory.
    payload_b = {
        "actor_id": "bob",
        "prompt": "What are the important facts I asked you to remember?",
    }
    context_b = FakeContext(
        session_id=bob_session_id,
    )

    result_b = invoke(payload_b, context_b)
    assert not str(result_b["result"]).startswith("[Error invoking model:"), result_b["result"]
    response_b = str(result_b["result"]).lower()
    cannot_know_indicators = [
        "don't know",
        "do not know",
        "can't",
        "cannot",
        "not sure",
        "no information",
        "no context",
        "didn't tell me",
        "did not tell me",
        "need more details",
        "need details",
        "need to clarify",
        "could you please clarify",
        "clarify which facts",
        "which facts",
        "what specific facts",
        "no specific information",
    ]

    assert important_fact_1.lower() not in response_b, result_b["result"]
    assert important_fact_2.lower() not in response_b, result_b["result"]
    assert important_fact_3.lower() not in response_b, result_b["result"]
    assert any(indicator in response_b for indicator in cannot_know_indicators), result_b["result"]
    print(result_b)

    # add extra logic here to verify that Alice can still access the secret fact in her own session, and that Bob cannot access it in his session, even after both have made multiple calls to the agent. This will help confirm that memory is properly isolated across sessions and users.
    # Session A/User A: ask for the important facts again to confirm they're still remembered.
    payload_a = {      
        "actor_id": "alice",
        "prompt": "What are the important facts I asked you to remember?",
    }   
    
    result_a = invoke(payload_a, context_a)
    print(result_a)

    assert not str(result_a["result"]).startswith("[Error invoking model:"), result_a["result"]
    response_a = str(result_a["result"]).lower()
    assert important_fact_1.lower() in response_a, result_a["result"]
    assert important_fact_2.lower() in response_a, result_a["result"]
    assert important_fact_3.lower() in response_a, result_a["result"]
    assert not any(indicator in response_a for indicator in cannot_know_indicators), result_a["result"]
