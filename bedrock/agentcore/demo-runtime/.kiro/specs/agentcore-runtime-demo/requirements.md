# Requirements Document

## Introduction

This feature delivers a minimal classroom demo of **Amazon Bedrock AgentCore Runtime**. It is a focused, stripped-down version of the existing [`bedrock-agentcore-demo-2`](https://github.com/kennyk65/aws-teaching-demos/tree/master/bedrock-agentcore-demo-2) demo.

The existing demo bundles AgentCore Memory (short-term conversation memory, session isolation, lifecycle hooks). That adds setup time and conceptual overhead that distracts from the single idea this demo wants to teach first: how to build, deploy, and invoke a basic agent on AgentCore Runtime.

The new demo keeps everything that makes the original work as a weather agent, but removes Memory from the default experience. Memory infrastructure is made **conditional in the CloudFormation template and defaults to not being created**, so the demo stays deployable and cheap, while leaving a clean seam for a later, dedicated Memory demo. Subsequent demos will layer on Identity, Gateway, Memory, and Observability.

The agent is built with the Strands framework, backed by an Amazon Bedrock model, and answers simple weather questions.

## Requirements

### Requirement 1: Deployable basic agent on AgentCore Runtime

**User Story:** As an instructor, I want a basic agent that deploys to Amazon Bedrock AgentCore Runtime, so that I can demonstrate the core build-and-deploy workflow without extra features.

#### Acceptance Criteria

1. WHEN the demo is deployed following the README THEN the system SHALL provision an AgentCore execution IAM role and an ECR repository via CloudFormation.
2. WHEN `agentcore configure` and `agentcore launch` are run as documented THEN the system SHALL build a container, push it to ECR, launch the agent, and create an endpoint.
3. WHEN the agent is invoked THEN the system SHALL respond using an Amazon Bedrock model through the Strands framework.
4. WHEN the agent is deployed THEN the system SHALL NOT require any AgentCore Memory resource to exist.

### Requirement 2: Weather question answering

**User Story:** As a user of the demo, I want to ask simple questions about the weather, so that I can see the agent reason and use tools.

#### Acceptance Criteria

1. WHEN a user asks for the weather in a location THEN the agent SHALL return a weather response for that location.
2. WHEN the agent produces a temperature for the user THEN the agent SHALL present it in Fahrenheit.
3. WHEN a weather-related question requires a Celsius-to-Fahrenheit conversion THEN the agent SHALL use the conversion tool rather than exposing Celsius to the user.
4. WHEN a user asks whether water will freeze given a temperature THEN the agent SHALL reason using the freezing point of water (32°F / 0°C) to answer.

### Requirement 3: Memory removed from default experience, retained as an optional condition

**User Story:** As an instructor, I want Memory excluded by default but available behind a switch, so that this demo stays simple while a future demo can enable Memory without reworking the template.

#### Acceptance Criteria

1. WHEN the CloudFormation template is deployed with default parameters THEN the system SHALL NOT create an AgentCore Memory resource.
2. WHEN the template provides a parameter controlling Memory creation THEN that parameter SHALL default to `false`.
3. IF the Memory parameter is set to `true` THEN the template SHALL create the AgentCore Memory resource and expose its ID as an output.
4. WHEN Memory is not created THEN the stack SHALL NOT emit a Memory-related output that would error on a missing resource.
5. WHEN the agent code runs THEN it SHALL NOT import, initialize, hook into, or depend on any Memory module or Memory client.

### Requirement 4: Clean, memory-free source files

**User Story:** As a learner reading the demo, I want the source to contain only what the basic demo needs, so that the code is easy to follow.

#### Acceptance Criteria

1. WHEN the agent source (`weather_agent.py`) is reviewed THEN it SHALL contain no references to memory hooks, memory providers, session restore/persist logic, or the `memory` module.
2. WHEN the project files are reviewed THEN the standalone `memory.py` module SHALL NOT be present.
3. WHEN `requirements.txt` is reviewed THEN it SHALL list only dependencies needed for the basic agent, with any memory-only dependencies removed.
4. WHEN the entrypoint handles a request THEN it SHALL still accept `prompt` and `actor_id` and return a result along with `session_id` and `actor_id`, without relying on memory behavior.

### Requirement 5: Local testing without memory

**User Story:** As a developer, I want to run a local test of the agent, so that I can confirm it works before deploying.

#### Acceptance Criteria

1. WHEN the test suite (`test_weather_agent.py`) is reviewed THEN it SHALL NOT include the memory-isolation test.
2. WHEN `pytest ./test_weather_agent.py` is run THEN it SHALL exercise the weather/freezing-point behavior of the agent.
3. WHEN the single-invocation weather test runs THEN it SHALL assert the agent returns a non-error response that addresses the requested location.

### Requirement 6: Documentation without memory

**User Story:** As a user following the demo, I want a README that matches the memory-free demo, so that the steps I run align with what is deployed.

#### Acceptance Criteria

1. WHEN the README is reviewed THEN it SHALL describe setup, local testing, deployment, invocation, and cleanup for the basic agent.
2. WHEN the README is reviewed THEN it SHALL NOT include steps, prompts, or sections about observing, testing, or selecting Memory.
3. WHEN the README lists prerequisites and commands THEN they SHALL be consistent with the memory-free template and agent code.
4. WHEN the README references future capabilities THEN it MAY note that Identity, Gateway, Memory, and Observability are planned for later demos, without requiring them now.
