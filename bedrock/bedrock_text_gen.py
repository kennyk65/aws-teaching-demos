import boto3, json

client = boto3.client('bedrock-runtime')
modelId="amazon.titan-text-lite-v1"

def call_bedrock(prompt):

    # if the prompt is empty, set it to a default value
    if not prompt:
        prompt = "What are the top 3 recommended European vacation destinations for extroverts?"

    # Note that the input for the body depends on the selected model
    # This body works for Amazon Titan:
    body = {
        "inputText": f"{prompt}",
        "textGenerationConfig":
        {"temperature": 0, "topP": 0.9, "maxTokenCount": 512, "stopSequences": [] }
        }

    # There is also a streaming option
    response = client.invoke_model(
        contentType="application/json",
        accept="*/*",
        modelId=modelId,
        body=json.dumps(body)  
    )

    return json.loads(response.get('body').read()).get('results')[0].get('outputText')



if __name__ == "__main__":
    result = call_bedrock("When is the next planetary conjunction involving at least three planets?")
    print(result)



# Lambda Handler:
def lambda_handler(event, context):

    # extract a query parameter called "prompt" from the input event:
    prompt = event['queryStringParameters']['prompt']
    
    response = call_bedrock(prompt)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "prompt": prompt,
            "response": response,
        }),
    }
