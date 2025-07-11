import os
import logging
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import StreamableHttpServerParams, StreamableHttpMcpToolAdapter
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_core.tools import FunctionTool
from tavily import AsyncTavilyClient
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Dict, Any, Callable, Awaitable
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination

# Load environment variables from .env file
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

class AgentManager:
    def __init__(self, user_input_func=None):
        # Load configurations from environment variables
        self.GITHUB_MCP_URL = os.getenv("GITHUB_MCP_URL")
        self.GITHUB_PAT = os.getenv("GITHUB_PAT")
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

        if not self.GITHUB_MCP_URL:
            raise ValueError("GITHUB_MCP_URL environment variable not set.")
        if not self.GITHUB_PAT:
            raise ValueError("GITHUB_PAT environment variable not set.")
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        if not self.TAVILY_API_KEY:
            raise ValueError("TAVILY_API_KEY environment variable not set.")

        self.user_input_func = user_input_func
        self._setup_agents_and_tools()

    def _setup_agents_and_tools(self):
        self.server_params = StreamableHttpServerParams(
            url=self.GITHUB_MCP_URL,
            headers={
                "Authorization": f"Bearer {self.GITHUB_PAT}",
                "Content-Type": "application/json"
            },
            timeout=10,
            sse_read_timeout=300,
        )

        self.model_client = OpenAIChatCompletionClient(
            model="gpt-4.1-nano-2025-04-14",
            api_key=self.OPENAI_API_KEY
        )

        async def tavily_search_func(query: str, max_results: int = 5) -> dict:
            client = AsyncTavilyClient(api_key=self.TAVILY_API_KEY)
            result = await client.search(query=query, max_results=max_results, include_answer=True)
            return result

        self.tavily_tool = FunctionTool(
            func=tavily_search_func,
            name="tavily_search",
            description="Perform a web search using Tavily and return summarized results."
        )

        async def get_tool_adapter(tool_name: str):
            return await StreamableHttpMcpToolAdapter.from_server_params(self.server_params, tool_name)

        # Tool adapters must be awaited, so we store coroutines for later initialization
        self._tool_adapter_add_issue_comment_coro = get_tool_adapter("add_issue_comment")
        self._tool_adapter_get_issue_coro = get_tool_adapter("get_issue")

        self.agents = {}

    async def initialize_agents(self, user_input_func=None):
        # Await tool adapters
        tool_adapter_get_issue = await self._tool_adapter_get_issue_coro
        tool_adapter_add_issue_comment = await self._tool_adapter_add_issue_comment_coro

        self.agents["issue_reader"] = AssistantAgent(
            name="issue_reader", model_client=self.model_client, tools=[tool_adapter_get_issue], reflect_on_tool_use=True,
            description="Extracts structured information from a GitHub issue.",
            system_message="You are a GitHub Issue Reader. Extract key problem details, error messages, user environment, and summarize the issue using the tool_adapter_get_issue tool. "
        )

        self.agents["researcher"] = AssistantAgent(
            name="researcher", model_client=self.model_client, tools=[self.tavily_tool], reflect_on_tool_use=True,
            description="Researches related info to assist with resolving the issue.",
            system_message="You are a web researcher. Based on the issue summary, find top 3 related GitHub issues, documentation, and known solutions using the tavily_tool. "
        )

        self.agents["reasoner"] = AssistantAgent(
            name="reasoner", model_client=self.model_client,
            description="Draft a github comment based on the issue and related research.",
            system_message="You are a technical expert. Given a GitHub issue and related research, suggest potential root causes and actionable next steps and format it as a github comment. "
        )

        self.agents["commenter"] = AssistantAgent(
            name="commenter", model_client=self.model_client, tools=[tool_adapter_add_issue_comment], reflect_on_tool_use=True,
            description="Writes a GitHub comment.",
            system_message="You are a GitHub commenter. If 'USER EDITED COMMENT:' is present, post user edited comment as-is. Else, post the reasoner agent's output as-is. Do not modify or paraphrase either option. After posting the comment, reply with 'TERMINATE'."
        )

        # Use the passed-in user_input_func if provided, else the one from self
        input_func = user_input_func if user_input_func is not None else self.user_input_func
        if input_func:
            self.agents["user_proxy"] = UserProxyAgent(
                name="user_proxy",
                input_func=input_func,
                description="A proxy for the user to review and edit the draft github comment from the reasoner agent. ",
            )

    async def analyze_issue_without_comment(self, issue_link: str):
        print(f"Received request for issue analysis only: {issue_link}")
        try:
            await self.initialize_agents()
            team = RoundRobinGroupChat([
                self.agents["issue_reader"],
                self.agents["researcher"],
                self.agents["reasoner"]
            ], max_turns=3)
            task = f"Analyze this issue and provide detailed next steps: {issue_link}"
            stream = team.run_stream(task=task)
            final_output = None
            async for chunk in stream:
                if hasattr(chunk, 'content') and chunk.content:
                    final_output = chunk.content
                elif hasattr(chunk, 'message') and chunk.message:
                    final_output = chunk.message.get('content', '')
                elif isinstance(chunk, dict) and 'content' in chunk:
                    final_output = chunk['content']
                elif isinstance(chunk, str):
                    final_output = chunk
            await self.model_client.close()
            if final_output:
                return {"response": final_output}
            else:
                return {"response": "Analysis completed successfully. Check the console output for detailed results."}
        except Exception as e:
            import traceback
            print(f"An error occurred: {e}")
            traceback.print_exc()
            # For Python 3.11+ ExceptionGroup (TaskGroup errors)
            try:
                BaseExceptionGroup = __import__('builtins').BaseExceptionGroup
            except (ImportError, AttributeError):
                BaseExceptionGroup = None
            if (BaseExceptionGroup and isinstance(e, BaseExceptionGroup)) or hasattr(e, 'exceptions'):
                print("ExceptionGroup sub-exceptions:")
                for sub in getattr(e, 'exceptions', []):
                    print(f"Sub-exception: {sub}")
                    traceback.print_exception(type(sub), sub, sub.__traceback__)
            raise Exception(str(e))

    async def analyze_issue_with_comment(self, issue_link: str):
        print(f"Received request for issue with comment: {issue_link}")
        try:
            await self.initialize_agents()
            team = RoundRobinGroupChat([
                self.agents["issue_reader"],
                self.agents["researcher"],
                self.agents["reasoner"],
                self.agents["commenter"]
            ], max_turns=4, termination_condition=TextMentionTermination("TERMINATE"))
            task = f"Summarize and add next steps for this issue: {issue_link}"
            stream = team.run_stream(task=task)
            final_output = None
            async for chunk in stream:
                if hasattr(chunk, 'content') and chunk.content:
                    final_output = chunk.content
                elif hasattr(chunk, 'message') and chunk.message:
                    final_output = chunk.message.get('content', '')
                elif isinstance(chunk, dict) and 'content' in chunk:
                    final_output = chunk['content']
                elif isinstance(chunk, str):
                    final_output = chunk
            await self.model_client.close()
            if final_output:
                return {"response": final_output}
            else:
                return {"response": "Comment generated and posted successfully. Check the issue for details."}
        except Exception as e:
            import traceback
            print(f"An error occurred: {e}")
            traceback.print_exc()
            # For Python 3.11+ ExceptionGroup (TaskGroup errors)
            try:
                BaseExceptionGroup = __import__('builtins').BaseExceptionGroup
            except (ImportError, AttributeError):
                BaseExceptionGroup = None
            if (BaseExceptionGroup and isinstance(e, BaseExceptionGroup)) or hasattr(e, 'exceptions'):
                print("ExceptionGroup sub-exceptions:")
                for sub in getattr(e, 'exceptions', []):
                    print(f"Sub-exception: {sub}")
                    traceback.print_exception(type(sub), sub, sub.__traceback__)
            raise Exception(str(e))

    async def hitl_team_stream(self, issue_link: str, user_input_func: Callable[[str], Awaitable[str]]):
        """
        Returns an async generator (the agent team stream) for HITL
        """
        await self.initialize_agents(user_input_func=user_input_func)
        team = RoundRobinGroupChat([
            self.agents["issue_reader"],
            self.agents["researcher"],
            self.agents["reasoner"],
            self.agents["user_proxy"],
            self.agents["commenter"]
        ], termination_condition=TextMentionTermination("TERMINATE"), max_turns=5)
        task = f"You have a team of agents, use them to read a github issue: {issue_link}, research related information, reason root causes and next steps as a github comment message, let human review it before posting. "
        return team.run_stream(task=task)

    @staticmethod
    def convert_datetime_to_string(obj):
        from datetime import datetime
        if isinstance(obj, dict):
            return {key: AgentManager.convert_datetime_to_string(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [AgentManager.convert_datetime_to_string(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj

class IssueRequest(BaseModel):
    """Request model for the issue link."""
    issue_link: str

class IssueResponse(BaseModel):
    """Response model for the generated comment."""
    response: str | Dict[str, Any]
