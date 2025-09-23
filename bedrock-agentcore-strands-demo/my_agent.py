# # my_agent.py
# # Simple AgentCore agent using Bedrock
# # pip install bedrock-agentcore-starter-toolkit
# # agentcore configure --entrypoint my_agent.py --requirements-file requirements.txt --protocol MCP
# #
# # agentcore launch --agent my_agent --runtime python3.12

# from bedrock_agentcore.runtime import BedrockAgentCoreApp
# from strands import Agent
# from strands.models import BedrockModel

# # Step 1: Define the model
# model = BedrockModel(
#     model_id="amazon.nova-micro-v1:0",
# )

# # Step 2: Create the agent
# agent = Agent(model=model)

# # Step 3: Define the AgentCore Runtime application
# app = BedrockAgentCoreApp()

# @app.entrypoint
# def invoke(payload):
#     """
#     Payload example:
#         {
#             "prompt": "Hello, AgentCore!"
#         }

#     Returns:
#         {
#             "result": "<assistant text>"
#         }
#     """
#     user_message = payload.get("prompt", "")
#     response = agent(user_message)
#     return {"result": response}

# if __name__ == "__main__":
#     # Local test only
#     app.run()

from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(data: dict):
    prompt = data.get("prompt", "")
    return {"response": f"Echo: {prompt}"}

if __name__ == "__main__":
    app.run()
