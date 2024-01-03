import boto3, json
import botocore


print(boto3.__version__)
print(botocore.__version__)

def call_bedrock(prompt):
    client = boto3.client('bedrock-runtime')
    ModelId="amazon.titan-text-lite-v1"

    #prompt = "What are the top 3 recommended European vacation destinations for extroverts?"

    # Note that the input for the body depends on the selected model
    body = {
        "inputText": f"{prompt}",
        "textGenerationConfig":
        {"temperature": 0, "topP": 0.9, "maxTokenCount": 512, "stopSequences": [] }
        }


    # There is also a streaming option
    response = client.invoke_model(
    contentType="application/json",
    accept="*/*",
    modelId=ModelId,
    body=json.dumps(body)  
    )

    completion = json.loads(response.get('body').read()).get('results')[0].get('outputText')
    return completion


def lambda_handler(event, context):

    #print("Received event: " + json.dumps(event, indent=2))

    # extract a query parameter called "prompt" from the input event:
    prompt = event['queryStringParameters']['prompt']
    
    ## TODO: REPLACE THIS HARDCODING WITH CALL TO BEDROCK ONCE BOTO3 IN LAMBDA IS FIXED.
    response = call_bedrock(prompt);
    #response = "This is a hardcoded response."

    return {
        "statusCode": 200,
        "body": json.dumps({
            "prompt": prompt,
            "response": response,
        }),
    }
