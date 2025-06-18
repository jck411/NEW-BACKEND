import asyncio
import json
from contextlib import AsyncExitStack
from typing import Any, Dict, List

import nest_asyncio
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from openai import AsyncOpenAI

# Apply nest_asyncio to allow nested event loops (needed for Jupyter/IPython)
nest_asyncio.apply()

# Load environment variables
load_dotenv("/home/human/AAREPOS/NEW BACKEND/.env")

# Global variables to store session state
session: ClientSession | None = None
exit_stack = AsyncExitStack()
openai_client = AsyncOpenAI()
model = "gpt-4o"


async def connect_to_server(server_script_path: str = "server.py"):
    """Connect to an MCP server.

    Args:
        server_script_path: Path to the server script.
    """
    global session, exit_stack

    # Server configuration
    server_params = StdioServerParameters(
        command="/home/human/AAAVENVS/NEWBKND/bin/python",  # Use the NEWBKND Python
        args=[server_script_path],
    )

    # Connect to the server
    stdio_transport = await exit_stack.enter_async_context(
        stdio_client(server_params)
    )
    
    # Create session
    session = await exit_stack.enter_async_context(
        ClientSession(stdio_transport[0], stdio_transport[1])
    )

    # Initialize the connection
    await session.initialize()

    # List available tools
    tools_result = await session.list_tools()
    print("\nConnected to server with tools:")
    for tool in tools_result.tools:
        print(f"  - {tool.name}: {tool.description}")


async def get_mcp_tools() -> List[Dict[str, Any]]:
    """Get available tools from the MCP server in OpenAI format.

    Returns:
        A list of tools in OpenAI format.
        
    Raises:
        RuntimeError: If session is not initialized.
    """
    global session
    
    if session is None:
        raise RuntimeError("Session is not initialized. Call connect_to_server() first.")
        
    tools_result = await session.list_tools()
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


async def process_query(query: str) -> str:
    """Process a query using OpenAI and available MCP tools.

    Args:
        query: The user query.

    Returns:
        The response from OpenAI.
        
    Raises:
        RuntimeError: If session is not initialized.
    """
    global session, openai_client, model

    if session is None:
        raise RuntimeError("Session is not initialized. Call connect_to_server() first.")

    # Get available tools
    tools = await get_mcp_tools()

    # Initial OpenAI API call
    response = await openai_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": query}],
        tools=tools,  # type: ignore
        tool_choice="auto",
    )

    # Get assistant's response
    assistant_message = response.choices[0].message

    # Initialize conversation with user query and assistant response
    messages = [
        {"role": "user", "content": query},
        assistant_message.model_dump(),
    ]

    # Handle tool calls if present
    if assistant_message.tool_calls:
        # Process each tool call
        for tool_call in assistant_message.tool_calls:
            try:
                # Execute tool call with improved argument parsing
                arguments = json.loads(tool_call.function.arguments)
                result = await session.call_tool(
                    tool_call.function.name,
                    arguments=arguments,
                )

                # Extract content with improved handling
                content_text = ""
                if result.content:
                    for content_item in result.content:
                        # Handle different content types properly
                        if hasattr(content_item, 'type'):
                            if content_item.type == 'text' and hasattr(content_item, 'text'):
                                content_text += content_item.text
                            else:
                                # For non-text content, provide a description
                                content_text += f"[{content_item.type} content]"
                        else:
                            # Fallback to string representation
                            content_text += str(content_item)

                # Add tool response to conversation
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": content_text,
                    }
                )
            except Exception as e:
                # Handle tool execution errors gracefully
                error_message = f"Error executing tool {tool_call.function.name}: {str(e)}"
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": error_message,
                    }
                )

        # Get final response from OpenAI with tool results
        final_response = await openai_client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,  # type: ignore
            tool_choice="none",  # Don't allow more tool calls
        )

        return final_response.choices[0].message.content or ""

    # No tool calls, just return the direct response
    return assistant_message.content or ""


async def cleanup():
    """Clean up resources."""
    global exit_stack
    await exit_stack.aclose()


async def main():
    """Main entry point for the client."""
    try:
        await connect_to_server("server.py")
        print("\nConnected to server. Enter your queries (press Ctrl+C to exit):")
        
        while True:
            try:
                query = input("\nEnter your query: ").strip()
                if query:
                    response = await process_query(query)
                    print(f"\nResponse: {response}")
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"\nError processing query: {e}")
    finally:
        await cleanup()


if __name__ == "__main__":
    asyncio.run(main())
