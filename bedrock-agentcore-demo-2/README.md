## Bedrock AgentCore Demo 🤖

This demo establishes a very simple Agent built with the **Strands** framework, utilizing an Amazon Bedrock model.  The main purpose is to highlight **Bedrock AgentCore**. It shows the steps to create and deploy a basic agent which calls a model, (primatively) manages chat memory, and demonstrates the **CloudWatch GenAI Observability** feature for AgentCore.

---

### Prerequisite

You will need:

* **Python** installed (3.12 or greater).
* The **AWS SDK**.
* The **agentcore CLI**, installed by running `pip install amazon-bedrock-agentcore-cli`.
* An IDE like **VSCode** works best, but is not required.
* Ability to call the *us.amazon.nova-micro-v1:0* model.
* Enable CloudWatch Signal Spans: Go to the console for **X-Ray settings** at [CloudWatch Transaction Search settings (us-west-2)](https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#xray:settings/transaction-search) (us-west-2 assumed). 
    * Currently, there is no command-line equivalent: find **‘Transaction Search’**, click **edit**, and **enable** it. Give this a few minutes. *(TODO - FIND CLI EQUIVALENT WHEN AVAILABLE)*

---

### Setup

1.  Clone / Copy `https://github.com/kennyk65/aws-teaching-demos`.
2.  `CD` into the `/bedrock-agentcore-demo-2` folder.

Run the following from this folder to set everything up:

```bash
aws cloudformation deploy --stack-name agentcore-weather-demo --template-file agentcore-weather-demo.yml --capabilities CAPABILITY_NAMED_IAM
$outputs = aws cloudformation describe-stacks --stack-name agentcore-weather-demo --query "Stacks[0].Outputs" --output json | ConvertFrom-Json
$role_arn = ($outputs | Where-Object OutputKey -eq 'RoleArn').OutputValue
$repo_uri = ($outputs | Where-Object OutputKey -eq 'RepositoryUri').OutputValue
Write-Host "The role is $role_arn"
Write-Host "The ECR Repository URI is $repo_uri"
```

* This establishes the Role, ECR repository, and environment variables needed later.

---

### Demo

#### Local Deployment (optional)

If you want to run the agent locally (no real reason to, other than to prove that it works), run this command:
```
python .\weather_agent.py
```

In a separate command shell, post this:
```
curl -X POST http://localhost:8080/invocations -H "Content-Type: application/json" -d "{\"user_id\": \"ken\", \"prompt\": \"What is the current temperature in Seattle, WA?  Use Farenheit temperature scale.\"}"

```

Stop the python execution when done.

#### AgentCore Runtime Deployment

Assuming you are still in the same folder as before, run these commands one at a time. See the comments for explanation on what each is doing:


```
# This establishes a new agent in AgentCore.
# The name and source file are given, as well as the execution role and
# ECR repository to use. However, it does not actually build / start the agent.
agentcore configure -n weather_agent -e weather_agent.py --execution-role $role_arn --ecr $repo_uri --requirements-file requirements.txt
```
When asked about *Configure OAuth authorizer instead? (yes/no)*, say no.

Then run these commands one at a time:
```

# This simple command:
# - builds a Docker container (using CodeBuild),
# - pushes an image to our ECR repository,
# - launches the agent,
# - creates an endpoint:
agentcore launch

# Invoke multiple times to demonstrate memory (using IAM for authentication)
agentcore invoke '{"user_id":"ken","prompt":"What is the weather in Seattle, WA?"}' 
agentcore invoke '{"user_id":"ken","prompt":"Do you think water will freeze there?"}' 
```

* Open the management console to see the agent running: https://us-west-2.console.aws.amazon.com/bedrock-agentcore/agents (assuming you are running in us-west-2).

* **Observability:** Open the [CloudWatch GenAI Observability](https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#/gen-ai-observability/agent-core/agents), (again, assuming you are running in us-west-2.)

* With the "Agents" tab selected, you can: 

    * Expand "view details" and see "Agent metrics".  Basic.

    * Expand "Runtime metrics" and see better metrics.  (no idea why they are separated).

    * **Traces** Down in the list of Agents, click the **DEFAULT** link.  

        * Find the "Traces" tab.  Click on one of the traces.  Two fun things you can see in here

            * Click the "Timeline" tab, show the order of events

            * Expand "Trajectory" and see a call graph. 

---

### Cleanup
Assuming you are still in the same folder as before, run these commands:

```
agentcore destroy -a weather_agent --force

aws cloudformation delete-stack --stack-name agentcore-weather-demo
```

* **IMPORTANT!! ⚠️ EXPENSIVE!!! ⚠️** Disable CloudWatch Signal Spans:
    * Go to the console for X-Ray settings at https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#xray:settings/transaction-search (us-west-2 assumed). 
    * Find ‘Transaction Search’, click edit, and disable it. Give this a few minutes. (TODO - FIND CLI EQUIVALENT WHEN AVAILABLE)
