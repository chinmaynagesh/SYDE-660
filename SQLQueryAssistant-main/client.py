import asyncio
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from llama_index.core.agent import ReActAgent
from llama_index.llms.mistralai import MistralAI
from llama_index.tools.mcp import BasicMCPClient, McpToolSpec
from langchain_core.runnables import RunnableLambda

from user_stories.user_story_1 import build_user_story_1_graph

# Configuration
MCP_URL = os.environ.get("MCP_URL", "http://127.0.0.1:8000/sse")
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "Cmm6JEg6eWD0Ri6z3o9RF04BeyfcJRq3")
MODEL_NAME = os.environ.get("LLM_MODEL", "mistral-large-latest")
TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.2"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = None
langgraph_runner = None

class Query(BaseModel):
    query: str

async def load_llm_and_tools():
    print(f"🔌 Connecting to MCP server at {MCP_URL}")
    mcp_client = BasicMCPClient(MCP_URL)
    tools = await McpToolSpec(client=mcp_client).to_tool_list_async()
    tools_dict = {t.metadata.name: t for t in tools}

    print("🧠 Loading Mistral...")
    llm = MistralAI(
        api_key=MISTRAL_API_KEY,
        model=MODEL_NAME,
        temperature=TEMPERATURE
    )
    return llm, tools_dict

@app.on_event("startup")
async def initialize_agent():
    global agent, langgraph_runner
    try:
        llm, tools_dict = await load_llm_and_tools()

        # Create agent
        agent = ReActAgent.from_tools(
            tools=list(tools_dict.values()),
            llm=llm,
            verbose=True,
            max_iterations=10,
            system_prompt=(
                "You are InsuranceBot, an AI assistant specialized in insurance claims and policies. "
                "Be concise, professional, and helpful. If you don't know the answer, say so."
            )
        )

        # Initialize LangGraph
        langgraph_runner = build_user_story_1_graph(llm, tools_dict)
        print("✅ Agent and LangGraph initialized")
    except Exception as e:
        print(f"❌ Error during startup: {e}")
        raise

@app.get("/ping")
async def ping():
    return {"status": "InsuranceBot is alive"}

@app.post("/ask")
async def ask_query(data: Query):
    try:
        if not agent or not langgraph_runner:
            raise HTTPException(status_code=503, detail="Agent not initialized")

        query = data.query.strip()[:1000]

        if "apply for ohip" in query.lower():
            user_context = {
                "health_card": "HC1234567890",
                "name": "John Doe",
                "dob": "2001-01-01",
                "email": "john@studentmail.com",
                "phone": "555-4321",
                "provider_id": "prov-001",
                "plan_type": "basic"
            }
            result = await langgraph_runner.ainvoke(user_context)
            return {"response": str(result)}

        response = await agent.achat(query)
        return {"response": str(response)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4000)