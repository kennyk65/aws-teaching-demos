## Bedrock AgentCore Demo 🤖

This demo establishes a very simple Agent using **Bedrock AgentCore**. It shows the steps to create and deploy a basic agent which calls a model, (primatively) manages chat memory, and demonstrates the **CloudWatch GenAI Observability** feature for AgentCore.

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
aws cloudformation deploy --stack-name agentcore-demo-v2 --template-file agentcore-demo-v2.yml --capabilities CAPABILITY_NAMED_IAM
$outputs = aws cloudformation describe-stacks --stack-name agentcore-demo-v2 --query "Stacks[0].Outputs" --output json | ConvertFrom-Json
$env:ROLE_ARN = ($outputs | Where-Object OutputKey -eq 'RoleArn').OutputValue
$env:REPO_URI = ($outputs | Where-Object OutputKey -eq 'RepositoryUri').OutputValue
Write-Host "The role is $env:ROLE_ARN"
Write-Host "The ECR Repository URI is $env:REPO_URI"
```

* This establishes the Role, ECR repository, and environment variables needed later.

---

### Demo
Assuming you are still in the same folder as before, run these commands one at a time. See the comments for explanation on what each is doing:


```
# This establishes a new agent in AgentCore.
# The name and source file are given, as well as the execution role and
# ECR repository to use. However, it does not actually build / start the agent.
agentcore configure -n agentcore_demo_v2 -e my_agent_v2.py --execution-role %ROLE_ARN% --ecr %REPO_URI% --requirements-file requirements.txt

# This simple command:
# - builds a Docker container (using CodeBuild),
# - pushes an image to our ECR repository,
# - launches the agent,
# - creates an endpoint:
agentcore launch

# Invoke multiple times to demonstrate memory (using IAM for authentication)
agentcore invoke '{"user_id":"ken","prompt":"List out the 5 great lakes"}'
agentcore invoke '{"user_id":"ken","prompt":"Which one is the deepest?"}'
agentcore invoke '{"user_id":"ken","prompt":"Which states / provinces does it touch?"}'

```

* Open the management console to see the agent running: https://us-west-2.console.aws.amazon.com/bedrock-agentcore/agents (assuming you are running in us-west-2).

* **Observability:** Open the CloudWatch GenAI Observability link: https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#/gen-ai-observability/model-invocation

---

### Cleanup
Assuming you are still in the same folder as before, run these commands:

```
agentcore destroy -a agentcore_demo_v2 --force

aws cloudformation delete-stack --stack-name agentcore-demo-v2
```

* **IMPORTANT!! ⚠️ EXPENSIVE!!! ⚠️** Disable CloudWatch Signal Spans:
    * Go to the console for X-Ray settings at https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#xray:settings/transaction-search (us-west-2 assumed). 
    * Find ‘Transaction Search’, click edit, and disable it. Give this a few minutes. (TODO - FIND CLI EQUIVALENT WHEN AVAILABLE)
