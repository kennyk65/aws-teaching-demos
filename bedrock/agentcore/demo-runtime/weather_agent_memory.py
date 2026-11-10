import atexit
import logging
import os
import sys

import boto3
from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
try:
    from mcp.client.streamable_http import streamable_http_client
except ImportError:  # older mcp releases use the previous name
    from mcp.client.streamable_http import streamablehttp_client as streamable_http_client
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient


logger = logging.getLogger("agent_activity")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))

GATEWAY_PARAMETER_NAME = os.environ.get(
    "GATEWAY_PARAMETER_NAME", "/agentcore/weather_agent/gateway-url"
)
MEMORY_PARAMETER_NAME = os.environ.get(
    "MEMORY_PARAMETER_NAME", "/agentcore/weather_agent/memory-id"
)

model_id = "us.anthropic.claude-sonnet-4-6"
logger.info(f"Defining custom model using: {model_id}...")
custom_model = BedrockModel(model_id=model_id, temperature=0.3)

ssm = boto3.client("ssm")
gateway_url = ssm.get_parameter(Name=GATEWAY_PARAMETER_NAME)["Parameter"]["Value"]
memory_id = ssm.get_parameter(Name=MEMORY_PARAMETER_NAME)["Parameter"]["Value"]

logger.info("Defining Tools...")
gateway = MCPClient(lambda: streamable_http_client(gateway_url))
gateway.start()
atexit.register(gateway.stop, None, None, None)
gateway_tools = gateway.list_tools_sync()
if not gateway_tools:
    raise RuntimeError("The AgentCore Gateway returned no tools")


def build_agent(tools, actor_id: str, session_id: str) -> Agent:
    system_prompt = """
    You are a helpful assistant. You can use the weather tool to tell the current weather, and the forecast tool for upcoming days.
    Users prefer Farenheit temperature scale and should not be exposed to Celcius.
    The freezing point of water is 0 degrees Celcius, which is 32 degrees Farenheit. Expect water to freeze at or below these temperatures.
    """

    memory_config = AgentCoreMemoryConfig(
        memory_id=memory_id,
        actor_id=actor_id,
        session_id=session_id,
    )
    # The session manager registers Strands hooks to save and restore messages.
    session_manager = AgentCoreMemorySessionManager(agentcore_memory_config=memory_config)
    return Agent(
        callback_handler=None,
        model=custom_model,
        tools=tools,
        system_prompt=system_prompt,
        session_manager=session_manager,
    )


app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict, context):
    logger.info(f"payload is: {payload}")
    actor_id = payload.get("actor_id", "default")
    session_id = context.session_id or actor_id
    user_input = payload.get("prompt", "Hello")
    logger.info(f"actor_id is {actor_id} and session_id is {session_id} ")

    try:
        agent = build_agent(gateway_tools, actor_id, session_id)
        logger.info(f"User input: {user_input}")
        response = agent(user_input, session_id=session_id)
        logger.debug(f"Received response: {response}")
        assistant_response = response.message["content"][0]["text"]
        logger.info(f"Assistant response: {assistant_response}")
    except Exception as e:
        import traceback

        assistant_response = f"[Error invoking model: {e}]"
        logger.error(assistant_response)
        logger.error(traceback.format_exc())

    return {
        "result": assistant_response,
        "session_id": session_id,
        "actor_id": actor_id,
    }


if __name__ == "__main__":
    logger.info("Agent is starting...")
    app.run()
