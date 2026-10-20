# Design Document

## Overview

This demo is a trimmed derivative of [`bedrock-agentcore-demo-2`](https://github.com/kennyk65/aws-teaching-demos/tree/master/bedrock-agentcore-demo-2). The goal is the simplest possible end-to-end example of an agent running on **Amazon Bedrock AgentCore Runtime**: a Strands agent, backed by a Bedrock model, exposing two weather tools, deployed as a container and invoked through an AgentCore endpoint.

The one structural change from the source demo is the removal of **AgentCore Memory** from the default path:

- In the application code and tests, Memory is removed entirely.
- In the CloudFormation template, Memory is retained but guarded by a `Condition` that defaults to disabled, so a future Memory demo can flip one parameter instead of re-authoring infrastructure.

Everything else (IAM execution role, ECR repository, model, tools, entrypoint contract, deploy/invoke/cleanup flow) is preserved so the demo behaves like the original minus memory.

### Design goals

- Keep the deployable surface area minimal and cheap (no Memory resource created by default).
- Preserve the exact developer workflow from the original README (configure → launch → invoke → destroy), minus memory prompts.
- Leave a clean, obvious seam for re-enabling Memory later.
- Keep the agent stateless per invocation — correct behavior must not depend on cross-request memory.

## Architecture

```
┌──────────────┐     agentcore invoke      ┌───────────────────────────────┐
│  Instructor  │ ────────────────────────▶ │  AgentCore Runtime Endpoint    │
│  / CLI       │                           │  (container from ECR image)    │
└──────────────┘                           │                                │
                                           │  BedrockAgentCoreApp (HTTP)    │
                                           │        │ @app.entrypoint        │
                                           │        ▼                        │
                                           │   build_agent() → Strands Agent │
                                           │        │  tools:                │
                                           │        │   - weather            │
                                           │        │   - celcius_to_faren.  │
                                           │        ▼                        │
                                           │   BedrockModel (Claude Sonnet) │
                                           └───────────────┬────────────────┘
                                                           │ bedrock:InvokeModel
                                                           ▼
                                                 ┌───────────────────┐
                                                 │  Amazon Bedrock    │
                                                 └───────────────────┘

Provisioned by CloudFormation:
  - AgentCoreExecutionRole (IAM)       ← always
  - AgentCoreECRRepo (ECR)             ← always
  - AgentCoreMemory (Memory)           ← only IF CreateMemory == true  (default false)
```

### Request flow

1. The CLI (or console) sends a payload `{"actor_id": ..., "prompt": ...}` with a session id to the endpoint.
2. `BedrockAgentCoreApp` routes the request to the `@app.entrypoint` function.
3. The entrypoint builds a fresh Strands `Agent` (model + tools, no hooks) and invokes it with the user prompt.
4. The agent reasons, optionally calls the `weather` and `celcius_to_farenheit` tools, and returns an answer in Fahrenheit.
5. The entrypoint returns `{"result", "session_id", "actor_id"}`.

Because there are no memory hooks, each invocation is independent. The `session_id`/`actor_id` are still echoed back for continuity with the original contract and for future use.

## Components and File Plan

The project folder (`demo-runtime`) will contain the following files, all adapted from the source demo.

### 1. `agentcore-weather-demo.template.yml` (CloudFormation)

Adapted from the source template. Changes:

- **Add parameter** `CreateMemory` (type `String`, `AllowedValues: ["true", "false"]`, `Default: "false"`). A string parameter with allowed values is used rather than relying on a raw boolean, since CloudFormation parameters are string-typed and this keeps the condition explicit.
- **Add condition** `ShouldCreateMemory: !Equals [!Ref CreateMemory, "true"]`.
- **Keep** `AgentCoreExecutionRole` and `AgentCoreECRRepo` unchanged and unconditional.
- **Guard the Memory resource**: `AgentCoreMemory` gets `Condition: ShouldCreateMemory`, so it is only created when `CreateMemory=true`.
- **Keep** the `MemoryName` parameter (only meaningful when memory is created; harmless otherwise).
- **IAM policy decision**: retain the `bedrock-agentcore:*Memory / *Memories / *Events / *Event` statement in the execution role. It is permission-only (no resource created) and keeps the role ready for the future Memory demo. This is called out explicitly as an intentional choice; an alternative is to also condition the policy statement, but that complicates the template for no functional gain while Memory is off.
- **Outputs**: keep `RoleArn`, `RoleName`, `RepositoryUri` unconditional. Make the `MemoryId` output `Condition: ShouldCreateMemory` so the stack does not try to read `MemoryId` from a resource that was not created (satisfies Requirement 3.4).

### 2. `weather_agent.py` (Agent entrypoint)

Adapted from the source. Changes:

- **Remove** `from memory import AgentCoreMemory, AgentCoreMemoryHookProvider`.
- **Remove** the `memory = AgentCoreMemory()` initialization.
- **Simplify** `build_agent`: drop the `session_id`/`actor_id` hook-provider parameters and the `hooks=[...]` argument. It becomes a simple factory that returns an `Agent` with `model`, `tools`, and `system_prompt`.
- **Update the system prompt**: keep the weather/Fahrenheit/freezing-point guidance; remove the two lines that instruct the model to use session memory ("Treat prior messages in this same session as available short-term memory." and the "answer from session memory" line), since there is no memory.
- **Keep** the entrypoint contract intact: still read `actor_id` and `prompt` from the payload, still derive `session_id` from `context.session_id or actor_id`, still return `{"result", "session_id", "actor_id"}`. This preserves the public shape without depending on memory.
- **Keep** both tools unchanged: `weather(location)` (returns the hard-coded `"Sunny and -5 degrees Celsius"`) and `celcius_to_farenheit(celcius)`.
- **Keep** the model id and `BedrockModel` configuration unchanged.

### 3. `requirements.txt`

Adapted from the source list:

```
bedrock-agentcore==1.10.0
strands-agents
bedrock-agentcore-starter-toolkit==0.3.9
aws-opentelemetry-distro>=0.10.0
boto3
```

Review outcome: none of these packages are memory-only. `bedrock-agentcore` provides both the runtime app and the memory client, but it is required for the runtime app itself, so it stays. The result is that `requirements.txt` is effectively unchanged, which satisfies Requirement 4.3 (no *memory-only* dependency remains, because there was none to remove). This is noted so the "unchanged" file is a deliberate, verified decision rather than an oversight.

### 4. `memory.py`

**Removed.** The standalone memory module is not copied into this demo (Requirement 4.2). With the agent no longer importing it, it has no consumers.

### 5. `test_weather_agent.py`

Adapted from the source test file. Changes:

- **Keep** `test_invoke` — but review its assertions against the memory-free agent:
  - The first prompt asks for the current temperature in Seattle and asserts the response contains `"Seattle"` and `"23"`. The `weather` tool returns `-5°C`, which converts to `23°F`, so the `"23"` assertion still holds via the conversion tool.
  - The second prompt ("Do you think water will freeze there?") originally relied on session memory to know the location/temperature. Without memory, the agent will not recall the prior turn. **Design decision:** revise this follow-up so it is self-contained — ask the freezing question with the temperature supplied in the same prompt (e.g., "If it is 23°F outside, will water freeze?"), so the test validates freezing-point reasoning without depending on memory. The semantic-comparison helpers (`_cosine_similarity`, `_semantic_compare`, etc.) are retained to validate the freezing answer.
- **Remove** `test_memory_isolation_across_users_and_sessions` entirely (Requirement 5.1).
- **Keep** the `FakeContext` helper and the token/similarity utilities used by the retained test.

### 6. `README.md`

New README, essentially the source README minus memory. Structure:

- **Title / intro**: basic agent on AgentCore Runtime; note Memory/Identity/Gateway/Observability are planned for later demos.
- **Prerequisites**: Python 3.12+, AWS SDK, `agentcore` CLI (`pip install amazon-bedrock-agentcore-cli`), ability to call the chosen Bedrock model. Remove the "Enable CloudWatch Signal Spans / Transaction Search" observability prerequisite (that belongs to the later Observability demo) unless kept purely as optional; default is to omit it to keep the basic demo clean.
- **Setup**: `aws cloudformation deploy ...` (default params, so no Memory). Capture `role_arn` and `repo_uri` outputs. Remove the "It takes a few minutes to create AgentCore Memory" note.
- **Local testing**: `pytest ./test_weather_agent.py` (and `-s` variant). No memory-isolation description.
- **Deployment**: `agentcore configure ...` then `agentcore launch --auto-update-on-conflict`. Remove the "If asked to select memory, choose the only option…" instruction, since no memory resource exists.
- **Invoke**: single weather invocation example. Remove the two-session "different short-term memory" comparison demo.
- **Cleanup**: `agentcore destroy -a weather_agent --force` and `aws cloudformation delete-stack ...`.

## Data Models

### Invocation payload (input)

| Field      | Type   | Required | Notes                                  |
|------------|--------|----------|----------------------------------------|
| `prompt`   | string | no       | User question; defaults to `"Hello"`.  |
| `actor_id` | string | no       | Caller identity; defaults to `"default"`. |

### Invocation result (output)

| Field        | Type   | Notes                                             |
|--------------|--------|---------------------------------------------------|
| `result`     | string | Agent's answer, or `[Error invoking model: ...]`. |
| `session_id` | string | `context.session_id` or falls back to `actor_id`. |
| `actor_id`   | string | Echoed from the payload.                          |

### CloudFormation parameters

| Parameter     | Type   | Default           | Purpose                                     |
|---------------|--------|-------------------|---------------------------------------------|
| `AgentName`   | String | `weather_agent`   | Names the role and ECR repo.                |
| `MemoryName`  | String | `weather_memory`  | Name used only when Memory is created.      |
| `CreateMemory`| String | `false`           | `"true"`/`"false"` gate for the Memory resource. |

## Error Handling

- The entrypoint wraps agent invocation in a `try/except`. On failure it returns `result = "[Error invoking model: <e>]"` and logs the traceback, preserving the original behavior. Tests assert the result does **not** start with that error prefix.
- No memory means no memory-related failure modes (missing resource, inactive status, hook errors) — a simplification that improves demo reliability.
- CloudFormation: with `CreateMemory=false`, the conditional `MemoryId` output is suppressed, avoiding a reference to a non-existent resource.

## Testing Strategy

- **Local unit/integration test** via `pytest ./test_weather_agent.py`:
  - `test_invoke` validates: (a) a non-error response mentioning the requested location with the expected converted temperature (`23°F`), and (b) correct freezing-point reasoning for a self-contained prompt.
  - Semantic similarity helpers guard the freezing answer against uncertain/conditional-only responses.
- **Manual deployment smoke test** (documented in README): deploy the stack with defaults, `agentcore configure`/`launch`, then `agentcore invoke` a weather question and confirm a sensible Fahrenheit answer.
- **Memory-off verification**: confirm the deployed stack creates no Memory resource with default parameters, and that the agent code neither imports nor references any memory module.

## Design Decisions and Rationale

1. **Conditional Memory instead of deletion in the template.** The spec asks to "omit memory based on a condition" that "defaults to false." Keeping the resource behind a condition (rather than deleting it) directly satisfies that and makes the future Memory demo a one-parameter change.
2. **Full removal of Memory from code and tests.** The spec asks for the agent and tests to have memory removed (not merely disabled). Code has no runtime condition for memory; it simply does not exist there. This keeps the application layer maximally simple.
3. **Retain memory IAM permissions in the execution role.** Low risk (permissions without resources do nothing), avoids role churn when Memory is later enabled. Flagged as a deliberate choice; can be revisited if least-privilege for the basic demo is preferred.
4. **Self-contained freezing test prompt.** Without memory, the agent cannot recall a previous turn, so the follow-up question is rewritten to carry its own context. This keeps a meaningful behavioral assertion without reintroducing a memory dependency.
5. **Preserve the entrypoint I/O contract.** Keeping `actor_id`/`session_id` in the request and response avoids breaking tooling and eases the later addition of Memory/Identity.
