# Bedrock AgentCore Runtime - Basic Forecast Agent

This demo deploys a simple Strands agent to **Amazon Bedrock AgentCore Runtime**,
then invokes it to answer a weather forecast question. The forecast is
simulated, not live weather data.

The AgentCore CLI packages this agent as a CodeZip archive, not a Docker image.
The deployment therefore does not build a container image.


## Prerequisites

- The AWS CLI, configured AWS credentials and region, and permission to deploy
  and invoke AgentCore and supporting resources. You also need access to the
  `us.anthropic.claude-sonnet-4-6` Bedrock model.
- Python 3.12 and [uv](https://docs.astral.sh/uv/getting-started/installation/).
- Node.js and npm; Node 22 or later is recommended.
- AgentCore CLI 1.0.3: `npm install -g @aws/agentcore`. Check with
  `agentcore --version`.
- AWS CDK CLI 2.1148.1 or later: follow the
  [CDK installation instructions](https://docs.aws.amazon.com/cdk/v2/guide/getting-started.html)
  and check `cdk --version`.
- A [CDK bootstrap](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html)
  in the target account and region. This project uses the `cdksetup` qualifier.
  Bootstrap is shared across projects and creates IAM roles; by default the
  CloudFormation execution role has `AdministratorAccess`. Review its
  permissions before setting it up.

CloudWatch Transaction Search is needed for full AgentCore observability; see
[Enabling AgentCore observability](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-configure.html#observability-configure-builtin).
AgentCore CLI 1.0.3 attempts to enable it during deployment if it is not already
active, affecting shared regional observability settings.


Clone this repository and change into `bedrock/agentcore/demo-runtime-new-cli`.

Install the project's CDK dependencies before building or deploying. Set up
the Python environment for running and testing the agent locally:
```bash
npm install --prefix agentcore/cdk
uv sync --project app/forecast_agent
```



## Demo

### AgentCore Runtime Deployment

From the project folder, run:

```bash
# Build the deployable artifact and deploy.
# WARNING - this can take several minutes without visual feedback.
agentcore deploy --skip-bootstrap

# Show the deployed resources.
agentcore status
```

Then invoke the agent in Git Bash:

```bash
agentcore invoke --runtime forecast_agent --payload '{"actor_id":"ken","prompt":"What is the weather forecast for Seattle, WA?"}' --session-id ken-session-001-abcdefghijklmnopqrstuvwxyz123
```

The response contains the forecast, actor ID, and session ID. Open the
[AgentCore console](https://us-west-2.console.aws.amazon.com/bedrock-agentcore/agents)
to show the Runtime and its endpoint; select your region if it is not
`us-west-2`.

To redeploy after changing the agent, run `agentcore deploy --skip-bootstrap`
again.

## Cleanup

Save a copy of `agentcore/agentcore.json` before cleanup: the first command
empties its resource configuration. Then, from the project folder, run:

```bash
# Remove the resources from the local project configuration.
agentcore remove all --yes

# Delete the project's CloudFormation stack and its resources.
agentcore deploy --yes --skip-bootstrap
```

Despite its name, `agentcore deploy` deletes the target stack when the
project configuration contains no resources; it does not update the stack.
The `--yes` flag confirms that deletion. This does not remove the shared CDK
bootstrap stack. Check for retained resources and charges in your account.

After cleanup, restore `agentcore/agentcore.json` from your saved copy before
deploying again. The original `demo-runtime` project is separate and should
not be removed.
