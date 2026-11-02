from strands import Agent, tool
from strands.models import BedrockModel
from strands.types.tools import ToolContext
from bedrock_agentcore import BedrockAgentCoreApp
import logging, boto3, sys, os, json


# Create a logger
logger = logging.getLogger("agent_activity")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))

# Initialize Bedrock client
bedrock = boto3.client("bedrock-runtime")
# Client for invoking other agents hosted in AgentCore Runtime
agentcore = boto3.client("bedrock-agentcore")
# Control-plane client, used to look up a runtime's ARN by name
control = boto3.client("bedrock-agentcore-control")


FORECAST_AGENT_NAME = os.environ.get("FORECAST_AGENT_NAME", "forecast_agent")
_arn_cache = {}

def resolve_agent_arn(name: str) -> str:
    """The runtime API only accepts an ARN, so look it up by name (cached)."""
    if name not in _arn_cache:
        for page in control.get_paginator("list_agent_runtimes").paginate():
            for rt in page["agentRuntimes"]:
                if rt["agentRuntimeName"] == name:
                    _arn_cache[name] = rt["agentRuntimeArn"]
                    break
            if name in _arn_cache:
                break
        else:
            raise ValueError(f"No agent runtime named '{name}' found")
    return _arn_cache[name]

logger.info("Defining Tools...")

@tool
def weather(location):
    """Get current weather information in the given location.  All temperatures are returned in Celcius."""
    return "Sunny and -5 degrees Celsius"

@tool
def celcius_to_farenheit(celcius):
    """Converts the given celcius temperature into farenheit.  Input is expected to be a number. Return value will be in Farenheit."""
    return (float(celcius) * 9/5) + 32

@tool(context=True)
def forecast(location: str, tool_context: ToolContext):
    """Get a multi-day weather forecast for the given location.  All temperatures are returned in Celcius."""
    
    # Get / pass the same session used by this agent to check the weather.
    session_id = tool_context.invocation_state["session_id"]
    try:
        response = agentcore.invoke_agent_runtime(
            agentRuntimeArn=resolve_agent_arn(FORECAST_AGENT_NAME),
            runtimeSessionId=session_id,
            payload=json.dumps({"prompt": f"Give me the forecast for {location}"}).encode("utf-8"),
        )
        body = json.loads(response["response"].read())
        return body.get("result", str(body)) if isinstance(body, dict) else str(body)
    except Exception as e:
        logger.error(f"Forecast agent call failed: {e}")
        return f"Forecast unavailable: {e}"



model_id="us.anthropic.claude-sonnet-4-6"
logger.info(f"Defining custom model using: {model_id}...")
custom_model = BedrockModel(
    model_id=model_id,
    temperature=0.3  # Lower temperature = more consistent responses
)


def build_agent() -> Agent:
    system_prompt = """
    You are a helpful assistant. You can use the weather tool to tell the current weather, and the forecast tool for upcoming days.  
    Users prefer Farenheit temperature scale and should not be exposed to Celcius.
    The freezing point of water is 0 degrees Celcius, which is 32 degrees Farenheit.  Expect water to freeze at or below these temperatures.  
    """

    return Agent(
        callback_handler=None,      # Suppress Strands default PrintingCallbackHandler, which would duplicate our logging.
        model=custom_model,
        tools=[weather, forecast, celcius_to_farenheit],
        system_prompt=system_prompt
    )

# Define the Bedrock AgentCore Runtime interface.  
# This object provides an HTTP server, handles request/response, etc.
app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict, context):
    logger.info(f"payload is: {payload}")
    assistant_response = ""
    actor_id = payload.get("actor_id", "default")
    session_id = context.session_id or actor_id
    user_input = payload.get("prompt", "Hello")
    logger.info(f"actor_id is {actor_id} and session_id is {session_id} ")

    try:
        agent = build_agent()

        # Call the agent using user input:
        logger.info(f"User input: {user_input}")
        response = agent(user_input, session_id=session_id)

        logger.debug(f"Received response: {response}")
        assistant_response = response.message['content'][0]['text']
        logger.info(f"Assistant response: {assistant_response}")

    except Exception as e:
        import traceback
        assistant_response = f"[Error invoking model: {e}]"
        logger.error(assistant_response)
        logger.error(traceback.format_exc())

    return {
        "result": assistant_response,
        "session_id": session_id,
        "actor_id": actor_id
    }



if __name__ == "__main__":
    logger.info("Agent is starting...")
    app.run()
