"""Content extraction utilities for MCP tool results."""
from typing import Any


def extract_tool_content(result: Any) -> str:
    """Extract content from MCP tool results.

    This utility handles the common pattern of extracting text content
    from tool results across different content types.

    Args:
        result: MCP tool result object

    Returns:
        str: Extracted content text
    """
    content_text = ""
    if result.content:
        for content_item in result.content:
            if hasattr(content_item, "type"):
                if content_item.type == "text" and hasattr(content_item, "text"):
                    content_text += content_item.text
                else:
                    content_text += f"[{content_item.type} content]"
            else:
                content_text += str(content_item)
    return content_text
