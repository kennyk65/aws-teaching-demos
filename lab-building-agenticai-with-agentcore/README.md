
## Building Agentic AI with Amazon Bedrock AgentCore 
### Instructor Demo: 
#### - Enhance and Scale Agents with Amazon Bedrock AgentCore 

This is the Lab/Demo that accompanies the _Building Agentic AI with Amazon Bedrock AgentCore_ course.  These notes provide guidance on how to run the lab/demo, what to highlight, what to look out for, etc.
 
The final architecture looks like this: 
![alt text](images/overview.png)

* You can run this on your own account.  
* TODO - NEED TO RUN A CF TEMPLATE TO SETUP A LAMBDA I THINK.
* Must be run in us-west-2.  I'm not sure why.  I have removed a few cases of (unnecessary) hard-coding.
* The initial Python imports from Task 1 take over 5 minutes to run. Do these first.

## Task 1.1
This is just setting up imports, running a simply 'Hello World' agent.
General introduction to Strands / Bedrock with single agent.  NO usage of AgentCore. Recommend moving quickly.

* You'll need to run `pip install -r requirements.txt` the first time.

![alt text](images/architecture_lab1_strands.png)

## Task 1.2 - Add basic memory
The Memory Hook provider is added here.

* This requires Task 1.1 to be complete.
* First they run code to create (or get) the memory resource.  Takes about 2 minutes.
  * Interesting: they have defined two long term memory strategies: user preferences and semantic.
* They seed short term memory with some conversation history.  Interestingly, they do not use the agent to do this, they just pump into memory directly.
* A HookProvider is setup for memory.  WARNING - it isn't what you might expect.  
  * It is build assuming one Agent, one user, one session.  
  * It does NOT attempt to rebuild agent memory for each request like you would do in a multi-threaded application.
  * Instead the `retrieve_customer_context()` simply embellishes the user message with some long term context - it **relies** on the agent preserving message history in memory.
  * The `save_support_interaction()` is more realistic, saving the latest user/assistant pair.
    * They strip out the tool activity.  This would be a big mistake if they were using this to hydrate the conversation later, but they are only using the memory events to prime long-term memory.

![alt text](images/architecture_lab2_memory.png)

## Task 1.3
This task deploys our multi-agent system to AgentCore Runtime

* The multi-agent _monolith_ is only slightly modified from Task 2, mainly to use AgentCore Runtime & Memory.
  * See the line that defines the `app = BedrockAgentCoreApp()` and `@app.entrypoint`.  These are the main concessions to AgentCore Runtime.
  * The `@tool`s are still inline - no use of AgentCore Gateway.
  * The use of AgentCore Memory is very low-level and manual; they are not using the newer memory hook.  This is not necessarily a mistake, note how the implementation embellishes the system prompt with key facts discovered from previous invocations.
* It will use a Cognito User-pool based identity, providing the OIDC token for AuthN.
* The AgentCore Runtime deployment process is demonstrated.
* It deploys it as a single MONOLITH.
* You can ignore the panic about "IMPORTANT: SAVE THESE CREDENTIALS NOW!".  The notebook logic captures what is needed.
* The observed behavior is no different from Task 2.  The relevant points are WHERE the agent is running, and HOW the memory is managed.

![alt text](images/task3-image.png)


## Cleanup 
This is important to cleanup the various artifacts installed in your AWS account, including:
* Cognito User Pool
* AgentCore Memory instance 
* AgentCore Runtime instance
* Bedrock Guardrails
* ECR repo, CodeBuild project.
* S3
* etc.
