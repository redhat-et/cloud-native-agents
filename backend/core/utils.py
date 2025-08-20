import asyncio
import logging
import os
import sys
import time
from inspect import iscoroutinefunction
from typing import AsyncGenerator, Awaitable, Callable, Dict, List, Optional, TypeVar, Union, cast

from autogen_core import CancellationToken
from autogen_core.models import RequestUsage

from autogen_agentchat.agents import UserProxyAgent
from autogen_agentchat.base import Response, TaskResult
from autogen_agentchat.messages import (
    BaseAgentEvent,
    BaseChatMessage,
    ModelClientStreamingChunkEvent,
    MultiModalMessage,
    UserInputRequestedEvent,
)

# Setup logging
logger = logging.getLogger(__name__)


def _is_running_in_iterm() -> bool:
    return os.getenv("TERM_PROGRAM") == "iTerm.app"


def _is_output_a_tty() -> bool:
    return sys.stdout.isatty()


SyncInputFunc = Callable[[str], str]
AsyncInputFunc = Callable[[str, Optional[CancellationToken]], Awaitable[str]]
InputFuncType = Union[SyncInputFunc, AsyncInputFunc]

T = TypeVar("T", bound=TaskResult | Response)




class UserInputManager:
    def __init__(self, callback: InputFuncType):
        self.input_events: Dict[str, asyncio.Event] = {}
        self.callback = callback



    def get_wrapped_callback(self) -> AsyncInputFunc:
        async def user_input_func_wrapper(prompt: str, cancellation_token: Optional[CancellationToken]) -> str:
            # Lookup the event for the prompt, if it exists wait for it.
            # If it doesn't exist, create it and store it.
            # Get request ID:
            request_id = UserProxyAgent.InputRequestContext.request_id()
            if request_id in self.input_events:
                event = self.input_events[request_id]
            else:
                event = asyncio.Event()
                self.input_events[request_id] = event

            await event.wait()

            del self.input_events[request_id]

            if iscoroutinefunction(self.callback):
                # Cast to AsyncInputFunc for proper typing
                async_func = cast(AsyncInputFunc, self.callback)
                return await async_func(prompt, cancellation_token)
            else:
                # Cast to SyncInputFunc for proper typing
                sync_func = cast(SyncInputFunc, self.callback)
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, sync_func, prompt)

        return user_input_func_wrapper




    def notify_event_received(self, request_id: str) -> None:
        if request_id in self.input_events:
            self.input_events[request_id].set()
        else:
            event = asyncio.Event()
            self.input_events[request_id] = event




def aprint(output: str, end: str = "\n", flush: bool = False) -> Awaitable[None]:
    return asyncio.to_thread(print, output, end=end, flush=flush)



# this function is original from autogen_agentchat.utils.Console.
async def Console(
    stream: AsyncGenerator[BaseAgentEvent | BaseChatMessage | T, None],
    *,
    no_inline_images: bool = False,
    output_stats: bool = False,
    user_input_manager: UserInputManager | None = None,
) -> T:
    """
    Consumes the message stream from :meth:`~autogen_agentchat.base.TaskRunner.run_stream`
    or :meth:`~autogen_agentchat.base.ChatAgent.on_messages_stream` and renders the messages to the console.
    Returns the last processed TaskResult or Response.

    .. note::

        `output_stats` is experimental and the stats may not be accurate.
        It will be improved in future releases.

    Args:
        stream (AsyncGenerator[BaseAgentEvent | BaseChatMessage | TaskResult, None] | AsyncGenerator[BaseAgentEvent | BaseChatMessage | Response, None]): Message stream to render.
            This can be from :meth:`~autogen_agentchat.base.TaskRunner.run_stream` or :meth:`~autogen_agentchat.base.ChatAgent.on_messages_stream`.
        no_inline_images (bool, optional): If terminal is iTerm2 will render images inline. Use this to disable this behavior. Defaults to False.
        output_stats (bool, optional): (Experimental) If True, will output a summary of the messages and inline token usage info. Defaults to False.

    Returns:
        last_processed: A :class:`~autogen_agentchat.base.TaskResult` if the stream is from :meth:`~autogen_agentchat.base.TaskRunner.run_stream`
            or a :class:`~autogen_agentchat.base.Response` if the stream is from :meth:`~autogen_agentchat.base.ChatAgent.on_messages_stream`.
    """
    render_image_iterm = _is_running_in_iterm() and _is_output_a_tty() and not no_inline_images
    start_time = time.time()
    total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

    last_processed: Optional[T] = None

    streaming_chunks: List[str] = []

    async for message in stream:
        if isinstance(message, TaskResult):
            duration = time.time() - start_time
            if output_stats:
                output = (
                    f"{'-' * 10} Summary {'-' * 10}\n"
                    f"Number of messages: {len(message.messages)}\n"
                    f"Finish reason: {message.stop_reason}\n"
                    f"Total prompt tokens: {total_usage.prompt_tokens}\n"
                    f"Total completion tokens: {total_usage.completion_tokens}\n"
                    f"Duration: {duration:.2f} seconds\n"
                )
                await aprint(output, end="", flush=True)

            # mypy ignore
            last_processed = message  # type: ignore

        elif isinstance(message, Response):
            duration = time.time() - start_time

            # Print final response.
            if isinstance(message.chat_message, MultiModalMessage):
                final_content = message.chat_message.to_text(iterm=render_image_iterm)
            else:
                final_content = message.chat_message.to_text()
            output = f"{'-' * 10} {message.chat_message.source} {'-' * 10}\n{final_content}\n"
            if message.chat_message.models_usage:
                if output_stats:
                    output += f"[Prompt tokens: {message.chat_message.models_usage.prompt_tokens}, Completion tokens: {message.chat_message.models_usage.completion_tokens}]\n"
                total_usage.completion_tokens += message.chat_message.models_usage.completion_tokens
                total_usage.prompt_tokens += message.chat_message.models_usage.prompt_tokens
            await aprint(output, end="", flush=True)

            # Print summary.
            if output_stats:
                if message.inner_messages is not None:
                    num_inner_messages = len(message.inner_messages)
                else:
                    num_inner_messages = 0
                output = (
                    f"{'-' * 10} Summary {'-' * 10}\n"
                    f"Number of inner messages: {num_inner_messages}\n"
                    f"Total prompt tokens: {total_usage.prompt_tokens}\n"
                    f"Total completion tokens: {total_usage.completion_tokens}\n"
                    f"Duration: {duration:.2f} seconds\n"
                )
                await aprint(output, end="", flush=True)

            # mypy ignore
            last_processed = message  # type: ignore
        # We don't want to print UserInputRequestedEvent messages, we just use them to signal the user input event.
        elif isinstance(message, UserInputRequestedEvent):
            if user_input_manager is not None:
                user_input_manager.notify_event_received(message.request_id)
        else:
            # Cast required for mypy to be happy
            message = cast(BaseAgentEvent | BaseChatMessage, message)  # type: ignore
            if not streaming_chunks:
                # Print message sender.
                await aprint(
                    f"{'-' * 10} {message.__class__.__name__} ({message.source}) {'-' * 10}", end="\n", flush=True
                )
            if isinstance(message, ModelClientStreamingChunkEvent):
                await aprint(message.to_text(), end="", flush=True)
                streaming_chunks.append(message.content)
            else:
                if streaming_chunks:
                    streaming_chunks.clear()
                    # Chunked messages are already printed, so we just print a newline.
                    await aprint("", end="\n", flush=True)
                elif isinstance(message, MultiModalMessage):
                    await aprint(message.to_text(iterm=render_image_iterm), end="\n", flush=True)
                else:
                    await aprint(message.to_text(), end="\n", flush=True)
                if message.models_usage:
                    if output_stats:
                        await aprint(
                            f"[Prompt tokens: {message.models_usage.prompt_tokens}, Completion tokens: {message.models_usage.completion_tokens}]",
                            end="\n",
                            flush=True,
                        )
                    total_usage.completion_tokens += message.models_usage.completion_tokens
                    total_usage.prompt_tokens += message.models_usage.prompt_tokens

    if last_processed is None:
        raise ValueError("No TaskResult or Response was processed.")

    return last_processed

# this function is modified from autogen_agentchat.utils.ConsoleWithCapture. It is used to capture the final output from the reasoner agent or comment posted by commenter or human approved comment.
async def ConsoleWithCapture(
    stream: AsyncGenerator[BaseAgentEvent | BaseChatMessage | T, None],
    *,
    no_inline_images: bool = False,
    output_stats: bool = False,
    user_input_manager: UserInputManager | None = None,
    websocket=None,
) -> tuple[T, str]:
    """
    Consumes the message stream and renders messages to console while capturing the final output.
    Returns a tuple of (last_processed, final_output_string).
    
    This function is similar to Console() but also captures the final output as a string
    that can be passed to the frontend. Automatically filters out "TERMINATE" messages
    and returns the second-to-last message content instead.

    Args:
        stream: Message stream to render and capture
        no_inline_images: If True, disables inline image rendering in iTerm2
        output_stats: If True, outputs token usage statistics
        user_input_manager: Optional user input manager for handling user input events
        websocket: Optional WebSocket connection for frontend streaming

    Returns:
        tuple: (last_processed, final_output_string) where last_processed is the final TaskResult or Response,
               and final_output_string is the captured final output as a string (with TERMINATE filtered out)
    """
    render_image_iterm = _is_running_in_iterm() and _is_output_a_tty() and not no_inline_images
    start_time = time.time()
    total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

    last_processed: Optional[T] = None
    final_output_string: str = ""
    streaming_chunks: List[str] = []

    async for message in stream:
        if isinstance(message, TaskResult):
            duration = time.time() - start_time
            if output_stats:
                output = (
                    f"{'-' * 10} Summary {'-' * 10}\n"
                    f"Number of messages: {len(message.messages)}\n"
                    f"Finish reason: {message.stop_reason}\n"
                    f"Total prompt tokens: {total_usage.prompt_tokens}\n"
                    f"Total completion tokens: {total_usage.completion_tokens}\n"
                    f"Duration: {duration:.2f} seconds\n"
                )
                await aprint(output, end="", flush=True)

            # Capture the final output from TaskResult
            if message.messages:
                # Find the last non-TERMINATE message
                for i in range(len(message.messages) - 1, -1, -1):
                    message_to_check = message.messages[i]
                    if hasattr(message_to_check, 'content') and message_to_check.content:
                        content = str(message_to_check.content)
                    elif hasattr(message_to_check, 'message') and message_to_check.message:
                        content = str(message_to_check.message.get('content', ''))
                    else:
                        content = str(message_to_check)
                    
                    if content.strip() != "TERMINATE":
                        final_output_string = content
                        break
                else:
                    # If all messages are TERMINATE, return empty string
                    final_output_string = ""

            last_processed = message  # type: ignore

        elif isinstance(message, Response):
            duration = time.time() - start_time

            # Print final response and capture it
            if isinstance(message.chat_message, MultiModalMessage):
                final_content = message.chat_message.to_text(iterm=render_image_iterm)
            else:
                final_content = message.chat_message.to_text()
            
            output = f"{'-' * 10} {message.chat_message.source} {'-' * 10}\n{final_content}\n"
            if message.chat_message.models_usage:
                if output_stats:
                    output += f"[Prompt tokens: {message.chat_message.models_usage.prompt_tokens}, Completion tokens: {message.chat_message.models_usage.completion_tokens}]\n"
                total_usage.completion_tokens += message.chat_message.models_usage.completion_tokens
                total_usage.prompt_tokens += message.chat_message.models_usage.prompt_tokens
            await aprint(output, end="", flush=True)

            # Print summary
            if output_stats:
                if message.inner_messages is not None:
                    num_inner_messages = len(message.inner_messages)
                else:
                    num_inner_messages = 0
                output = (
                    f"{'-' * 10} Summary {'-' * 10}\n"
                    f"Number of inner messages: {num_inner_messages}\n"
                    f"Total prompt tokens: {total_usage.prompt_tokens}\n"
                    f"Total completion tokens: {total_usage.completion_tokens}\n"
                    f"Duration: {duration:.2f} seconds\n"
                )
                await aprint(output, end="", flush=True)

            last_processed = message  # type: ignore
            
        elif isinstance(message, UserInputRequestedEvent):
            if user_input_manager is not None:
                user_input_manager.notify_event_received(message.request_id)
        else:
            # Cast required for mypy to be happy
            message = cast(BaseAgentEvent | BaseChatMessage, message)  # type: ignore
            if not streaming_chunks:
                # Print message sender
                await aprint(
                    f"{'-' * 10} {message.__class__.__name__} ({message.source}) {'-' * 10}", end="\n", flush=True
                )
            if isinstance(message, ModelClientStreamingChunkEvent):
                await aprint(message.to_text(), end="", flush=True)
                streaming_chunks.append(message.content)
            else:
                if streaming_chunks:
                    streaming_chunks.clear()
                    # Chunked messages are already printed, so we just print a newline
                    await aprint("", end="\n", flush=True)
                elif isinstance(message, MultiModalMessage):
                    await aprint(message.to_text(iterm=render_image_iterm), end="\n", flush=True)
                else:
                    await aprint(message.to_text(), end="\n", flush=True)
                if message.models_usage:
                    if output_stats:
                        await aprint(
                            f"[Prompt tokens: {message.models_usage.prompt_tokens}, Completion tokens: {message.models_usage.completion_tokens}]",
                            end="\n",
                            flush=True,
                        )
                    total_usage.completion_tokens += message.models_usage.completion_tokens
                    total_usage.prompt_tokens += message.models_usage.prompt_tokens

            # Send message to WebSocket for frontend if websocket is provided
            if websocket is not None:
                try:
                    # Import AgentManager here to avoid circular imports
                    from backend.core.agents import AgentManager
                    await websocket.send_json(AgentManager.convert_datetime_to_string(message.model_dump()))
                except Exception as e:
                    logger.error(f"Error sending message to WebSocket: {str(e)}")
                    break

    if last_processed is None:
        raise ValueError("No TaskResult or Response was processed.")

    # last_processed is the last message in the stream, contains all agent messages and tool calls details
    # final_output_string is the final output from the reasoner agent or comment posted by commenter or human approved comment
    # print("--------------------------------")
    # print(f"Final output: {final_output_string}")
    # print("--------------------------------")
    # print(f"Last processed: {last_processed}")
    # print("--------------------------------")
    return last_processed, final_output_string