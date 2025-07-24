from typing import TypedDict
from langgraph.graph import StateGraph
from langchain_core.runnables import RunnableLambda
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserStory1State(TypedDict, total=False):
    health_card: str
    name: str
    dob: str
    email: str
    phone: str
    provider_id: str
    plan_type: str
    find_user: str
    register_user: str
    rag_info: str
    create_policy: str

def build_user_story_1_graph(llm, tools: dict):
    graph = StateGraph(UserStory1State)

    # Node functions with logging only
    def logged_find_user(state: UserStory1State):
        logger.info("⏳ Starting user lookup...")
        logger.info(f"🔍 Searching for user with health card: {state.get('health_card')}")
        result = tools["find_user_by_health_card_or_id"](state)
        logger.info("✅ User lookup completed")
        logger.debug(f"User lookup result: {result}")
        return {"find_user": result}

    def logged_register_user(state: UserStory1State):
        logger.info("⏳ Starting user registration...")
        logger.info(f"📝 Registering user: {state.get('name')}")
        result = tools["register_new_user"](state)
        logger.info("✅ User registration completed")
        logger.debug(f"Registration result: {result}")
        return {"register_user": result}

    def logged_create_policy(state: UserStory1State):
        logger.info("⏳ Creating insurance policy...")
        logger.info(f"📄 Policy details: {state.get('plan_type')}")
        result = tools["create_policy"](state)
        logger.info("✅ Policy creation completed")
        logger.debug(f"Policy creation result: {result}")
        return {"create_policy": result}

    # Add nodes
    graph.add_node("find_user", RunnableLambda(logged_find_user))
    graph.add_node("register_user", RunnableLambda(logged_register_user))
    graph.add_node("create_policy", RunnableLambda(logged_create_policy))

    # RAG node with logging
    def rag_node(state: UserStory1State):
        logger.info("⏳ Generating RAG response...")
        logger.info(f"🧠 Processing query with LLM")
        
        # Implement your actual RAG logic here
        rag_response = f"OHIP information for {state.get('name')}"
        
        logger.info("✅ RAG response generated")
        logger.debug(f"RAG response: {rag_response}")
        return {"rag_info": rag_response}
    
    graph.add_node("rag_info", rag_node)

    # Set entry point
    graph.set_entry_point("find_user")

    # Conditional edges
    def should_register_user(state: UserStory1State):
        response = state.get("find_user", "")
        logger.info(f"🔀 Evaluating user existence check: {response}")
        
        decision = "register_user" if ("user_id" not in response.lower() and "name" not in response.lower()) else "rag_info"
        logger.info(f"📌 Decision: {decision}")
        return decision

    graph.add_conditional_edges(
        "find_user",
        should_register_user,
        {
            "register_user": "register_user",
            "rag_info": "rag_info"
        }
    )

    # Add regular edges with logging
    def log_edge_transition(from_node: str, to_node: str):
        logger.info(f"➡️ Transitioning from {from_node} to {to_node}")

    graph.add_edge("register_user", "rag_info")
    graph.add_edge("rag_info", "create_policy")

    # Set finish point
    graph.set_finish_point("create_policy")

    logger.info("🛠️ Workflow graph compiled successfully")
    return graph.compile()