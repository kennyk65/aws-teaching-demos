The goal of this project is to create a simple classroom demo of Bedrock AgentCore Runtime.  

The demo needs to be based on the existing demo at https://github.com/kennyk65/aws-teaching-demos/tree/master/bedrock-agentcore-demo-2.  This existing demo is great, but it includes demonstration of AgentCore Memory, which I want to wait for a separate demo.

Reference the README.md.  Begin by making a new README.md which is essentially the same except for any references to testing or observing memory.
Reference the agentcore-weather-demo.template.yml.  The new version should be the same except omit memory based on a condition.  The condition on whether to build memory should default to false.
Reference the weather_agent.py.  Make the new version the same except remove references / setup / hooks for memory.
Reference the test_weather_agent.py.  Make the new version without the memory test.
Remove any other files / requirements that are specific to setting up memory.

The result should be an agent deployable on Amazon Bedrock AgentCore Runtime.  The agent should respond to simple questions about the weather.

Later, I will add other capabilities to this demo, highlighting Identity, Gateway, Memory, Observability, etc.  But to begin, I need a very basic example.

 