import boto3, json, base64


def call_bedrock(prompt):
    client = boto3.client('bedrock-runtime')
    ModelId="amazon.titan-image-generator-v1"

    #prompt = "picture of very happy golden retriever"

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

    ## TODO FIGURE OUT HOW TO GET THE RETURNED BYTES RETURNED AS AN IMAGE.
    base64_image = response_body.get("images")[0]   # get first image
    #decoded = base64.b64encode(base64_image).decode('utf-8')
    base64_bytes = base64_image.encode('ascii')     # convert to ascii bytes
    image_bytes = base64.b64decode(base64_bytes)    # decode these bytes into binary image data bytes.
    return base64_image


def lambda_handler(event, context):

    #print("Received event: " + json.dumps(event, indent=2))

    # extract a query parameter called "prompt" from the input event:
    prompt = event['queryStringParameters']['prompt']
    
    ## TODO: REPLACE THIS HARDCODING WITH CALL TO BEDROCK ONCE BOTO3 IN LAMBDA IS FIXED.
    response = call_bedrock(prompt);
    #response = "This is a hardcoded response."


    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'image/png',  
        },
        'body': response,
        'isBase64Encoded': True,
    }    
