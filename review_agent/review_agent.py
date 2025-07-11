from langgraph.prebuilt import create_react_agent
from langchain_anthropic import ChatAnthropic
from langchain_mcp_adapters.client import MultiServerMCPClient
import os
import dotenv
import asyncio 

dotenv.load_dotenv()        

async def run_agent():
    client = MultiServerMCPClient(
        {
            "mcp::github": {
                "url": os.getenv("GITHUB_MPC_URL"),
                "transport": "sse",
            }
        }
    )

    tools = await client.get_tools()
    model = ChatAnthropic(
        model=os.getenv("MODEL_NAME"),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0.0,
    )

    agent = create_react_agent(
        model=model,
        tools=tools,
        prompt="You are a helpful assistant that can answer questions and help with tasks. Your primary goal is to review PRs and provide feedback on them.",
    )

    response = await agent.ainvoke({"messages":[{"role":"user", "content":"Can you review PR 5 in the redhat-et cloud-native-agents repo?"}]})
    print(response["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(run_agent())