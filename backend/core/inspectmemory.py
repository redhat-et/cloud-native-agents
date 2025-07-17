from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_core.memory import MemoryContent, MemoryMimeType
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.memory.chromadb import (
    ChromaDBVectorMemory,
    HttpChromaDBVectorMemoryConfig,
)
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize user memory
user_memory = ChromaDBVectorMemory(
    config=HttpChromaDBVectorMemoryConfig(
        collection_name="abstraction_demo",
        host=os.getenv("CHROMADB_URL"),
        port=80,
    )
)
async def main():
    # Add user preferences to memory
    await user_memory.add(MemoryContent(content="The weather should be in metric units", mime_type=MemoryMimeType.TEXT))

    await user_memory.add(MemoryContent(content="Meal recipe must be vegan", mime_type=MemoryMimeType.TEXT))


    async def get_weather(city: str, units: str = "imperial") -> str:
        if units == "imperial":
            return f"The weather in {city} is 73 °F and Sunny."
        elif units == "metric":
            return f"The weather in {city} is 23 °C and Sunny."
        else:
            return f"Sorry, I don't know the weather in {city}."


    assistant_agent = AssistantAgent(
        name="assistant_agent",
        model_client=OpenAIChatCompletionClient(
            model="gpt-4o-2024-08-06",
        ),
        tools=[get_weather],
        memory=[user_memory],
    )

    # Run the agent with a task.
    stream = assistant_agent.run_stream(task="What is the weather in New York?")
    await Console(stream)

    await assistant_agent._model_context.get_messages()
asyncio.run(main())

# Output:
# 
# ---------- TextMessage (user) ----------
# What is the weather in New York?
# ---------- MemoryQueryEvent (assistant_agent) ----------
# [MemoryContent(content='The weather should be in metric units', mime_type='MemoryMimeType.TEXT', metadata={'mime_type': 'MemoryMimeType.TEXT', 'score': 0.43428415, 'id': '1cfc10ba-21ec-4fe7-9009-10d91897789a'}), MemoryContent(content='Meal recipe must be vegan', mime_type='MemoryMimeType.TEXT', metadata={'mime_type': 'MemoryMimeType.TEXT', 'score': -0.02963019999999994, 'id': 'e2b0804e-5256-4e99-937f-526e8da221de'})]
# ---------- ToolCallRequestEvent (assistant_agent) ----------
# [FunctionCall(id='call_eZceZUJAmzGtgOSG4sZMG51W', arguments='{"city":"New York","units":"metric"}', name='get_weather')]
# ---------- ToolCallExecutionEvent (assistant_agent) ----------
# [FunctionExecutionResult(content='The weather in New York is 23 °C and Sunny.', name='get_weather', call_id='call_eZceZUJAmzGtgOSG4sZMG51W', is_error=False)]
# ---------- ToolCallSummaryMessage (assistant_agent) ----------
# The weather in New York is 23 °C and Sunny.
