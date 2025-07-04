"""Tests for dynamic tool management."""

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.dynamic_tools import DynamicToolManager


class TestDynamicToolManager:
    """Test suite for DynamicToolManager class."""

    def test_dynamic_tool_manager_initialization(self):
        """Test DynamicToolManager initialization."""
        mock_mcp_server = MagicMock()
        config: Dict[str, Any] = {"openai": {"model": "gpt-4o-mini"}}

        manager = DynamicToolManager(mock_mcp_server, config)

        assert manager.mcp_server == mock_mcp_server
        assert manager.config == config
        assert manager.dynamic_tools == {}

    @pytest.mark.asyncio
    async def test_transform_tools_based_on_config(self):
        """Test transform_tools_based_on_config method."""
        mock_mcp_server = MagicMock()
        config: Dict[str, Any] = {
            "openai": {"model": "gpt-4o-mini", "temperature": 0.7},
            "chatbot": {"system_prompt": "You are helpful"},
            "logging": {"level": "INFO"},
        }

        manager = DynamicToolManager(mock_mcp_server, config)

        # Mock the private methods using patch
        with (
            patch.object(
                manager, "_update_configuration_tools", new_callable=AsyncMock
            ) as mock_config,
            patch.object(
                manager, "_update_openai_tools", new_callable=AsyncMock
            ) as mock_openai,
            patch.object(
                manager, "_update_logging_tools", new_callable=AsyncMock
            ) as mock_logging,
            patch.object(
                manager, "_update_chatbot_tools", new_callable=AsyncMock
            ) as mock_chatbot,
        ):

            await manager.transform_tools_based_on_config()

            # Verify all update methods were called
            mock_config.assert_called_once()
            mock_openai.assert_called_once()
            mock_logging.assert_called_once()
            mock_chatbot.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_configuration_tools(self):
        """Test _update_configuration_tools method."""
        mock_mcp_server = MagicMock()
        config: Dict[str, Dict[str, Any]] = {"openai": {}, "chatbot": {}}

        manager = DynamicToolManager(mock_mcp_server, config)

        with patch.object(
            manager, "_create_section_tool", new_callable=AsyncMock
        ) as mock_create:
            await manager._update_configuration_tools()  # type: ignore[protected]

            # Should call _create_section_tool for each config section
            assert mock_create.call_count == 2
            mock_create.assert_any_call("openai")
            mock_create.assert_any_call("chatbot")

    @pytest.mark.asyncio
    async def test_create_section_tool_new_tool(self):
        """Test _create_section_tool for new tool creation."""
        mock_mcp_server = MagicMock()
        mock_tool_decorator = MagicMock()
        mock_mcp_server.tool = mock_tool_decorator

        config: Dict[str, Any] = {"openai": {"model": "gpt-4o-mini"}}
        manager = DynamicToolManager(mock_mcp_server, config)

        await manager._create_section_tool("openai")  # type: ignore[protected]

        # Should create the tool
        assert "get_openai_config" in manager.dynamic_tools
        mock_tool_decorator.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_section_tool_existing_tool(self):
        """Test _create_section_tool when tool already exists."""
        mock_mcp_server = MagicMock()
        config: Dict[str, Any] = {"openai": {"model": "gpt-4o-mini"}}
        manager = DynamicToolManager(mock_mcp_server, config)

        # Add existing tool
        manager.dynamic_tools["get_openai_config"] = MagicMock()

        await manager._create_section_tool("openai")  # type: ignore[protected]

        # Should not create new tool
        assert len(manager.dynamic_tools) == 1

    @pytest.mark.asyncio
    async def test_update_openai_tools_with_openai_config(self):
        """Test _update_openai_tools when OpenAI config exists."""
        mock_mcp_server = MagicMock()
        mock_tool_decorator = MagicMock()
        mock_mcp_server.tool = mock_tool_decorator

        config: Dict[str, Any] = {
            "openai": {"model": "gpt-4o-mini", "max_tokens": 2000}
        }
        manager = DynamicToolManager(mock_mcp_server, config)

        await manager._update_openai_tools()  # type: ignore[protected]

        # Should create OpenAI tool
        assert "get_current_model_capabilities" in manager.dynamic_tools
        mock_tool_decorator.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_openai_tools_without_openai_config(self):
        """Test _update_openai_tools when OpenAI config doesn't exist."""
        mock_mcp_server = MagicMock()
        config: Dict[str, Any] = {"chatbot": {"system_prompt": "test"}}
        manager = DynamicToolManager(mock_mcp_server, config)

        await manager._update_openai_tools()  # type: ignore[protected]

        # Should not create any tools
        assert len(manager.dynamic_tools) == 0

    @pytest.mark.asyncio
    async def test_update_logging_tools_with_logging_config(self):
        """Test _update_logging_tools when logging config exists."""
        mock_mcp_server = MagicMock()
        mock_tool_decorator = MagicMock()
        mock_mcp_server.tool = mock_tool_decorator

        config: Dict[str, Any] = {"logging": {"level": "INFO", "enabled": True}}
        manager = DynamicToolManager(mock_mcp_server, config)

        await manager._update_logging_tools()  # type: ignore[protected]

        # Should create logging tool
        assert "analyze_logging_performance" in manager.dynamic_tools
        mock_tool_decorator.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_chatbot_tools_with_chatbot_config(self):
        """Test _update_chatbot_tools when chatbot config exists."""
        mock_mcp_server = MagicMock()
        mock_tool_decorator = MagicMock()
        mock_mcp_server.tool = mock_tool_decorator

        config: Dict[str, Any] = {
            "chatbot": {
                "system_prompt": "You are helpful",
                "max_conversation_history": 100,
            }
        }
        manager = DynamicToolManager(mock_mcp_server, config)

        await manager._update_chatbot_tools()  # type: ignore[protected]

        # Should create chatbot tool
        assert "analyze_conversation_settings" in manager.dynamic_tools
        mock_tool_decorator.assert_called_once()

    def test_get_section_description_known_sections(self):
        """Test get_section_description for known sections."""
        mock_mcp_server = MagicMock()
        config: Dict[str, Any] = {}
        manager = DynamicToolManager(mock_mcp_server, config)

        # Test known sections
        assert "OpenAI API configuration" in manager.get_section_description("openai")
        assert "Chatbot behavior settings" in manager.get_section_description("chatbot")
        assert "Logging configuration" in manager.get_section_description("logging")

    def test_get_section_description_unknown_section(self):
        """Test get_section_description for unknown section."""
        mock_mcp_server = MagicMock()
        config: Dict[str, Any] = {}
        manager = DynamicToolManager(mock_mcp_server, config)

        result = manager.get_section_description("unknown_section")
        assert "Configuration settings for unknown_section" in result

    def test_get_model_info_known_models(self):
        """Test get_model_info for known models."""
        mock_mcp_server = MagicMock()
        config: Dict[str, Any] = {}
        manager = DynamicToolManager(mock_mcp_server, config)

        # Test known models
        gpt4o_info = manager.get_model_info("gpt-4o")
        assert gpt4o_info["context_window"] == 128000
        assert gpt4o_info["best_for"] == "complex reasoning"

        gpt4o_mini_info = manager.get_model_info("gpt-4o-mini")
        assert gpt4o_mini_info["context_window"] == 128000
        assert gpt4o_mini_info["best_for"] == "fast responses"

    def test_get_model_info_unknown_model(self):
        """Test get_model_info for unknown model."""
        mock_mcp_server = MagicMock()
        config: Dict[str, Any] = {}
        manager = DynamicToolManager(mock_mcp_server, config)

        result = manager.get_model_info("unknown-model")
        assert result["context_window"] == "unknown"
        assert result["best_for"] == "general use"

    def test_get_logging_performance_impact_known_levels(self):
        """Test get_logging_performance_impact for known levels."""
        mock_mcp_server = MagicMock()
        config: Dict[str, Any] = {}
        manager = DynamicToolManager(mock_mcp_server, config)

        # Test known levels
        assert "High I/O impact" in manager.get_logging_performance_impact("DEBUG")
        assert "Moderate I/O impact" in manager.get_logging_performance_impact("INFO")
        assert "Low I/O impact" in manager.get_logging_performance_impact("WARNING")

    def test_get_logging_performance_impact_unknown_level(self):
        """Test get_logging_performance_impact for unknown level."""
        mock_mcp_server = MagicMock()
        config: Dict[str, Any] = {}
        manager = DynamicToolManager(mock_mcp_server, config)

        result = manager.get_logging_performance_impact("UNKNOWN")
        assert result == "Unknown impact"

    def test_get_logging_recommendations_debug_level(self):
        """Test get_logging_recommendations for DEBUG level."""
        mock_mcp_server = MagicMock()
        config: Dict[str, Any] = {}
        manager = DynamicToolManager(mock_mcp_server, config)

        recommendations = manager.get_logging_recommendations("DEBUG", enabled=True)
        assert "Consider INFO level for production" in recommendations

    def test_get_logging_recommendations_disabled_logging(self):
        """Test get_logging_recommendations for disabled logging."""
        mock_mcp_server = MagicMock()
        config: Dict[str, Any] = {}
        manager = DynamicToolManager(mock_mcp_server, config)

        recommendations = manager.get_logging_recommendations("INFO", enabled=False)
        assert "Enable logging for troubleshooting" in recommendations

    def test_get_logging_recommendations_no_recommendations(self):
        """Test get_logging_recommendations when no recommendations needed."""
        mock_mcp_server = MagicMock()
        config: Dict[str, Any] = {}
        manager = DynamicToolManager(mock_mcp_server, config)

        recommendations = manager.get_logging_recommendations("INFO", enabled=True)
        assert len(recommendations) == 0

    def test_analyze_prompt_tone_sarcastic(self):
        """Test analyze_prompt_tone for sarcastic prompt."""
        mock_mcp_server = MagicMock()
        config: Dict[str, Any] = {}
        manager = DynamicToolManager(mock_mcp_server, config)

        result = manager.analyze_prompt_tone("You are a sarcastic assistant")
        assert result == "sarcastic/humorous"

    def test_analyze_prompt_tone_helpful(self):
        """Test analyze_prompt_tone for helpful prompt."""
        mock_mcp_server = MagicMock()
        config: Dict[str, Any] = {}
        manager = DynamicToolManager(mock_mcp_server, config)

        result = manager.analyze_prompt_tone("You are a helpful assistant")
        assert result == "helpful/professional"

    def test_analyze_prompt_tone_neutral(self):
        """Test analyze_prompt_tone for neutral prompt."""
        mock_mcp_server = MagicMock()
        config: Dict[str, Any] = {}
        manager = DynamicToolManager(mock_mcp_server, config)

        result = manager.analyze_prompt_tone("You are an assistant")
        assert result == "neutral"

    @pytest.mark.asyncio
    async def test_regenerate_all_tools(self):
        """Test regenerate_all_tools method."""
        mock_mcp_server = MagicMock()
        config: Dict[str, Any] = {"openai": {"model": "gpt-4o-mini"}}
        manager = DynamicToolManager(mock_mcp_server, config)

        # Mock the transform method
        with patch.object(
            manager, "transform_tools_based_on_config", new_callable=AsyncMock
        ) as mock_transform:
            await manager.regenerate_all_tools()

            # Should call transform_tools_based_on_config
            mock_transform.assert_called_once()

    def test_dynamic_tools_tracking(self):
        """Test that dynamic tools are properly tracked."""
        mock_mcp_server = MagicMock()
        mock_tool_decorator = MagicMock()
        mock_mcp_server.tool = mock_tool_decorator

        config: Dict[str, Any] = {"openai": {"model": "gpt-4o-mini"}}
        manager = DynamicToolManager(mock_mcp_server, config)

        # Initially empty
        assert len(manager.dynamic_tools) == 0

        # Add a tool manually
        manager.dynamic_tools["test_tool"] = MagicMock()
        assert len(manager.dynamic_tools) == 1
        assert "test_tool" in manager.dynamic_tools

    def test_config_access(self):
        """Test that config is properly accessible."""
        mock_mcp_server = MagicMock()
        config: Dict[str, Any] = {
            "openai": {"model": "gpt-4o-mini"},
            "chatbot": {"system_prompt": "test"},
        }
        manager = DynamicToolManager(mock_mcp_server, config)

        assert manager.config["openai"]["model"] == "gpt-4o-mini"
        assert manager.config["chatbot"]["system_prompt"] == "test"
        assert len(manager.config) == 2
