"""Tests for content extraction utilities."""

from unittest.mock import MagicMock

from backend.utils.content_extraction import extract_tool_content


class TestExtractToolContent:
    """Test suite for extract_tool_content function."""

    def test_extract_tool_content_with_text_content(self):
        """Test extracting content from tool result with text content."""
        # Mock content item with text type
        content_item = MagicMock()
        content_item.type = "text"
        content_item.text = "Hello, world!"

        # Mock result with content
        result = MagicMock()
        result.content = [content_item]

        extracted = extract_tool_content(result)
        assert extracted == "Hello, world!"

    def test_extract_tool_content_with_multiple_text_items(self):
        """Test extracting content from tool result with multiple text items."""
        # Mock multiple content items
        content_item1 = MagicMock()
        content_item1.type = "text"
        content_item1.text = "Hello, "

        content_item2 = MagicMock()
        content_item2.type = "text"
        content_item2.text = "world!"

        # Mock result with content
        result = MagicMock()
        result.content = [content_item1, content_item2]

        extracted = extract_tool_content(result)
        assert extracted == "Hello, world!"

    def test_extract_tool_content_with_non_text_content(self):
        """Test extracting content from tool result with non-text content."""
        # Mock content item with image type
        content_item = MagicMock()
        content_item.type = "image"

        # Mock result with content
        result = MagicMock()
        result.content = [content_item]

        extracted = extract_tool_content(result)
        assert extracted == "[image content]"

    def test_extract_tool_content_with_no_type_attribute(self):
        """Test extracting content from tool result with no type attribute."""
        # Mock content item without type attribute
        content_item = "plain string content"

        # Mock result with content
        result = MagicMock()
        result.content = [content_item]

        extracted = extract_tool_content(result)
        assert extracted == "plain string content"

    def test_extract_tool_content_with_empty_content(self):
        """Test extracting content from tool result with empty content."""
        # Mock result with empty content
        result = MagicMock()
        result.content = []

        extracted = extract_tool_content(result)
        assert extracted == ""

    def test_extract_tool_content_with_no_content(self):
        """Test extracting content from tool result with no content attribute."""
        # Mock result with no content
        result = MagicMock()
        result.content = None

        extracted = extract_tool_content(result)
        assert extracted == ""
