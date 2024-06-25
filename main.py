"""
API entrypoint for backend API.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from chatbot import CustomerSupportAIAgent
from models.request import ChatBotRequest

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agent pool keyed by session_id to retain memories/history in-memory.
# Note: the context is lost every time the service is restarted.
agent_pool = {}


@app.get("/")
def root():
    """
    Health probe endpoint.
    """
    return {"status": "ready"}


@app.post("/ai")
def run_customer_support_ai_agent(request: ChatBotRequest):
    """
    Run the Cosmic Works AI agent.
    """
    if request.session_id not in agent_pool:
        agent_pool[request.session_id] = CustomerSupportAIAgent(request.session_id)
    agent_instance = agent_pool[request.session_id]
    try:
        response_message = agent_instance.run(request.prompt)
        return {"message": response_message}
    except Exception as e:
        # Handle any potential errors gracefully
        raise HTTPException(status_code=500, detail=str(e))
