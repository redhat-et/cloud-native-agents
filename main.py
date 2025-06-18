import asyncio
import os
import json
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from typing import Dict, Any

# Autogen imports
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import SseServerParams, SseMcpToolAdapter
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core.tools import FunctionTool
from tavily import AsyncTavilyClient
from dotenv import load_dotenv
from autogen_agentchat.ui import Console

# Load environment variables from .env file
load_dotenv()

# --- FastAPI App Initialization ---
app = FastAPI(
    title="GitHub Issue Agent Team API",
    description="An API to trigger an agent team to analyze a GitHub issue and suggest next steps.",
)

# --- Pydantic Models for API ---
class IssueRequest(BaseModel):
    """Request model for the issue link."""
    issue_link: str

class IssueResponse(BaseModel):
    """Response model for the generated comment."""
    response: str | Dict[str, Any]

# --- Agent and Tool Configuration (Global Setup) ---
# Load configurations from environment variables
GITHUB_MCP_URL = os.getenv("GITHUB_MCP_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not GITHUB_MCP_URL:
    raise ValueError("GITHUB_MCP_URL environment variable not set.")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set.")
if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY environment variable not set.")

@app.post("/github_webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    if payload.get("action") == "opened" and "issue" in payload:
        issue_url = payload["issue"]["html_url"]
        # Use background task so webhook returns quickly
        background_tasks.add_task(analyze_issue, IssueRequest(issue_link=issue_url))
        return {"status": "accepted", "detail": f"Processing issue {issue_url}"}
    return {"status": "ignored", "reason": "Not an 'opened' issue event"}

# --- API Endpoint ---
@app.post("/issue_next_steps", response_model=IssueResponse)
async def analyze_issue(request: IssueRequest):
    """
    Accepts a GitHub issue URL, processes it with an agent team,
    and returns the suggested next steps as a comment.
    """
    print(f"Received request for issue: {request.issue_link}")

    try:
        server_params = SseServerParams(
            url=GITHUB_MCP_URL,
            headers=None,
            timeout=10,
            sse_read_timeout=300,
        )

        model_client = OpenAIChatCompletionClient(
            model="gpt-4.1-nano-2025-04-14",
            api_key=OPENAI_API_KEY
        )

        # --- Tool Definitions ---
        async def tavily_search_func(query: str, max_results: int = 5) -> dict:
            client = AsyncTavilyClient(api_key=TAVILY_API_KEY)
            result = await client.search(query=query, max_results=max_results, include_answer=True)
            return result

        tavily_tool = FunctionTool(
            func=tavily_search_func,
            name="tavily_search",
            description="Perform a web search using Tavily and return summarized results."
        )

        async def get_tool_adapter(tool_name: str):
            """Helper function to get the tool adapter by name."""
            return await SseMcpToolAdapter.from_server_params(server_params, tool_name)

        tool_adapter_add_issue_comment = await get_tool_adapter("add_issue_comment")
        tool_adapter_get_issue = await get_tool_adapter("get_issue")

        # --- Agent Definitions ---
        issue_reader = AssistantAgent(
            name="issue_reader", model_client=model_client, tools=[tool_adapter_get_issue], reflect_on_tool_use=True,
            description="Extracts structured information from a GitHub issue.",
            system_message="You are a GitHub Issue Reader. Extract key problem details, error messages, user environment, and summarize the issue."
        )

        researcher = AssistantAgent(
            name="researcher", model_client=model_client, tools=[tavily_tool], reflect_on_tool_use=True,
            description="Researches related info to assist with resolving the issue.",
            system_message="You are a web researcher. Based on the issue summary, find related GitHub issues, documentation, and known solutions."
        )

        reasoner = AssistantAgent(
            name="reasoner", model_client=model_client, description="Analyzes and generates an action plan.",
            system_message="You are a technical expert. Given a GitHub issue and related research, suggest potential root causes and actionable next steps."
        )

        commenter = AssistantAgent(
            name="commenter", model_client=model_client, tools=[tool_adapter_add_issue_comment], reflect_on_tool_use=True,
            description="Writes a GitHub comment.",
            system_message="Turn the response from the researcher agent and reasoner agent output into a detailed GitHub comment. Do not end the comment with a question or an incomplete thought."
        )

        team = RoundRobinGroupChat([issue_reader, researcher, reasoner, commenter], max_turns=4)
        
        # --- Running the Agent Team ---
        task = f"Summarize and add next steps for this issue: {request.issue_link}"
        stream = team.run_stream(task=task)
        await Console(stream)
        await model_client.close()
        # Fix: Add condition to check if the task was successful
        return {"response": "Comment generated successfully. Check the issue for details."}

    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))
