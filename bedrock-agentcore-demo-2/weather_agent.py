# import warnings
# warnings.filterwarnings(action="ignore", message=r"datetime.datetime.utcnow") 

from strands import Agent, tool
from strands.models import BedrockModel
from bedrock_agentcore import BedrockAgentCoreApp
from botocore.exceptions import ClientError
from memory import AgentCoreMemory    # See memory.py for details
import logging, boto3, time, os, json, sys



# Create a logger
logger = logging.getLogger("agent_activity")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))

# Create an agent with logging enabled
logger.info("Creating new agent with Nova Lite model")

logger.info("Defining Tools")

@tool
def weather(location):
    """Get current weather information in the given location.  All temperatures are returned in Celcius."""
    return "Sunny and O degree Celsius"

@tool
def celcius_to_farenheit(celcius):
    """Converts the given celcius temperature into farenheit.  Input is expected to be a number. Return value will be in Farenheit."""
    return (float(celcius) * 9/5) + 32


logger.info("Defining custom model")
custom_model = BedrockModel(
    model_id="us.amazon.nova-lite-v1:0",
    temperature=0.3  # Lower temperature = more consistent responses
)

logger.info("Defining Agent")
agent = Agent(callback_handler=None,
    model=custom_model,
    tools=[weather, celcius_to_farenheit],
    system_prompt="You are a helpful assistant. You can use the weather tool to tell the weather.  Users prefer Farenheit temperature scale and should not be exposed to Celcius."
)


# Initialize Bedrock AgentCore Memory
logger.info("Defining Memory")
memory = AgentCoreMemory()

# Initialize Bedrock client
bedrock = boto3.client("bedrock-runtime")

app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload: dict):
    assistant_response = ""
    user_id = payload.get("user_id", "default")
    user_input = payload.get("prompt", "Hello")
    session_id = payload.get("session_id", user_id)
    
    try:
        # Retrieve conversation history from memory
        conversation_history = memory.get_conversation_history(user_id, session_id)
        
        # Add the new user message
        conversation_history.append({
            "role": "user",
            "content": [{"text": user_input}]
        })

        # build messages array for the model (full history)
        model_input = {"messages": conversation_history}
        
        logger.info(f"Sending to model: {json.dumps(model_input)}")
        response = agent(json.dumps(model_input))

        logger.debug(f"Received response: {response}")
        assistant_response = response.message['content'][0]['text']
        logger.info(f"Assistant response: {assistant_response}")

        # Add assistant response
        conversation_history.append({
            "role": "assistant",
            "content": [{"text": assistant_response}]
        })
        
        # Store updated conversation history
        memory.set_conversation_history(user_id, conversation_history, session_id)

    except Exception as e:
        assistant_response = f"[Error invoking model: {e}]"
        logger.error(assistant_response)

    return {
        "result": assistant_response,
        "session_id": session_id,
        "user_id": user_id
    }

logger.info("Starting Agent")

if __name__ == "__main__":
    app.run()

