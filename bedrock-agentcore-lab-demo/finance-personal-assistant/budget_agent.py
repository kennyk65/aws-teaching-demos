# Export complete budget agent implementation to Python file
from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import calculator
from pydantic import BaseModel, Field
from typing import List, Union
from decimal import Decimal
import matplotlib.pyplot as plt
import logging

# Configure logging for error tracking and debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Define structured output models for financial data
class BudgetCategory(BaseModel):
    name: str = Field(description="Budget category name")
    amount: float = Field(description="Dollar amount for this category")
    percentage: float = Field(description="Percentage of total income")


class FinancialReport(BaseModel):
    monthly_income: float = Field(description="Total monthly income")
    budget_categories: List[BudgetCategory] = Field(
        description="List of budget categories"
    )
    recommendations: List[str] = Field(description="List of specific recommendations")
    financial_health_score: int = Field(
        ge=1, le=10, description="Financial health score from 1-10"
    )


# Enhanced system prompt for structured outputs
BUDGET_SYSTEM_PROMPT = """You are a helpful personal finance assistant. 
You provide general strategies for creating budgets, tips on financial discipline to achieve financial milestones, and analyze financial trends. You do not provide any investment advice. 

When generating financial reports, always provide:
1. Clear budget breakdowns using the 50/30/20 rule or custom allocations
2. Specific, actionable recommendations (2-3 steps)
3. A financial health score based on spending patterns
4. Practical budgeting and spending advice

Use structured output when requested to provide comprehensive financial reports."""

# Continue with previous configurations
bedrock_model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
    region_name="us-west-2",
    temperature=0.0,  # Deterministic responses for financial advice
)


@tool
def calculate_budget(monthly_income: float) -> str:
    """Calculate 50/30/20 budget breakdown for the given monthly income."""
    try:
        # Perform calculations
        needs = monthly_income * 0.50
        wants = monthly_income * 0.30
        savings = monthly_income * 0.20
        
        return f"💰 Budget for ${monthly_income:,.0f}/month:\n• Needs: ${needs:,.0f} (50%)\n• Wants: ${wants:,.0f} (30%)\n• Savings: ${savings:,.0f} (20%)"
    
    except Exception as e:
        logger.error(f"Error in calculate_budget: {e}")
        return "❌ Error: Unable to calculate budget. Please provide a valid monthly income amount."


@tool
def create_financial_chart(
    data_dict: dict, chart_title: str = "Financial Chart"
) -> str:
    """Create a pie chart visualization from financial data dictionary."""
    try:
        # Basic validation
        if not data_dict:
            return "❌ Error: No data provided for chart."
        
        labels = list(data_dict.keys())
        values = [float(v) for v in data_dict.values()]
        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FECA57", "#FF9FF3"]
        
        # Create chart
        plt.figure(figsize=(8, 6))
        plt.pie(
            values,
            labels=labels,
            autopct="%1.1f%%",
            colors=colors[:len(values)],
            startangle=90,
        )
        plt.title(f"📊 {chart_title}", fontsize=14, fontweight="bold")
        plt.axis("equal")
        plt.tight_layout()
        plt.show()
        
        return f"✅ {chart_title} visualization created successfully!"
    
    except Exception as e:
        logger.error(f"Error in create_financial_chart: {e}")
        return "❌ Error: Unable to create chart visualization."


# Create our complete financial agent
budget_agent = Agent(
    model=bedrock_model,
    system_prompt=BUDGET_SYSTEM_PROMPT,
    tools=[calculate_budget, create_financial_chart, calculator],
    callback_handler=None,
)

if __name__ == "__main__":
    # Test structured output using structured_output_async
    print("\nStructured financial report:")
    structured_response = budget_agent.structured_output(
        output_model=FinancialReport,
        prompt="Generate a comprehensive financial report for someone earning $6000/month with $800 dining expenses.",
    )
    print(f"Income: ${structured_response.monthly_income:,.0f}")
    for category in structured_response.budget_categories:
        print(
            f"• {category.name}: ${category.amount:,.0f} ({category.percentage:.1f}%)"
        )
    print(f"\nFinancial Health Score: {structured_response.financial_health_score}/10")
    print("\nRecommendations:")
    for i, rec in enumerate(structured_response.recommendations, 1):
        print(f"{i}. {rec}")
