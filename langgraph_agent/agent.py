from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_aws import ChatBedrockConverse
import json
import os
import sys

# In a real environment, this imports from the actual AgentCore Gateway MCP tools
# For this PoC, we import our mocked tools directly to simulate local testing Sandbox
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mock_tools.financial_apis import get_customer_balance, check_loan_eligibility

# 1. Define the LangGraph State
class State(TypedDict):
    messages: Annotated[list, add_messages]

# 2. Define Tools
@tool
def get_balance(customer_id: str) -> str:
    """Retrieve the customer's current account balance."""
    return get_customer_balance(customer_id)

@tool
def check_loan(customer_id: str, requested_amount: float) -> str:
    """Check if the customer is eligible for a loan."""
    return check_loan_eligibility(customer_id, requested_amount)

tools = [get_balance, check_loan]

# 3. Initialize the LLM (Amazon Bedrock)
# We will use Claude 3 Haiku for the PoC as it's fast and cost-effective
try:
    llm = ChatBedrockConverse(
        model="anthropic.claude-3-haiku-20240307-v1:0",
        region_name="us-east-1",  # Replace with actual region
        # Credentials should be picked up from the environment or EC2/ECS role
    )
    llm_with_tools = llm.bind_tools(tools)
except Exception as e:
     print(f"Warning: Could not initialize Bedrock LLM (likely no AWS credentials). Mocking LLM. Error: {e}")
     # Mock LLM for local testing without AWS credentials
     from langchain_core.runnables import RunnableLambda
     def mock_llm(state):
         return AIMessage(content="[MOCK BEDROCK] I have checked the customer's balance and loan eligibility.")
     llm_with_tools = RunnableLambda(mock_llm)

# 4. Define Graph Nodes
def chatbot_node(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

def tools_node(state: State):
    # Basic tool execution logic
    last_message = state["messages"][-1]
    tool_msgs = []
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            # Find the tool
            action = next((t for t in tools if t.name == tool_call["name"]), None)
            if action:
                try:
                    # Execute tool
                    result = action.invoke(tool_call["args"])
                    tool_msgs.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
                except Exception as e:
                     tool_msgs.append(ToolMessage(content=f"Error: {e}", tool_call_id=tool_call["id"]))
            else:
                 tool_msgs.append(ToolMessage(content=f"Tool {tool_call['name']} not found", tool_call_id=tool_call["id"]))
    
    return {"messages": tool_msgs}

def route_tools(state: State) -> Literal["tools_node", "__end__"]:
    """Routing logic to see if tools should be called."""
    if isinstance(state["messages"][-1], AIMessage) and state["messages"][-1].tool_calls:
        return "tools_node"
    return "__end__"

# 5. Build the Graph
graph_builder = StateGraph(State)
graph_builder.add_node("chatbot_node", chatbot_node)
graph_builder.add_node("tools_node", tools_node)

graph_builder.add_edge(START, "chatbot_node")
graph_builder.add_conditional_edges("chatbot_node", route_tools)
graph_builder.add_edge("tools_node", "chatbot_node")

# Compile the graph
agent_graph = graph_builder.compile()

# Example local test execution
if __name__ == "__main__":
    print("--- Starting Local LangGraph PoC Test ---")
    
    # LangSmith Tracing Setup (Simulating CI/CD injected env vars)
    # os.environ["LANGCHAIN_TRACING_V2"] = "true"
    # os.environ["LANGCHAIN_API_KEY"] = "your_langsmith_api_key"
    # os.environ["LANGCHAIN_PROJECT"] = "ncino-agent-poc"
    # print("LangSmith tracing configured (commented out for local sandbox run without key).")

    inputs = {"messages": [HumanMessage(content="What is the balance for customer 123? Are they eligible for a $20,000 loan?")]}
    
    print(f"User Request: {inputs['messages'][0].content}\n")
    
    try:
        # Run graph
        print("\n--- Executing Graph ---")
        result = agent_graph.invoke(inputs)
        
        for msg in result["messages"]:
            if isinstance(msg, HumanMessage):
                pass
            elif isinstance(msg, AIMessage):
                if msg.tool_calls:
                    print(f"Agent Action -> Calling tools: {[t['name'] for t in msg.tool_calls]}")
                elif msg.content:
                    print(f"Agent Response -> {msg.content}")
            elif isinstance(msg, ToolMessage):
                print(f"Tool Result -> {msg.content}")
             
    except Exception as e:
        print(f"\nExecution Error: {e}")
