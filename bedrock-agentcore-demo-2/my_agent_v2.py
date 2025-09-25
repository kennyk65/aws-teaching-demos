# my_agent_v2.py
from bedrock_agentcore import BedrockAgentCoreApp
import boto3, time, os, json
from botocore.exceptions import ClientError

# CloudWatch Logs setup
logs = boto3.client("logs")
LOG_GROUP = "/aws/bedrock-agentcore/custom"
LOG_STREAM = "agentcore_demo_v2"
_sequence_token = None

def log(msg: str):
    global _sequence_token
    ts = int(time.time() * 1000)
    try:
        try: logs.create_log_group(logGroupName=LOG_GROUP)
        except ClientError: pass
        try: logs.create_log_stream(logGroupName=LOG_GROUP, logStreamName=LOG_STREAM)
        except ClientError: pass

        kwargs = {
            "logGroupName": LOG_GROUP,
            "logStreamName": LOG_STREAM,
            "logEvents": [{"timestamp": ts, "message": msg}],
        }
        if _sequence_token:
            kwargs["sequenceToken"] = _sequence_token

        resp = logs.put_log_events(**kwargs)
        _sequence_token = resp.get("nextSequenceToken")

    except Exception as e:
        print(f"[log-fallback] {msg} ({e})")

# Minimal memory dictionary to store conversation history
memory = {}

# Initialize Bedrock client
bedrock = boto3.client("bedrock-runtime")

app = BedrockAgentCoreApp()



# simple in-memory store keyed by user_id
memory = {}

@app.entrypoint
def invoke(payload: dict):
    user_id = payload.get("user_id", "default")
    user_input = payload.get("prompt", "Hello")

    # initialize memory for user if not exists
    if user_id not in memory:
        memory[user_id] = []

    # add the new user message to memory
    memory[user_id].append({
        "role": "user",
        "content": [{"text": user_input}]
    })

    # build messages array for the model (full history)
    model_input = {"messages": memory[user_id]}

    log(f"Sending to model: {json.dumps(model_input)}")

    try:
        response = bedrock.invoke_model(
            modelId="us.amazon.nova-micro-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(model_input)
        )

        # parse JSON response
        body_str = response["body"].read().decode("utf-8")
        body = json.loads(body_str)

        # extract assistant message (Nova puts it under output.message)
        assistant_message = body.get("output", {}).get("message", {})
        memory[user_id].append(assistant_message)

        # pull text for return convenience
        model_output = ""
        for c in assistant_message.get("content", []):
            if "text" in c:
                model_output += c["text"]

    except Exception as e:
        model_output = f"[Error invoking model: {e}]"
        log(model_output)

    return {
        "result": model_output,
        "conversation_history": memory[user_id]
    }




if __name__ == "__main__":
    app.run()
