import asyncio
import json
import logging
import os
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Dict, List, Optional, AsyncGenerator, Union

import nest_asyncio
import yaml
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from openai import AsyncOpenAI

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Load environment variables
load_dotenv("/home/human/AAREPOS/NEW BACKEND/.env")

class Config:
    """Configuration manager for the chatbot."""
    
    def __init__(self, config_path: str = "config.yaml"):
        # Get the directory where client.py is located
        client_dir = Path(__file__).parent
        self.config_path = client_dir / config_path
        
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
        # Setup logging
        if self.config['logging']['enabled']:
            logging.basicConfig(
                filename=self.config['logging']['log_file'],
                level=getattr(logging, self.config['logging']['level'].upper()),
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Configuration loaded successfully")

    @property
    def openai_config(self) -> Dict[str, Any]:
        return self.config['openai']
    
    @property
    def server_config(self) -> Dict[str, Any]:
        return self.config['server']
    
    @property
    def chatbot_config(self) -> Dict[str, Any]:
        return self.config['chatbot']

class ChatBot:
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.openai_client = AsyncOpenAI()
        self.conversation_history: List[Dict[str, Any]] = []
        
        # Initialize system message from config
        self.system_message = {
            "role": "system",
            "content": self.config.chatbot_config['system_prompt']
        }
        self.conversation_history.append(self.system_message)
        
        self.logger.info("ChatBot initialized with configuration")

    async def connect_to_server(self):
        """Connect to an MCP server using configured parameters."""
        server_params = StdioServerParameters(
            command=self.config.server_config['python_path'],
            args=[self.config.server_config['script_path']],
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(stdio_transport[0], stdio_transport[1])
        )

        await self.session.initialize()
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

    async def process_message(self, user_message: str):
        """Process a user message maintaining conversation context."""
        if self.config.chatbot_config.get('stream_responses', False):
            async for chunk in self._process_message_streaming(user_message):
                yield chunk
        else:
            result = await self._process_message_non_streaming(user_message)
            yield result

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
        
        # Get initial response with streaming
        response = await self.openai_client.chat.completions.create(
            model=self.config.openai_config['model'],
            messages=self.conversation_history,
            tools=tools,
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
                if not tool_calls:
                    tool_calls = delta.tool_calls
                else:
                    for i, tool_call in enumerate(delta.tool_calls):
                        if i < len(tool_calls):
                            if tool_call.function and tool_call.function.arguments:
                                tool_calls[i].function.arguments += tool_call.function.arguments

        # Add assistant message to history
        assistant_message = {
            "role": "assistant", 
            "content": full_content,
            "tool_calls": [tc.model_dump() for tc in tool_calls] if tool_calls else None
        }
        self.conversation_history.append(assistant_message)

        # Handle tool calls if present
        if tool_calls:
            for tool_call in tool_calls:
                try:
                    arguments = json.loads(tool_call.function.arguments)
                    result = await self.session.call_tool(
                        tool_call.function.name,
                        arguments=arguments,
                    )

                    content_text = self._extract_tool_content(result)
                    
                    # Add tool response to conversation
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": content_text,
                    })
                except Exception as e:
                    error_message = f"Error executing tool {tool_call.function.name}: {str(e)}"
                    self.logger.error(error_message)
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": error_message,
                    })

            # Get final response with streaming
            final_response = await self.openai_client.chat.completions.create(
                model=self.config.openai_config['model'],
                messages=self.conversation_history,
                tools=tools,
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

    async def _process_message_non_streaming(self, user_message: str) -> str:
        """Process message without streaming responses."""
        if self.session is None:
            raise RuntimeError("Session is not initialized")

        # Manage conversation history size
        if len(self.conversation_history) > self.config.chatbot_config['max_conversation_history']:
            # Keep system message and trim oldest messages
            self.conversation_history = [self.system_message] + self.conversation_history[-(self.config.chatbot_config['max_conversation_history']-1):]
            self.logger.info("Conversation history trimmed to maintain size limit")

        self.conversation_history.append({"role": "user", "content": user_message})
        
        tools = await self.get_mcp_tools()
        
        # Get initial response without streaming
        response = await self.openai_client.chat.completions.create(
            model=self.config.openai_config['model'],
            messages=self.conversation_history,
            tools=tools,
            tool_choice="auto",
            temperature=self.config.openai_config['temperature'],
            top_p=self.config.openai_config['top_p'],
            max_tokens=self.config.openai_config['max_tokens'],
            presence_penalty=self.config.openai_config['presence_penalty'],
            frequency_penalty=self.config.openai_config['frequency_penalty'],
            stream=False
        )

        assistant_message = response.choices[0].message
        self.conversation_history.append(assistant_message.model_dump())

        # Handle tool calls if present
        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                try:
                    arguments = json.loads(tool_call.function.arguments)
                    result = await self.session.call_tool(
                        tool_call.function.name,
                        arguments=arguments,
                    )

                    content_text = self._extract_tool_content(result)
                    
                    # Add tool response to conversation
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": content_text,
                    })
                except Exception as e:
                    error_message = f"Error executing tool {tool_call.function.name}: {str(e)}"
                    self.logger.error(error_message)
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": error_message,
                    })

            # Get final response without streaming
            final_response = await self.openai_client.chat.completions.create(
                model=self.config.openai_config['model'],
                messages=self.conversation_history,
                tools=tools,
                tool_choice="none",
                temperature=self.config.openai_config['temperature'],
                top_p=self.config.openai_config['top_p'],
                max_tokens=self.config.openai_config['max_tokens'],
                presence_penalty=self.config.openai_config['presence_penalty'],
                frequency_penalty=self.config.openai_config['frequency_penalty'],
                stream=False
            )
            
            final_message = final_response.choices[0].message
            self.conversation_history.append(final_message.model_dump())
            return final_message.content or ""

        return assistant_message.content or ""

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
        if self.config.chatbot_config['clear_history_on_exit']:
            self.conversation_history.clear()
            self.logger.info("Conversation history cleared on exit")
        await self.exit_stack.aclose()

async def main():
    """Main entry point for the chatbot."""
    chatbot = None
    try:
        config = Config("config.yaml")
        chatbot = ChatBot(config)
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
                    if config.chatbot_config.get('stream_responses', False):
                        print("\nAssistant: ", end="", flush=True)
                        async for chunk in chatbot.process_message(user_input):
                            print(chunk, end="", flush=True)
                        print()  # New line after response
                    else:
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
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("Please make sure the config.yaml file exists in the client directory.")
    except Exception as e:
        print(f"\nError during initialization: {e}")
    finally:
        if chatbot is not None:
            await chatbot.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
