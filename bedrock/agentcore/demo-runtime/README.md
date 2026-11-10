# Bedrock AgentCore Runtime - Basic Forecast Agent

This demo establishes a very simple Agent built with the Strands framework, utilizing an Amazon Bedrock model. The main purpose is to highlight **Amazon Bedrock AgentCore Runtime**. It shows the steps to create and deploy a basic agent which calls a model and answers simple questions about the weather forecast for a given location.

This is intentionally minimal. Later demos will layer on additional AgentCore capabilities such as Identity, Gateway, Memory, and Observability. This one focuses only on building, deploying, and invoking an agent on AgentCore Runtime.

## Prerequisite

You will need:

- Python installed (3.12 or greater).
- The AWS SDK.
- The agentcore CLI, installed by running `pip install amazon-bedrock-agentcore-cli`.
- An IDE like VSCode works best, but is not required.
- Ability to call the `us.anthropic.claude-sonnet-4-6` model.

## Setup

1. Clone / Copy https://github.com/kennyk65/aws-teaching-demos.
2. CD into bedrock/agentcore/demo-runtime folder.

Run the following from this folder to set everything up.

(Mac/Linux):

```bash
aws cloudformation deploy --stack-name agentcore-weather-demo --template-file agentcore-weather-demo.template.yml --capabilities CAPABILITY_NAMED_IAM

role_arn=$(aws cloudformation describe-stacks --stack-name agentcore-weather-demo --query "Stacks[0].Outputs[?OutputKey=='RoleArn'].OutputValue | [0]" --output text)
repo_uri=$(aws cloudformation describe-stacks --stack-name agentcore-weather-demo --query "Stacks[0].Outputs[?OutputKey=='RepositoryUri'].OutputValue | [0]" --output text)

echo "The role is $role_arn"
echo "The ECR Repository URI is $repo_uri"
```

This establishes the Role, ECR repository, and environment variables needed later.


## Demo

### Local Testing (optional)

If you want to test the agent locally (no real reason to, other than to prove that it works), run the pytest command:

```bash
pytest ./test/test_forecast_agent.py
```

If you want to see `print()` output while running pytest:

```bash
pytest -s ./test/test_forecast_agent.py
```

...or in VSCode, right-click the `test_forecast_agent.py` file and say "Run Test".

### AgentCore Runtime Deployment

Assuming you are still in the same folder as before, run these commands one at a time. See the comments for explanation on what each is doing:

```bash
# This establishes a new agent in AgentCore.
# The name and source file are given, as well as the execution role and
# ECR repository to use. However, it does not actually build / start the agent.
agentcore configure -n forecast_agent -e forecast_agent.py --execution-role $role_arn --ecr $repo_uri --requirements-file requirements.txt
```

- When asked about `Configure OAuth authorizer instead? (yes/no)`, say `no`.
- If asked about `Configure request header allowlist? (yes/no) [no]`, just press enter.

Then run:

```bash
# This simple command:
# - builds a Docker container (using CodeBuild),
# - pushes an image to our ECR repository,
# - launches the agent,
# - creates an endpoint:
agentcore launch -a forecast_agent --auto-update-on-conflict
```

Then invoke the agent:

```bash
agentcore invoke -a forecast_agent '{"actor_id":"ken","prompt":"What is the weather forecast for Seattle, WA?"}' --session-id ken-session-001-abcdefghijklmnopqrstuvwxyz123
```

Open the management console to see the agent running: https://us-west-2.console.aws.amazon.com/bedrock-agentcore/agents (assuming you are running in us-west-2).
Find the Endpoints list.

# AgentCore Identity Demo

If you'd like to demonstrate one agent calling another, show the `weather_agent.py`.  Show the tool that gets the weather forecast by calling the other agent.

Make a new weather agent:

```bash
agentcore configure -n weather_agent -e weather_agent.py --execution-role $role_arn --ecr $repo_uri --requirements-file requirements.txt
agentcore launch -a weather_agent --auto-update-on-conflict
```

- When asked about `Configure OAuth authorizer instead? (yes/no)`, say `no`.
- If asked about `Configure request header allowlist? (yes/no) [no]`, just press enter.

Then invoke the agent:

```bash
agentcore invoke -a weather_agent '{"actor_id":"ken","prompt":"What is the weather in Seattle, WA right now and for the next few days?"}' --session-id ken-session-001-abcdefghijklmnopqrstuvwxyz123
```

Open the management console to see the agent running: https://us-west-2.console.aws.amazon.com/bedrock-agentcore/agents (assuming you are running in us-west-2).

# AgentCore Gateway Demo

If you'd like to demo the AgentCore Gateway, we'll just need to create an API Gateway with some Lambdas to use as targets.  Update the stack with the CreateGateway=true tag.

```
aws cloudformation deploy --stack-name agentcore-weather-demo --template-file agentcore-weather-demo.template.yml --capabilities CAPABILITY_NAMED_IAM --parameter-overrides CreateGateway=true

agentcore configure -n weather_agent_gateway -e weather_agent_gateway.py --execution-role $role_arn --ecr $repo_uri --requirements-file requirements.txt
agentcore launch -a weather_agent_gateway --auto-update-on-conflict
```

- When asked about `Configure OAuth authorizer instead? (yes/no)`, say `no`.
- If asked about `Configure request header allowlist? (yes/no) [no]`, just press enter.

Then invoke the agent:

```bash
agentcore invoke -a weather_agent_gateway '{"actor_id":"ken","prompt":"What is the weather in Seattle, WA right now and for the next few days?"}' --session-id ken-session-001-abcdefghijklmnopqrstuvwxyz123
```

* Things to demo:
    * Show the 'defining tools' section of the code.
    * Show the gateway at  https://us-west-2.console.aws.amazon.com/bedrock-agentcore/toolsAndGateways 
    * Observability shows tool use that uses the gateway: https://us-west-2.console.aws.amazon.com/bedrock-agentcore/observability?region=us-west-2 

# AgentCore Memory Demo

This version uses the same Gateway tools and adds AgentCore short-term Memory.

```bash
aws cloudformation deploy --stack-name agentcore-weather-demo --template-file agentcore-weather-demo.template.yml --capabilities CAPABILITY_NAMED_IAM --parameter-overrides CreateGateway=true CreateMemory=true

agentcore configure -n weather_agent_memory -e weather_agent_memory.py --execution-role $role_arn --ecr $repo_uri --requirements-file requirements.txt
agentcore launch -a weather_agent_memory --auto-update-on-conflict
```

Invoke the same actor and session twice. The second question relies on the
temperature returned in the first answer:

```bash
agentcore invoke -a weather_agent_memory '{"actor_id":"ken","prompt":"What is the current temperature in Seattle, WA?"}' --session-id ken-session-001-abcdefghijklmnopqrstuvwxyz123
agentcore invoke -a weather_agent_memory '{"actor_id":"ken","prompt":"Would water freeze at that temperature?"}' --session-id ken-session-001-abcdefghijklmnopqrstuvwxyz123
```

Demonstrate session isolation; if Bob asks about freezing water the result is confusion:

```
agentcore invoke -a weather_agent_memory '{"actor_id":"bob","prompt":"Would water freeze there?"}' --session-id bob-session-001-abcdefghijklmnopqrstuvwxyz123
```


## Cleanup

Assuming you are still in the same folder as before, run these commands:

```bash
agentcore destroy -a weather_agent --force
agentcore destroy -a forecast_agent --force
agentcore destroy -a weather_agent_gateway --force
agentcore destroy -a weather_agent_memory --force

aws cloudformation delete-stack --stack-name agentcore-weather-demo
```
