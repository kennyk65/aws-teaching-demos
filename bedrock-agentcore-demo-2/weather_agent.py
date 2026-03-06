from strands import Agent, tool
from strands.models import BedrockModel
from bedrock_agentcore import BedrockAgentCoreApp
from botocore.exceptions import ClientError
from memory import AgentCoreMemory, AgentCoreMemoryHookProvider
import logging, boto3, time, os, json, sys


# Create a logger
logger = logging.getLogger("agent_activity")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))

# Initialize Bedrock client
bedrock = boto3.client("bedrock-runtime")


logger.info("Defining Tools")

@tool
def weather(location):
    """Get current weather information in the given location.  All temperatures are returned in Celcius."""
    return "Sunny and -5 degrees Celsius"

@tool
def celcius_to_farenheit(celcius):
    """Converts the given celcius temperature into farenheit.  Input is expected to be a number. Return value will be in Farenheit."""
    return (float(celcius) * 9/5) + 32


model_id="us.amazon.nova-micro-v1:0"
logger.info(f"Defining custom model using: {model_id}")
custom_model = BedrockModel(
    model_id=model_id,
    temperature=0.3  # Lower temperature = more consistent responses
)

# Initialize Bedrock AgentCore Memory
logger.info("Defining Memory")
memory = AgentCoreMemory()

def build_agent(session_id: str, actor_id: str) -> Agent:
    # Build a per-request hook provider so session context is explicit and isolated.
    memory_hook_provider = AgentCoreMemoryHookProvider(
        memory.client,
        memory.memory_id,
        session_id=session_id,
        actor_id=actor_id,
    )

    return Agent(
        callback_handler=None,
        model=custom_model,
        tools=[weather, celcius_to_farenheit],
        hooks=[memory_hook_provider],
        system_prompt="You are a helpful assistant. You can use the weather tool to tell the weather.  Users prefer Farenheit temperature scale and should not be exposed to Celcius."
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
        agent = build_agent(session_id=session_id, actor_id=actor_id)

        # Call the agent using user input:
        logger.info(f"User input: {user_input}")
        response = agent(user_input)

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

@app.on_event("startup")
def startup_handler():
    logger.info("=" * 60)
    logger.info("Agent startup complete - ready for requests")
    logger.info("=" * 60)



if __name__ == "__main__":
    logger.info("Starting Agent...")
    app.run()

