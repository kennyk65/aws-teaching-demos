from uuid import uuid4

from weather_agent_gateway import gateway_tools, invoke


class FakeContext:
    def __init__(self, session_id=None):
        self.session_id = session_id


class TestWeatherAgentGateway:
    def test_gateway_discovers_weather_tools(self):
        tool_names = {tool.tool_name.rsplit("___", 1)[-1] for tool in gateway_tools}
        assert {"weather", "forecast", "celcius_to_farenheit"} <= tool_names

    def test_current_weather(self):
        session_id = f"gateway-weather-session-{uuid4().hex}"
        payload = {
            "actor_id": "ken",
            "prompt": "What is the current temperature in Seattle, WA?",
        }

        result = invoke(payload, FakeContext(session_id=session_id))

        assert result["actor_id"] == "ken"
        assert result["session_id"] == session_id
        assert not result["result"].startswith("[Error invoking model:"), result["result"]
        assert "Seattle" in result["result"]
        assert "23" in result["result"]
        print(result)

    def test_forecast(self):
        session_id = f"gateway-forecast-session-{uuid4().hex}"
        payload = {
            "actor_id": "ken",
            "prompt": "What is the 5-day weather forecast for Seattle, WA?",
        }

        result = invoke(payload, FakeContext(session_id=session_id))

        assert result["actor_id"] == "ken"
        assert result["session_id"] == session_id
        assert not result["result"].startswith("[Error invoking model:"), result["result"]
        response = result["result"].lower()
        assert "seattle" in response
        assert "sun" in response
        assert "snow" in response
        print(result)
