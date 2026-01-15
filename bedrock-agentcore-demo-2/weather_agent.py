from strands import Agent, tool
from strands.models import BedrockModel
from bedrock_agentcore import BedrockAgentCoreApp
from botocore.exceptions import ClientError
from memory import AgentCoreMemory, AgentCoreSessionManager
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
    return "Sunny and O degree Celsius"

@tool
def celcius_to_farenheit(celcius):
    """Converts the given celcius temperature into farenheit.  Input is expected to be a number. Return value will be in Farenheit."""
    return (float(celcius) * 9/5) + 32


model_id="us.amazon.nova-lite-v1:0"
logger.info(f"Defining custom model using: {model_id}")
custom_model = BedrockModel(
    model_id=model_id,
    temperature=0.3  # Lower temperature = more consistent responses
)

# Initialize Bedrock AgentCore Memory
logger.info("Defining Memory")
memory = AgentCoreMemory()

# Setup the a Strands Agent SessionManager.  This will integrate AgentCore Memory into the Strands Agent.
session_manager = AgentCoreSessionManager(memory.client, memory.memory_id)

logger.info("Defining Agent")
agent = Agent(
    callback_handler=None,
    model=custom_model,
    tools=[weather, celcius_to_farenheit],
    session_manager=session_manager,   
    system_prompt="You are a helpful assistant. You can use the weather tool to tell the weather.  Users prefer Farenheit temperature scale and should not be exposed to Celcius."
)

# Define the Bedrock AgentCore Runtime interface.  
# This object provides an HTTP server, handles request/response, etc.
app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict):
    assistant_response = ""
    user_id = payload.get("user_id", "default")
    user_input = payload.get("prompt", "Hello")
    session_id = payload.get("session_id", user_id)
    
    try:
        # Initialize session to restore history
        session_manager.initialize(agent, session_id=session_id)
        
        # Call the agent using user input:
        logger.info(f"User input: {user_input}")
        response = agent(user_input)

        logger.debug(f"Received response: {response}")
        assistant_response = response.message['content'][0]['text']
        logger.info(f"Assistant response: {assistant_response}")
        
        # Manually save the conversation (only user and assistant messages)
        session_manager.save_conversation(agent, session_id)

    except Exception as e:
        import traceback
        assistant_response = f"[Error invoking model: {e}]"
        logger.error(assistant_response)
        logger.error(traceback.format_exc())

    return {
        "result": assistant_response,
        "session_id": session_id,
        "user_id": user_id
    }

@app.on_event("startup")
def startup_handler():
    logger.info("=" * 60)
    logger.info("Agent startup complete - ready for requests")
    logger.info("=" * 60)



if __name__ == "__main__":
    logger.info("Starting Agent...")
    app.run()

