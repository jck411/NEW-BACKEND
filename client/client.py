import asyncio
import json
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

import nest_asyncio
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from openai import AsyncOpenAI

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Load environment variables
load_dotenv("/home/human/AAREPOS/NEW BACKEND/.env")

class ChatBot:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.openai_client = AsyncOpenAI()
        self.model = "gpt-4"
        self.conversation_history: List[Dict[str, Any]] = []
        # System message to define chatbot behavior
        self.system_message = {
            "role": "system",
            "content": """You are a helpful AI assistant. Maintain a natural, conversational tone 
            while providing accurate and helpful responses. If you need to use tools to help answer 
            questions, use them, but always maintain context of the ongoing conversation."""
        }
        self.conversation_history.append(self.system_message)

    async def connect_to_server(self, server_script_path: str = "server.py"):
        """Connect to an MCP server."""
        server_params = StdioServerParameters(
            command="/home/human/AAAVENVS/NEWBKND/bin/python",
            args=[server_script_path],
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

    async def process_message(self, user_message: str) -> str:
        """Process a user message maintaining conversation context."""
        if self.session is None:
            raise RuntimeError("Session is not initialized")

        # Add user message to conversation history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        tools = await self.get_mcp_tools()
        
        # Get initial response
        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=self.conversation_history,
            tools=tools,
            tool_choice="auto",
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
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": error_message,
                    })

            # Get final response incorporating tool results
            final_response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                tools=tools,
                tool_choice="none",
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
        await self.exit_stack.aclose()

async def main():
    """Main entry point for the chatbot."""
    chatbot = ChatBot()
    try:
        tools = await chatbot.connect_to_server("server.py")
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
                    response = await chatbot.process_message(user_input)
                    print(f"\nAssistant: {response}")
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}")
    finally:
        await chatbot.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
