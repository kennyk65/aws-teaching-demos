# Create AgentCore-compatible deployment file with streaming endpoint and memory integration

from strands import Agent, tool
from strands.models import BedrockModel
from strands.agent.conversation_manager import SummarizingConversationManager

from budget_agent import FinancialReport, budget_agent
from financial_analysis_agent import financial_analysis_agent
from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient

from utils import get_guardrail_id
import uuid
import os
import logging

# Configure logging for error tracking and debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize AgentCore app
app = BedrockAgentCoreApp()

ORCHESTRATOR_PROMPT = """You are a comprehensive financial advisor orchestrator that coordinates between specialized financial agents to provide complete financial guidance. 

Your specialized agents are:
1. **budget_agent**: Handles budgeting, spending analysis, savings recommendations, and expense tracking
2. **financial_analysis_agent_tool**: Handles investment analysis, stock research, portfolio creation, and performance comparisons

Guidelines for using your agents:
- Use **budget_agent** for questions about: budgets, spending habits, expense tracking, savings goals, debt management
- Use **financial_analysis_agent_tool** for questions about: stocks, investments, portfolios, market analysis, investment recommendations
- You can use both agents together for comprehensive financial planning
- Always provide a cohesive summary that combines insights from multiple agents when applicable
- Maintain a helpful, professional tone and include appropriate disclaimers about financial advice

When a user asks a question:
1. Determine which agent(s) are most appropriate
2. Call the relevant agent(s) with focused queries
3. Synthesize the responses into a coherent, comprehensive answer
4. Provide actionable next steps when possible"""

# Add conversation management to maintain context
conversation_manager = SummarizingConversationManager(
    summary_ratio=0.3,  # Summarize 30% of messages when context reduction is needed
    preserve_recent_messages=5,  # Always keep 5 most recent messages
)

# Configure Bedrock model
bedrock_model = BedrockModel(
    model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0",
    region_name="us-west-2",
    temperature=0.0,  # Deterministic responses for financial advice
    guardrail_id=get_guardrail_id(),
    guardrail_version="DRAFT",
    guardrail_trace="enabled",
)


@tool
def budget_agent_tool(query: str) -> FinancialReport:
    """Generate structured financial reports with budget analysis and recommendations."""
    logger.info(f"budget_agent_tool called with query: {query[:100]}...")
    try:
        structured_response = budget_agent.structured_output(
            output_model=FinancialReport, prompt=query
        )
        logger.info("budget_agent_tool completed successfully")
        return structured_response
    except Exception as e:
        logger.error(f"Error in budget_agent_tool: {e}", exc_info=True)
        # Return a default structured response on error
        return FinancialReport(
            monthly_income=0.0,
            budget_categories=[],
            recommendations=[f"Error generating report: {str(e)}"],
            financial_health_score=1,
        )


@tool
def financial_analysis_agent_tool(query: str) -> str:
    """Handle investment analysis queries including stock research, portfolio creation, and performance comparisons."""
    logger.info(f"financial_analysis_agent_tool called with query: {query[:100]}...")
    try:
        response = financial_analysis_agent(query)
        logger.info("financial_analysis_agent_tool completed successfully")
        return str(response)
    except Exception as e:
        logger.error(f"Error in financial_analysis_agent_tool: {e}", exc_info=True)
        return f"❌ Financial analysis error: {str(e)}"


# Initialize orchestrator agent at module level
logger.info("Initializing orchestrator agent...")
orchestrator_agent = Agent(
    model=bedrock_model,
    system_prompt=ORCHESTRATOR_PROMPT,
    tools=[budget_agent_tool, financial_analysis_agent_tool],
    conversation_manager=conversation_manager,
)
logger.info("Orchestrator agent initialized successfully")


@app.entrypoint
async def invoke(payload):
    """Your AI agent function with memory integration"""
    user_message = payload["prompt"]
    actor_id = payload.get("actor_id", "default_user")  # User identifier
    session_id = payload.get("session_id", str(uuid.uuid4()))  # Session identifier
    
    # Retrieve relevant memories before processing
    memory_id = os.environ.get('AGENTCORE_MEMORY_ID')
    if memory_id:
        try:
            memory_client = MemoryClient()
            # Query relevant memories for context
            relevant_memories = memory_client.query_records(
                memory_id=memory_id,
                query=user_message,
                namespace=f"finance/user/{actor_id}/facts",
                max_results=5
            )
            
            # Add memory context to system prompt if available
            if relevant_memories:
                memory_context = "\n\nRelevant user information from previous conversations:\n"
                for record in relevant_memories:
                    memory_context += f"- {record.get('content', '')}\n"
                
                # Enhance agent with memory context
                enhanced_prompt = ORCHESTRATOR_PROMPT + memory_context
                orchestrator_agent.system_prompt = enhanced_prompt
        except Exception as e:
            logger.warning(f"Error retrieving memories: {e}")
    
    # Stream response
    full_response = ""
    async for event in orchestrator_agent.stream_async(user_message):
        if "data" in event:
            chunk = event["data"]
            full_response += chunk
            yield chunk
    
    # Store conversation in memory after response
    if memory_id:
        try:
            memory_client.create_event(
                memory_id=memory_id,
                actor_id=actor_id,
                session_id=session_id,
                content=f"User: {user_message}\nAssistant: {full_response}"
            )
        except Exception as e:
            logger.warning(f"Error storing memory: {e}")


if __name__ == "__main__":
    app.run()
