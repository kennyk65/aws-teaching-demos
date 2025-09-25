# my_agent.py
from bedrock_agentcore import BedrockAgentCoreApp
import boto3, time
from botocore.exceptions import ClientError


logs = boto3.client("logs")
LOG_GROUP = "/aws/bedrock-agentcore/custom"
LOG_STREAM = "agentcore_demo"
_sequence_token = None


def log(msg: str):
    global _sequence_token
    ts = int(time.time() * 1000)

    try:
        # Make sure group and stream exist (ignore if already exist)
        try:
            logs.create_log_group(logGroupName=LOG_GROUP)
        except ClientError:
            pass
        try:
            logs.create_log_stream(logGroupName=LOG_GROUP, logStreamName=LOG_STREAM)
        except ClientError:
            pass

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
        # Fallback so you don't lose messages
        print(f"[log-fallback] {msg} ({e})")



# Minimal "hello world" agent. It does NOT call a model (keeps it simple).
# When run in AgentCore Runtime you'll get runtime/session metrics and logs in CloudWatch.
app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload: dict):

    log("entered entrypoint")
    log(f"payload: {payload}")

    prompt = payload.get("prompt", "world")
    # Return a simple structured response; AgentCore runtime expects JSON-serializable return.
    return {"result": f"Hello, {prompt}!"}

if __name__ == "__main__":
    app.run()
