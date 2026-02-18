# Export financial analysis agent to standalone Python file

import yfinance as yf
from strands import Agent, tool
from typing import List
from strands.models import BedrockModel
import logging

# Configure logging for error tracking and debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Financial Analysis Agent System Prompt
FINANCIAL_ANALYSIS_PROMPT = """You are a specialized financial analysis agent focused on investment research and portfolio recommendations. Your role is to:

1. Research and analyze stock performance data
2. Create diversified investment portfolios
3. Provide data-driven investment recommendations

You do not provide specific investment advice but rather present analytical data to help users make informed decisions. Always include disclaimers about market risks and the importance of consulting financial advisors."""

bedrock_model = BedrockModel(
    model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0",
    region_name="us-west-2",
    temperature=0.0,  # Deterministic responses for financial advice
)


# Tool 1: Get Stock Analysis
@tool
def get_stock_analysis(symbol: str) -> str:
    """Get comprehensive analysis for a specific stock symbol."""
    try:
        # Fetch stock data
        stock = yf.Ticker(symbol)
        info = stock.info
        hist = stock.history(period="1y")
        
        if hist.empty:
            return f"❌ Error: No data found for symbol '{symbol.upper()}'."
        
        # Calculate key metrics
        current_price = hist["Close"].iloc[-1]
        year_high = hist["High"].max()
        year_low = hist["Low"].min()
        avg_volume = hist["Volume"].mean()
        price_change = ((current_price - hist["Close"].iloc[0]) / hist["Close"].iloc[0]) * 100

        return f"""
📊 Stock Analysis for {symbol.upper()}:
• Current Price: ${current_price:.2f}
• 52-Week High: ${year_high:.2f}
• 52-Week Low: ${year_low:.2f}
• Year-to-Date Change: {price_change:.2f}%
• Average Daily Volume: {avg_volume:,.0f} shares
• Company: {info.get("longName", "N/A")}
• Sector: {info.get("sector", "N/A")}
"""
    except Exception as e:
        logger.error(f"Error retrieving data for {symbol}: {e}")
        return f"❌ Error: Unable to retrieve stock data for '{symbol}'."


# Tool 2: Create Diversified Portfolio with comprehensive error handling
@tool
def create_diversified_portfolio(risk_level: str, investment_amount: float) -> str:
    """Create a diversified portfolio based on risk level (conservative, moderate, aggressive) and investment amount."""
    try:

        # Convert to float for calculations
        amount = float(investment_amount)
        
        # Input validation - negative check
        if amount < 0:
            logger.warning(f"Negative investment amount: {amount}")
            return "❌ Error: Investment amount cannot be negative. Please provide a positive amount."
        
        # Input validation - zero check
        if amount == 0:
            return "❌ Error: Investment amount cannot be zero. Please provide a positive amount to invest."
        
        # Input validation - minimum investment
        if amount < 100:
            return "❌ Error: Investment amount too small. Please provide at least $100 for portfolio diversification."
        
        # Input validation - maximum investment
        if amount > 100_000_000:
            logger.warning(f"Unusually high investment amount: {amount}")
            return "❌ Error: Investment amount seems unusually high. Please verify the amount (maximum $100,000,000)."
        
        portfolios = {
            "conservative": {
                "stocks": ["JNJ", "PG", "KO", "PEP", "WMT"],
                "weights": [0.25, 0.20, 0.20, 0.20, 0.15],
                "description": "Stable, dividend-paying blue-chip stocks with low volatility",
            },
            "moderate": {
                "stocks": ["AAPL", "MSFT", "JPM", "V", "DIS"],
                "weights": [0.25, 0.25, 0.20, 0.15, 0.15],
                "description": "Mix of established tech leaders and stable financial/consumer stocks",
            },
            "aggressive": {
                "stocks": ["TSLA", "NVDA", "META", "COIN", "PLTR"],
                "weights": [0.30, 0.25, 0.20, 0.15, 0.10],
                "description": "High-growth tech and emerging sector stocks with higher volatility",
            },
        }
        
        # Input validation - risk level check
        risk_level_lower = risk_level.strip().lower()
        if risk_level_lower not in portfolios:
            logger.warning(f"Invalid risk level provided: {risk_level}")
            return "❌ Error: Risk level must be 'conservative', 'moderate', or 'aggressive'. Please choose one of these options."
        
        portfolio = portfolios[risk_level_lower]
        
        result = f"""
🎯 {risk_level_lower.upper()} Portfolio Recommendation (${amount:,.0f}):
{portfolio["description"]}

Portfolio Allocation:
"""
        
        for stock, weight in zip(portfolio["stocks"], portfolio["weights"]):
            allocation = amount * weight
            result += f"• {stock}: {weight * 100:.0f}% (${allocation:,.0f})\n"
        
        result += "\n⚠️ Disclaimer: This is for educational purposes only. Consult a financial advisor before investing."
        return result
    
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid input for create_diversified_portfolio: risk_level={risk_level}, amount={investment_amount}, error: {e}")
        return "❌ Error: Unable to create portfolio. Please check your inputs and try again."
    except Exception as e:
        logger.error(f"Unexpected error in create_diversified_portfolio: {e}")
        return "❌ Error: An unexpected error occurred while creating portfolio. Please try again."


# Tool 3: Compare Stock Performance with comprehensive error handling
@tool
def compare_stock_performance(symbols: List[str], period: str = "1y") -> str:
    """Compare performance of multiple stocks over a specified period (1y, 6m, 3m, 1m)."""
    try:
        # Input validation - type checking
        if not isinstance(symbols, list):
            logger.error(f"Invalid type for symbols: {type(symbols)}")
            return "❌ Error: Symbols must be provided as a list"
        
        # Input validation - empty list check
        if not symbols:
            return "❌ Error: Please provide at least one stock symbol to compare."
        
        # Input validation - list size check
        if len(symbols) > 5:
            return "❌ Error: Please limit comparison to 5 stocks maximum for better readability."
        
        # Input validation - period check
        valid_periods = ["1m", "3m", "6m", "1y", "2y", "5y"]
        if period not in valid_periods:
            logger.warning(f"Invalid period provided: {period}")
            return f"❌ Error: Invalid time period '{period}'. Please use one of: {', '.join(valid_periods)}"
        
        # Validate each symbol
        for symbol in symbols:
            if not isinstance(symbol, str):
                logger.error(f"Non-string symbol in list: {symbol}")
                return "❌ Error: All stock symbols must be text strings"
            if not symbol.strip():
                return "❌ Error: Empty stock symbol found. Please provide valid ticker symbols."
        
        performance_data = {}
        failed_symbols = []
        
        for symbol in symbols:
            symbol = symbol.strip().upper()
            try:
                stock = yf.Ticker(symbol)
                hist = stock.history(period=period)
                
                if not hist.empty and len(hist) >= 2:
                    start_price = hist["Close"].iloc[0]
                    end_price = hist["Close"].iloc[-1]
                    performance = ((end_price - start_price) / start_price) * 100
                    performance_data[symbol] = performance
                else:
                    failed_symbols.append(symbol)
            except Exception as e:
                logger.warning(f"Failed to fetch data for {symbol}: {e}")
                failed_symbols.append(symbol)
        
        # Check if we got any valid data
        if not performance_data:
            return f"❌ Error: Unable to retrieve data for any of the provided symbols. Please verify the ticker symbols are correct."
        
        result = f"📈 Stock Performance Comparison ({period}):\n"
        sorted_stocks = sorted(
            performance_data.items(), key=lambda x: x[1], reverse=True
        )
        
        for stock, performance in sorted_stocks:
            result += f"• {stock}: {performance:+.2f}%\n"
        
        # Add note about failed symbols if any
        if failed_symbols:
            result += f"\n⚠️ Note: Unable to retrieve data for: {', '.join(failed_symbols)}"
        
        return result
    
    except ValueError as e:
        logger.error(f"Value error in compare_stock_performance: {e}")
        return "❌ Error: Invalid input values. Please check your stock symbols and period."
    except Exception as e:
        logger.error(f"Unexpected error in compare_stock_performance: {e}")
        return "❌ Error: Unable to compare stock performance. Please check your internet connection and try again."


# Create the Financial Analysis Agent
financial_analysis_agent = Agent(
    model=bedrock_model,  # Using the same bedrock_model from Step 1
    system_prompt=FINANCIAL_ANALYSIS_PROMPT,
    tools=[get_stock_analysis, create_diversified_portfolio, compare_stock_performance],
    callback_handler=None,
)

if __name__ == "__main__":
    # Test the Financial Analysis Agent
    response = financial_analysis_agent(
        "Create a moderate risk portfolio for $10,000 and analyze Apple stock"
    )
    print(response)
