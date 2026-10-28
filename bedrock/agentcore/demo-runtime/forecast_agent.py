from strands import Agent, tool
from strands.models import BedrockModel
from bedrock_agentcore import BedrockAgentCoreApp
import logging, boto3, sys


# Create a logger
logger = logging.getLogger("agent_activity")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))

# Initialize Bedrock client
bedrock = boto3.client("bedrock-runtime")


logger.info("Defining Tools...")

@tool
def forecast(location):
    """Get a multi-day weather forecast for the given location.  All temperatures are returned in Celcius."""
    return (
        "5-day forecast: "
        "Day 1: Sunny, high -2 degrees Celsius, low -8 degrees Celsius. "
        "Day 2: Partly cloudy, high 0 degrees Celsius, low -6 degrees Celsius. "
        "Day 3: Snow, high -3 degrees Celsius, low -9 degrees Celsius. "
        "Day 4: Cloudy, high 1 degrees Celsius, low -4 degrees Celsius. "
        "Day 5: Sunny, high 3 degrees Celsius, low -2 degrees Celsius."
    )

@tool
def celcius_to_farenheit(celcius):
    """Converts the given celcius temperature into farenheit.  Input is expected to be a number. Return value will be in Farenheit."""
    return (float(celcius) * 9/5) + 32


model_id="us.anthropic.claude-sonnet-4-6"
logger.info(f"Defining custom model using: {model_id}...")
custom_model = BedrockModel(
    model_id=model_id,
    temperature=0.3  # Lower temperature = more consistent responses
)


def build_agent() -> Agent:
    system_prompt = """
    You are a helpful assistant. You can use the forecast tool to provide a weather forecast for a given location.  
    Always summarize the upcoming days clearly, day by day.
    Users prefer Farenheit temperature scale and should not be exposed to Celcius.
    """

    return Agent(
        callback_handler=None,      # Suppress Strands default PrintingCallbackHandler, which would duplicate our logging.
        model=custom_model,
        tools=[forecast, celcius_to_farenheit],
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



if __name__ == "__main__":
    logger.info("Agent is starting...")
    app.run()
