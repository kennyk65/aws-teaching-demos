import boto3, json

client = boto3.client('bedrock-agent-runtime')
modelId="amazon.titan-text-lite-v1"

def call_bedrock(prompt):
    # if the prompt is empty, set it to a default value
    if not prompt:
        prompt = "What are the top 3 most popular course titles based on 'Students (OPS)'? Show the sum of 'Students (OPS)' for each."

    # Call the knowledge base:
    # TODO: REMOVE HARD-CODING OF KNOWLEDGEBASEID
    # TODO: PRESENTLY NOT RESPONDING WITH INFORMATION FROM KNOWLEDGEBASE
    response = client.retrieve_and_generate(
        input={
            'text': prompt
        },
        retrieveAndGenerateConfiguration={
            'type': 'KNOWLEDGE_BASE',
            'knowledgeBaseConfiguration': {
                'knowledgeBaseId': 'YSP1FFNJUU',
                'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-instant-v1'
            }
        }
    )

    return response['output']['text']



if __name__ == "__main__":
    result = call_bedrock("What are the top 3 most popular course titles based on 'Students (OPS)'? Show the sum of 'Students (OPS)' for each.")
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
