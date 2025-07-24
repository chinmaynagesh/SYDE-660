# ohip_graph.py

from langgraph.graph import StateGraph, END
from llama_index.tools.mcp import BasicMCPClient
from llama_index.core.agent import AgentRunner, ReActAgent
from mistralai import Mistral
import os

# Define Mistral + MCP setup

MODEL_NAME = "mistral-large-latest"
MCP_URL = os.getenv("MCP_URL", "http://localhost:8000/sse")

mistral_client = Mistral(api_key="Cmm6JEg6eWD0Ri6z3o9RF04BeyfcJRq3")
mcp_client = BasicMCPClient(MCP_URL)

# ----- Step 1: Tools -----
# Define tools to use in the flow
from llama_index.tools.mcp import McpToolSpec

tool_spec = McpToolSpec(client=mcp_client)
tools = tool_spec.to_tool_list()

# ----- Step 2: Define LangGraph nodes -----
from typing import TypedDict, Optional

class OHIPState(TypedDict):
    input: str
    user_id: Optional[str]
    registered: Optional[bool]
    response: Optional[str]

# Define each step in the story

def find_user_node(state: OHIPState) -> OHIPState:
    user_input = state["input"]
    # Simulate: extract ID or use static for now
    health_card = "HC123"  # Example only
    tool = next(t for t in tools if t.metadata.name == "find_user_by_health_card_or_id")
    result = tool.invoke({"health_card": health_card})
    
    print(f"[find_user] → {result}")
    if "null" in result.lower() or not result.strip():
        return {**state, "user_id": None, "registered": False}
    
    # Assume user_id found
    return {**state, "user_id": "user123", "registered": True}

def register_node(state: OHIPState) -> OHIPState:
    if state["registered"]:
        return state
    tool = next(t for t in tools if t.metadata.name == "register_new_user")
    result = tool.invoke({
        "name": "John Doe",
        "dob": "2000-01-01",
        "health_card": "HC123",
        "email": "john@example.com"
    })
    print(f"[register_user] → {result}")
    return {**state, "user_id": "user123", "registered": True}

def explain_ohip_node(state: OHIPState) -> OHIPState:
    system = "You are a helpful OHIP assistant."
    user = f"The user wants to apply for OHIP. Provide the step-by-step application process."

    resp = mistral_client.chat.complete(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
    )
    return {**state, "response": resp.choices[0].message.content.strip()}

def create_policy_node(state: OHIPState) -> OHIPState:
    tool = next(t for t in tools if t.metadata.name == "create_policy")
    result = tool.invoke({
        "user_id": state["user_id"],
        "provider_id": "OHIP",
        "plan_type": "Student Basic"
    })
    print(f"[create_policy] → {result}")
    return {**state, "response": f"{state['response']}\n✅ Policy created."}

# ----- Step 3: Build Graph -----
def build_ohip_graph():
    graph = StateGraph(OHIPState)

    graph.add_node("find_user", find_user_node)
    graph.add_node("register", register_node)
    graph.add_node("explain_ohip", explain_ohip_node)
    graph.add_node("create_policy", create_policy_node)

    graph.set_entry_point("find_user")

    graph.add_edge("find_user", "register")
    graph.add_edge("register", "explain_ohip")
    graph.add_edge("explain_ohip", "create_policy")
    graph.add_edge("create_policy", END)

    return graph.compile()
