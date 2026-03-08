import os
import sys
import json
import asyncio
from strands import Agent, tool

# Import our mocked tools directly for local testing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mock_tools.financial_apis import get_customer_balance, check_loan_eligibility

# 1. Define Strands Tools
# Strands uses a @tool decorator similar to LangChain
@tool
def get_balance_tool(customer_id: str) -> str:
    """
    Retrieve the customer's current account balance.
    Args:
        customer_id: The ID of the customer.
    """
    return get_customer_balance(customer_id)

@tool
def check_loan_tool(customer_id: str, requested_amount: float) -> str:
    """
    Check if the customer is eligible for a loan.
    Args:
        customer_id: The ID of the customer.
        requested_amount: The amount the customer wants to borrow.
    """
    return check_loan_eligibility(customer_id, requested_amount)

tools = [get_balance_tool, check_loan_tool]

# 2. Define the Agent
# Note: Strands natively connects to Bedrock. It defaults to Claude 3 Haiku if not specified.
agent = Agent(
    name="Financial Advisor Agent",
    description="You are a helpful financial assistant for nCino.",
    system_prompt="""
    You help bank employees check customer data.
    When asked about a customer, always check their balance first.
    Then, if they ask about a loan, check their loan eligibility.
    Provide the final answer clearly based on the tool results.
    """,
    tools=tools,
    # Here you would typically specify the exact model ID like "anthropic.claude-3-haiku-20240307-v1:0"
    # But for a robust local test that might lack credentials, we're relying on the fact that
    # the Strands Agent loop is the core thing we are testing here.
)

async def main():
    print("--- Starting Local Strands PoC Test ---")
    user_input = "What is the balance for customer 123? Are they eligible for a $20,000 loan?"
    print(f"User Request: {user_input}\n")
    
    try:
        print("\n--- Executing Agent Loop ---")
        # Strands handles the loop, tool execution, and state internally
        response = await agent.invoke_async(user_input)
        
        # In Strands, the response object contains the text and the trace
        print(f"\nFinal Response:\n{response.content}")
        
    except Exception as e:
        print(f"\nExecution Error (Likely missing AWS Credentials for Bedrock): {e}")

if __name__ == "__main__":
    asyncio.run(main())
