import json
import logging
from collections.abc import AsyncGenerator, AsyncIterator
from typing import TypedDict

from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionToolParam,
)
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

from .config import ServerConfig
from .session import MCPSession
from .utils import extract_tool_content
from .utils.security import get_required_env_var

# Load environment variables from .env file
load_dotenv()


class ToolCallFunction(TypedDict):
    """Type definition for tool call function parameters."""

    name: str
    arguments: str


class ToolCall(TypedDict):
    """Type definition for tool call structure."""

    id: str
    type: str
    function: ToolCallFunction


class ConversationManager:
    """Manages conversation history and message processing with OpenAI.

    This class handles streaming chat completions with tool calls, maintaining
    conversation context and managing the interaction flow with MCP servers.
    """

    def __init__(self, mcp_session: MCPSession) -> None:
        """Initialize the ConversationManager with MCP session.

        Args:
            mcp_session: The MCP session for tool execution and configuration.
        """
        self.mcp_session = mcp_session

        # Securely get OpenAI API key from environment
        openai_api_key = get_required_env_var("OPENAI_API_KEY")
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)

        # Use proper types for conversation history
        self.conversation_history: list[ChatCompletionMessageParam] = []
        self.system_message: ChatCompletionMessageParam = {
            "role": "system",
            "content": "",
        }
        self.logger = logging.getLogger(__name__)
        self._config_version: str = ""

    def set_system_message(self, content: str) -> None:
        """Set or update the system message.

        Args:
            content: The system message content to set.
        """
        self.system_message = {"role": "system", "content": content}

        # Update in conversation history
        if (
            self.conversation_history
            and self.conversation_history[0]["role"] == "system"
        ):
            self.conversation_history[0]["content"] = content
        else:
            self.conversation_history.insert(0, self.system_message)

    def trim_history(self, max_length: int) -> None:
        """Trim conversation history to maintain size limit.

        Args:
            max_length: Maximum number of messages to keep in history.
        """
        if len(self.conversation_history) > max_length:
            # Keep system message and trim oldest messages
            self.conversation_history = [
                self.system_message,
                *self.conversation_history[-(max_length - 1) :],
            ]
            self.logger.info("Conversation history trimmed to maintain size limit")

    async def process_message_streaming(
        self, user_message: str, config: ServerConfig
    ) -> AsyncGenerator[str]:
        """Process message with streaming responses and tool calls.

        This method handles the complete conversation flow including:
        - Message streaming from OpenAI
        - Tool call execution
        - Conversation history management
        - Iterative tool calling with limits

        Args:
            user_message: The user's input message.
            config: Server configuration containing OpenAI and chatbot settings.

        Yields:
            str: Streaming content chunks from the AI response.

        Raises:
            RuntimeError: If tool execution fails or max iterations exceeded.
        """
        self.trim_history(config.chatbot_config["max_conversation_history"])
        self.conversation_history.append({"role": "user", "content": user_message})

        # Get tools with proper type annotation
        tools = await self.mcp_session.get_tools_for_openai()
        tools_param: list[ChatCompletionToolParam] = tools  # type: ignore[assignment]

        max_tool_iterations = 5
        current_iteration = 0

        while current_iteration < max_tool_iterations:
            current_iteration += 1

            # Get streaming response from OpenAI
            response: AsyncIterator[ChatCompletionChunk] = (
                await self.openai_client.chat.completions.create(
                    model=config.openai_config["model"],
                    messages=self.conversation_history,
                    tools=tools_param,
                    tool_choice="auto",
                    temperature=config.openai_config["temperature"],
                    top_p=config.openai_config["top_p"],
                    max_tokens=config.openai_config["max_tokens"],
                    presence_penalty=config.openai_config["presence_penalty"],
                    frequency_penalty=config.openai_config["frequency_penalty"],
                    stream=True,
                )
            )

            # Process streaming response and yield content as it comes
            full_content = ""
            tool_calls_dict: dict[int, ToolCall] = {}

            async for chunk in response:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta

                # Handle content streaming - yield chunks as they come
                if getattr(delta, "content", None) is not None:
                    content = delta.content
                    if content is not None:
                        full_content += content
                        yield content  # Stream the chunk immediately

                # Handle tool calls streaming
                if getattr(delta, "tool_calls", None) is not None:
                    tool_calls_list = delta.tool_calls
                    if tool_calls_list is not None:
                        for delta_tool_call in tool_calls_list:
                            idx = delta_tool_call.index

                            if idx not in tool_calls_dict:
                                # Initialize new tool call
                                function_name = (
                                    delta_tool_call.function.name
                                    if delta_tool_call.function
                                    and delta_tool_call.function.name
                                    else ""
                                )
                                function_args = (
                                    delta_tool_call.function.arguments
                                    if delta_tool_call.function
                                    and delta_tool_call.function.arguments
                                    else ""
                                )
                                tool_calls_dict[idx] = {
                                    "id": delta_tool_call.id or "",
                                    "type": delta_tool_call.type or "function",
                                    "function": {
                                        "name": function_name,
                                        "arguments": function_args,
                                    },
                                }
                            elif (
                                delta_tool_call.function
                                and delta_tool_call.function.arguments
                            ):
                                # Accumulate arguments
                                args = delta_tool_call.function.arguments
                                tool_calls_dict[idx]["function"]["arguments"] += args

            # Convert to sorted list
            tool_calls = [
                tool_calls_dict[idx] for idx in sorted(tool_calls_dict.keys())
            ]

            # Add assistant message to history
            assistant_message = self._create_assistant_message(full_content, tool_calls)
            self.conversation_history.append(assistant_message)

            # If no tool calls, we're done
            if not tool_calls:
                break

            # Execute tool calls
            self.logger.info(
                "Iteration %s: Received %s tool calls: %s",
                current_iteration,
                len(tool_calls),
                [tc["function"]["name"] for tc in tool_calls],
            )
            await self._execute_tool_calls(tool_calls)

        # Handle max iterations reached
        if current_iteration >= max_tool_iterations:
            async for chunk in self._handle_max_iterations(config, tools_param):
                yield chunk

    async def _process_streaming_response(
        self, response: AsyncIterator[ChatCompletionChunk]
    ) -> tuple[str, list[ToolCall]]:
        """Process the streaming response from OpenAI.

        Args:
            response: The streaming response from OpenAI.

        Returns:
            tuple: (full_content, tool_calls) where full_content is the complete
                   response text and tool_calls is the list of tool calls.
        """
        full_content = ""
        tool_calls_dict: dict[int, ToolCall] = {}

        async for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            # Handle content streaming
            if getattr(delta, "content", None) is not None:
                content = delta.content
                if content is not None:
                    full_content += content

            # Handle tool calls streaming
            if getattr(delta, "tool_calls", None) is not None:
                tool_calls_list = delta.tool_calls
                if tool_calls_list is not None:
                    for delta_tool_call in tool_calls_list:
                        idx = delta_tool_call.index

                        if idx not in tool_calls_dict:
                            # Initialize new tool call
                            function_name = (
                                delta_tool_call.function.name
                                if delta_tool_call.function
                                and delta_tool_call.function.name
                                else ""
                            )
                            function_args = (
                                delta_tool_call.function.arguments
                                if delta_tool_call.function
                                and delta_tool_call.function.arguments
                                else ""
                            )
                            tool_calls_dict[idx] = {
                                "id": delta_tool_call.id or "",
                                "type": delta_tool_call.type or "function",
                                "function": {
                                    "name": function_name,
                                    "arguments": function_args,
                                },
                            }
                        elif (
                            delta_tool_call.function
                            and delta_tool_call.function.arguments
                        ):
                            # Accumulate arguments
                            args = delta_tool_call.function.arguments
                            tool_calls_dict[idx]["function"]["arguments"] += args

        # Convert to sorted list
        tool_calls = [tool_calls_dict[idx] for idx in sorted(tool_calls_dict.keys())]

        return full_content, tool_calls

    def _create_assistant_message(
        self, content: str, tool_calls: list[ToolCall]
    ) -> ChatCompletionMessageParam:
        """Create an assistant message with optional tool calls.

        Args:
            content: The message content.
            tool_calls: List of tool calls to include.

        Returns:
            ChatCompletionMessageParam: The properly typed assistant message.
        """
        assistant_message: ChatCompletionMessageParam = {
            "role": "assistant",
            "content": content,
        }

        if tool_calls:
            assistant_message["tool_calls"] = tool_calls  # type: ignore[typeddict-item]

        return assistant_message

    async def _execute_tool_calls(self, tool_calls: list[ToolCall]) -> None:
        """Execute a list of tool calls and add responses to conversation history.

        Args:
            tool_calls: List of tool calls to execute.
        """
        for tool_call in tool_calls:
            try:
                arguments = json.loads(tool_call["function"]["arguments"])
                result = await self.mcp_session.call_tool(
                    tool_call["function"]["name"],
                    arguments=arguments,
                )
                content_text = extract_tool_content(result)

                # Add tool response to conversation
                self.conversation_history.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": content_text,
                    }
                )
            except Exception as e:
                error_message = (
                    f"Error executing tool {tool_call['function']['name']}: {e!s}"
                )
                self.logger.exception(error_message)
                self.conversation_history.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": error_message,
                    }
                )

    async def _handle_max_iterations(
        self, config: ServerConfig, tools_param: list[ChatCompletionToolParam]
    ) -> AsyncGenerator[str]:
        """Handle the case when max tool iterations is reached.

        Args:
            config: Server configuration.
            tools_param: List of available tools.

        Yields:
            str: Summary content chunks.
        """
        self.logger.info(
            "Reached maximum tool iterations, asking LLM to summarize progress"
        )

        summary_prompt: ChatCompletionMessageParam = {
            "role": "user",
            "content": (
                "I've reached my tool call limit (5 iterations per message). "
                "Please summarize what you've accomplished so far, what still needs to be done, "
                "and ask if I'd like you to continue by sending another message."
            ),
        }
        self.conversation_history.append(summary_prompt)

        summary_response: AsyncIterator[ChatCompletionChunk] = (
            await self.openai_client.chat.completions.create(
                model=config.openai_config["model"],
                messages=self.conversation_history,
                tools=tools_param,
                tool_choice="none",
                temperature=config.openai_config["temperature"],
                top_p=config.openai_config["top_p"],
                max_tokens=config.openai_config["max_tokens"],
                presence_penalty=config.openai_config["presence_penalty"],
                frequency_penalty=config.openai_config["frequency_penalty"],
                stream=True,
            )
        )

        summary_content = ""
        async for chunk in summary_response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if getattr(delta, "content", None) is not None:
                content = delta.content
                if content is not None:
                    summary_content += content
                    yield content

        self.conversation_history.append(
            {"role": "assistant", "content": summary_content}
        )

    def clear_history(self) -> None:
        """Clear conversation history while preserving system message."""
        self.conversation_history.clear()
        if self.system_message:
            self.conversation_history.append(self.system_message)
