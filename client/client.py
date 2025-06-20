import asyncio
import json
import logging
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional, AsyncGenerator

import nest_asyncio
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from openai import AsyncOpenAI
import os

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

class ServerConfig:
    """Configuration manager that gets all config from the MCP server."""
    
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        
        # Setup basic logging (will be updated from server config later)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    async def load_from_server(self, session):
        """Load configuration from the MCP server."""
        try:
            result = await session.call_tool("get_config", arguments={})
            content_text = self._extract_tool_content(result)
            self.config = json.loads(content_text)
            
            # Update logging configuration
            if 'logging' in self.config and self.config['logging']['enabled']:
                log_level = getattr(logging, self.config['logging']['level'].upper())
                logging.getLogger().setLevel(log_level)
            
            self.logger.info("Configuration loaded from server")
        except Exception as e:
            self.logger.error(f"Failed to load config from server: {e}")
            raise
    
    def _extract_tool_content(self, result) -> str:
        """Extract content from tool results."""
        content_text = ""
        if result.content:
            for content_item in result.content:
                if hasattr(content_item, 'type'):
                    if content_item.type == 'text' and hasattr(content_item, 'text'):
                        content_text += content_item.text
                    else:
                        content_text += f"[{content_item.type} content]"
                else:
                    content_text += str(content_item)
        return content_text

    @property
    def openai_config(self) -> Dict[str, Any]:
        return self.config.get('openai', {})
    
    @property
    def server_config(self) -> Dict[str, Any]:
        return self.config.get('server', {})
    
    @property
    def chatbot_config(self) -> Dict[str, Any]:
        return self.config.get('chatbot', {})

class ChatBot:
    def __init__(self):
        self.config = ServerConfig()
        self.logger = logging.getLogger(__name__)
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.openai_client = AsyncOpenAI()
        self.conversation_history: List[Dict[str, Any]] = []
        self.system_message: Dict[str, Any] = {}
        
        self.logger.info("ChatBot initialized (config will be loaded from server)")

    async def connect_to_server(self, python_path: str = None, script_path: str = None):
        """Connect to an MCP server and load configuration."""
        # Use current Python executable if not specified
        if python_path is None:
            import sys
            python_path = sys.executable
        
        # Use relative path to server.py if not specified
        if script_path is None:
            import os
            script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "server.py")
        
        server_params = StdioServerParameters(
            command=python_path,
            args=[script_path],
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(stdio_transport[0], stdio_transport[1])
        )

        await self.session.initialize()
        
        # Load configuration from server
        await self.config.load_from_server(self.session)
        
        # Initialize system message from server config
        self.system_message = {
            "role": "system",
            "content": self.config.chatbot_config.get('system_prompt', 'You are a helpful assistant.')
        }
        self.conversation_history.append(self.system_message)
        
        return await self.session.list_tools()

    async def get_mcp_tools(self) -> List[Dict[str, Any]]:
        """Get available tools from the MCP server in OpenAI format."""
        if self.session is None:
            raise RuntimeError("Session is not initialized. Call connect_to_server() first.")
            
        tools_result = await self.session.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            }
            for tool in tools_result.tools
        ]

    async def _update_system_prompt_if_changed(self):
        """Check if system prompt has changed in server config and update if necessary."""
        if self.session is None:
            return
            
        try:
            # Get current system prompt from server
            result = await self.session.call_tool(
                "get_config",
                arguments={"section": "chatbot"}
            )
            
            content_text = self._extract_tool_content(result)
            server_config = json.loads(content_text)
            
            if "chatbot" in server_config:
                new_system_prompt = server_config["chatbot"].get("system_prompt", "")
                current_system_prompt = self.system_message.get("content", "")
                
                if new_system_prompt != current_system_prompt:
                    # Reload full config from server
                    await self.config.load_from_server(self.session)
                    
                    # Update system message
                    self.system_message["content"] = new_system_prompt
                    
                    # Update first message in conversation history (should be system message)
                    if self.conversation_history and self.conversation_history[0]["role"] == "system":
                        self.conversation_history[0]["content"] = new_system_prompt
                        self.logger.info(f"System prompt updated to: {new_system_prompt[:50]}...")
                    else:
                        # If somehow system message is not first, insert it
                        self.conversation_history.insert(0, self.system_message)
                        self.logger.info("System message added to conversation history")
        except Exception as e:
            self.logger.warning(f"Failed to update system prompt from server: {e}")

    async def process_message(self, user_message: str):
        """Process a user message maintaining conversation context."""
        # Check if system prompt has changed and update if necessary
        await self._update_system_prompt_if_changed()
        
        async for chunk in self._process_message_streaming(user_message):
            yield chunk

    async def _process_message_streaming(self, user_message: str) -> AsyncGenerator[str, None]:
        """Process message with streaming responses."""
        if self.session is None:
            raise RuntimeError("Session is not initialized")

        # Manage conversation history size
        if len(self.conversation_history) > self.config.chatbot_config['max_conversation_history']:
            # Keep system message and trim oldest messages
            self.conversation_history = [self.system_message] + self.conversation_history[-(self.config.chatbot_config['max_conversation_history']-1):]
            self.logger.info("Conversation history trimmed to maintain size limit")

        self.conversation_history.append({"role": "user", "content": user_message})
        
        tools = await self.get_mcp_tools()
        # Convert conversation_history to OpenAI message objects
        from openai.types.chat import (
            ChatCompletionMessageParam,
            ChatCompletionToolParam
        )
        messages: List[ChatCompletionMessageParam] = self.conversation_history  # type: ignore
        tools_param: List[ChatCompletionToolParam] = tools  # type: ignore
        
        # Get initial response with streaming
        response = await self.openai_client.chat.completions.create(
            model=self.config.openai_config['model'],
            messages=messages,
            tools=tools_param,
            tool_choice="auto",
            temperature=self.config.openai_config['temperature'],
            top_p=self.config.openai_config['top_p'],
            max_tokens=self.config.openai_config['max_tokens'],
            presence_penalty=self.config.openai_config['presence_penalty'],
            frequency_penalty=self.config.openai_config['frequency_penalty'],
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
                yield delta.content
            
            # Handle tool calls
            if delta.tool_calls:
                for delta_tool_call in delta.tool_calls:
                    idx = delta_tool_call.index
                    
                    if idx not in tool_calls_dict:
                        # Initialize new tool call
                        tool_calls_dict[idx] = {
                            'id': delta_tool_call.id,
                            'type': delta_tool_call.type,
                            'function': {
                                'name': delta_tool_call.function.name if delta_tool_call.function and delta_tool_call.function.name else '',
                                'arguments': delta_tool_call.function.arguments if delta_tool_call.function and delta_tool_call.function.arguments else ''
                            }
                        }
                    else:
                        # Accumulate arguments
                        if delta_tool_call.function and delta_tool_call.function.arguments:
                            tool_calls_dict[idx]['function']['arguments'] += delta_tool_call.function.arguments

        # Convert accumulated tool calls back to list format
        tool_calls = [tool_calls_dict[idx] for idx in sorted(tool_calls_dict.keys())]

        # Add assistant message to history
        assistant_message = {
            "role": "assistant", 
            "content": full_content,
            "tool_calls": tool_calls if tool_calls else None
        }
        self.conversation_history.append(assistant_message)

        # Handle tool calls if present
        if tool_calls:
            self.logger.info(f"Received {len(tool_calls)} tool calls: {[tc['function']['name'] for tc in tool_calls]}")
            for tool_call in tool_calls:
                try:
                    arguments = json.loads(tool_call['function']['arguments'])
                    result = await self.session.call_tool(
                        tool_call['function']['name'],
                        arguments=arguments,
                    )
                    content_text = self._extract_tool_content(result)
                    # Add tool response to conversation
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call['id'],
                        "content": content_text,
                    })
                except Exception as e:
                    error_message = f"Error executing tool {tool_call['function']['name']}: {str(e)}"
                    self.logger.error(error_message)
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call['id'],
                        "content": error_message,
                    })

            # Get final response with streaming
            final_response = await self.openai_client.chat.completions.create(
                model=self.config.openai_config['model'],
                messages=self.conversation_history,  # Use updated history with tool results
                tools=tools_param,
                tool_choice="none",
                temperature=self.config.openai_config['temperature'],
                top_p=self.config.openai_config['top_p'],
                max_tokens=self.config.openai_config['max_tokens'],
                presence_penalty=self.config.openai_config['presence_penalty'],
                frequency_penalty=self.config.openai_config['frequency_penalty'],
                stream=True
            )
            
            # Stream final response
            final_content = ""
            async for chunk in final_response:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    final_content += delta.content
                    yield delta.content
            
            # Add final message to history
            self.conversation_history.append({"role": "assistant", "content": final_content})

    def _extract_tool_content(self, result) -> str:
        """Extract content from tool results."""
        content_text = ""
        if result.content:
            for content_item in result.content:
                if hasattr(content_item, 'type'):
                    if content_item.type == 'text' and hasattr(content_item, 'text'):
                        content_text += content_item.text
                    else:
                        content_text += f"[{content_item.type} content]"
                else:
                    content_text += str(content_item)
        return content_text

    async def cleanup(self):
        """Clean up resources."""
        if self.config.chatbot_config.get('clear_history_on_exit', False):
            self.conversation_history.clear()
            self.logger.info("Conversation history cleared on exit")
        await self.exit_stack.aclose()

async def main():
    """Main entry point for the chatbot."""
    chatbot = None
    try:
        chatbot = ChatBot()
        tools = await chatbot.connect_to_server()
        
        print("\nChatbot initialized with the following tools:")
        for tool in tools.tools:
            print(f"  - {tool.name}: {tool.description}")
        print("\nYou can start chatting (press Ctrl+C to exit):")
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                if user_input.lower() in ['exit', 'quit']:
                    print("Goodbye!")
                    break
                if user_input:
                    print("\nAssistant: ", end="", flush=True)
                    async for chunk in chatbot.process_message(user_input):
                        print(chunk, end="", flush=True)
                    print()  # New line after response
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                logging.error(f"Error during chat: {str(e)}")
                print(f"\nError: {e}")
    except Exception as e:
        print(f"\nError during initialization: {e}")
    finally:
        if chatbot is not None:
            await chatbot.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
