# my_agent.py
from bedrock_agentcore import BedrockAgentCoreApp

# Minimal "hello world" agent. It does NOT call a model (keeps it simple).
# When run in AgentCore Runtime you'll get runtime/session metrics and logs in CloudWatch.
app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload: dict):
    prompt = payload.get("prompt", "world")
    # Return a simple structured response; AgentCore runtime expects JSON-serializable return.
    return {"result": f"Hello, {prompt}!"}

if __name__ == "__main__":
    app.run()
