import asyncio
from .client_and_tool import analyze_issue_grpc_tool
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv
load_dotenv()

async def main():
    # Set up the model client (replace with your model and API key as needed)
    model_client = OpenAIChatCompletionClient(model="gpt-4.1-nano-2025-04-14")
    agent = AssistantAgent(
        name="test_agent",
        model_client=model_client,
        tools=[analyze_issue_grpc_tool],
        system_message="You are a helpful assistant that can analyze GitHub issues using a gRPC tool."
    )
    issue_link = "https://github.com/RHETbot/test-repository/issues/1"
    task = f"Analyze this GitHub issue: {issue_link}"
    result = await agent.run(task=task)
    print("Agent response:", result.messages[-1].content)
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main()) 
