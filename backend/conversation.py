import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam

from .session import MCPSession
from .utils import extract_tool_content
from .utils.security import get_required_env_var

# Load environment variables from .env file
load_dotenv()


class ConversationManager:
    """Manages conversation history and message processing with OpenAI."""

    def __init__(self, mcp_session: MCPSession):
        self.mcp_session = mcp_session
        
        # Securely get OpenAI API key from environment
        openai_api_key = get_required_env_var("OPENAI_API_KEY")
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        
        self.conversation_history: list[dict[str, Any]] = []
        self.system_message: dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        self._config_version: str = ""

    def set_system_message(self, content: str):
        """Set or update the system message."""
        self.system_message = {"role": "system", "content": content}

        # Update in conversation history
        if self.conversation_history and self.conversation_history[0]["role"] == "system":
            self.conversation_history[0]["content"] = content
        else:
            self.conversation_history.insert(0, self.system_message)

    def trim_history(self, max_length: int):
        """Trim conversation history to maintain size limit."""
        if len(self.conversation_history) > max_length:
            # Keep system message and trim oldest messages
            self.conversation_history = [self.system_message] + self.conversation_history[-(max_length-1):]
            self.logger.info("Conversation history trimmed to maintain size limit")

    async def process_message_streaming(self, user_message: str, config) -> AsyncGenerator[str]:
        """Process message with streaming responses and tool calls."""
        # Manage conversation history size
        self.trim_history(config.chatbot_config["max_conversation_history"])

        self.conversation_history.append({"role": "user", "content": user_message})

        tools = await self.mcp_session.get_tools_for_openai()
        messages: list[ChatCompletionMessageParam] = self.conversation_history  # type: ignore
        tools_param: list[ChatCompletionToolParam] = tools  # type: ignore

        # Allow multiple rounds of tool calls with reasonable limit
        max_tool_iterations = 5  # Prevent infinite loops
        current_iteration = 0

        while current_iteration < max_tool_iterations:
            current_iteration += 1

            # Get response with streaming
            response = await self.openai_client.chat.completions.create(
                model=config.openai_config["model"],
                messages=self.conversation_history,
                tools=tools_param,
                tool_choice="auto",  # Let LLM decide if tools are needed
                temperature=config.openai_config["temperature"],
                top_p=config.openai_config["top_p"],
                max_tokens=config.openai_config["max_tokens"],
                presence_penalty=config.openai_config["presence_penalty"],
                frequency_penalty=config.openai_config["frequency_penalty"],
                stream=True
            )

            # Handle streaming response
            full_content = ""
            tool_calls = []
            tool_calls_dict = {}  # Accumulate tool calls by index

            async for chunk in response:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta

                # Handle content
                if delta.content:
                    full_content += delta.content
                    # Only yield content if no tool calls (to avoid mixing output)
                    if not delta.tool_calls:
                        yield delta.content

                # Handle tool calls
                if delta.tool_calls:
                    for delta_tool_call in delta.tool_calls:
                        idx = delta_tool_call.index

                        if idx not in tool_calls_dict:
                            # Initialize new tool call
                            tool_calls_dict[idx] = {
                                "id": delta_tool_call.id,
                                "type": delta_tool_call.type,
                                "function": {
                                    "name": delta_tool_call.function.name if delta_tool_call.function and delta_tool_call.function.name else "",
                                    "arguments": delta_tool_call.function.arguments if delta_tool_call.function and delta_tool_call.function.arguments else ""
                                }
                            }
                        # Accumulate arguments
                        elif delta_tool_call.function and delta_tool_call.function.arguments:
                            tool_calls_dict[idx]["function"]["arguments"] += delta_tool_call.function.arguments

            # Convert accumulated tool calls back to list format
            tool_calls = [tool_calls_dict[idx] for idx in sorted(tool_calls_dict.keys())]

            # Add assistant message to history
            assistant_message = {
                "role": "assistant",
                "content": full_content,
                "tool_calls": tool_calls if tool_calls else None
            }
            self.conversation_history.append(assistant_message)

            # If no tool calls, we're done - content was already yielded during streaming
            if not tool_calls:
                break

            # Execute tool calls
            self.logger.info(f"Iteration {current_iteration}: Received {len(tool_calls)} tool calls: {[tc['function']['name'] for tc in tool_calls]}")
            await self._execute_tool_calls(tool_calls)

            # Continue loop to let LLM decide if more tools are needed

        # If we hit max iterations, ask LLM to summarize
        if current_iteration >= max_tool_iterations:
            async for chunk in self._handle_max_iterations(config, tools_param):
                yield chunk

    async def _execute_tool_calls(self, tool_calls: list[dict[str, Any]]):
        """Execute a list of tool calls and add responses to conversation history."""
        for tool_call in tool_calls:
            try:
                arguments = json.loads(tool_call["function"]["arguments"])
                result = await self.mcp_session.call_tool(
                    tool_call["function"]["name"],
                    arguments=arguments,
                )
                content_text = extract_tool_content(result)
                # Add tool response to conversation
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": content_text,
                })
            except Exception as e:
                error_message = f"Error executing tool {tool_call['function']['name']}: {e!s}"
                self.logger.error(error_message)
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": error_message,
                })

    async def _handle_max_iterations(self, config, tools_param) -> AsyncGenerator[str]:
        """Handle the case when max tool iterations is reached."""
        self.logger.info("Reached maximum tool iterations, asking LLM to summarize progress")

        # Add a system message asking for summary and continuation prompt
        summary_prompt = {
            "role": "user",
            "content": "I've reached my tool call limit (5 iterations per message). Please summarize what you've accomplished so far, what still needs to be done, and ask if I'd like you to continue by sending another message."
        }
        self.conversation_history.append(summary_prompt)

        summary_response = await self.openai_client.chat.completions.create(
            model=config.openai_config["model"],
            messages=self.conversation_history,
            tools=tools_param,
            tool_choice="none",  # No more tools for this summary
            temperature=config.openai_config["temperature"],
            top_p=config.openai_config["top_p"],
            max_tokens=config.openai_config["max_tokens"],
            presence_penalty=config.openai_config["presence_penalty"],
            frequency_penalty=config.openai_config["frequency_penalty"],
            stream=True
        )

        summary_content = ""
        async for chunk in summary_response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                summary_content += delta.content
                yield delta.content

        # Add summary to conversation history
        self.conversation_history.append({"role": "assistant", "content": summary_content})



    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history.clear()
        if self.system_message:
            self.conversation_history.append(self.system_message)
