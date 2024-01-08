import boto3, json, base64


def call_bedrock(prompt):
    client = boto3.client('bedrock-runtime')
    ModelId="amazon.titan-image-generator-v1"

    # Note that the input for the body depends on the selected model
    body = { 
        "textToImageParams": {
            "text": f"{prompt}"
            },
        "taskType": "TEXT_IMAGE",
        "imageGenerationConfig":{
            "cfgScale":8,
            "seed":0,
            "quality":"standard",
            "width":512,
            "height":512,
            "numberOfImages":1
        }
    }

    # There is also a streaming option
    response = client.invoke_model(
        modelId=ModelId,
        body=json.dumps(body)  
    )

    print(response)
    response_body = json.loads(response.get("body").read())

    # The returned bytes are base64 encoded:
    base64_image = response_body.get("images")[0]
    return base64_image


def lambda_handler(event, context):

    #print("Received event: " + json.dumps(event, indent=2))

    # extract a query parameter called "prompt" from the input event:
    prompt = "picture of two happy golden retrievers playing tug-o-war"
    query_parameters = event.get('queryStringParameters')
    if query_parameters:
        prompt = query_parameters.get('prompt',prompt)

    response = call_bedrock(prompt);

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'image/png',  
        },
        'body': response,
        'isBase64Encoded': True,
    }    
