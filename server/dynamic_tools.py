"""Dynamic tool transformation capabilities for FastMCP 2.x.

Integrates with configuration system to create adaptive tools.
"""

import logging
from typing import Any, cast

import yaml
from fastmcp import FastMCP

logger = logging.getLogger(__name__)


class DynamicToolManager:
    """Manages dynamic tool transformation based on configuration changes."""

    def __init__(self, mcp_server: FastMCP[Any], config: dict[str, Any]) -> None:
        """Initialize the DynamicToolManager.

        Args:
            mcp_server: The FastMCP server instance to register tools with
            config: Configuration dictionary containing tool settings
        """
        self.mcp_server = mcp_server
        self.config = config
        self.dynamic_tools: dict[str, Any] = {}  # Track dynamically created tools

    async def transform_tools_based_on_config(self) -> None:
        """Transform tools based on current configuration."""
        logger.info("Transforming tools based on configuration...")

        # Update existing tools
        await self._update_configuration_tools()
        await self._update_openai_tools()
        await self._update_logging_tools()
        await self._update_chatbot_tools()

        logger.info(
            "Tool transformation complete. Dynamic tools created: %s",
            len(self.dynamic_tools),
        )

    async def _update_configuration_tools(self) -> None:
        """Update configuration management tools based on current config."""
        # Create section-specific tools dynamically
        for section in self.config:
            tool_name = f"get_{section}_config"
            if tool_name not in self.dynamic_tools:
                await self._create_section_tool(section)

    async def _create_section_tool(self, section: str) -> None:
        """Create a dynamic tool for a specific configuration section."""
        tool_name = f"get_{section}_config"

        # Check if tool already exists
        if tool_name in self.dynamic_tools:
            return

        @self.mcp_server.tool(
            name=tool_name,
            description=f"Get current {section} configuration with detailed explanations",
        )
        async def section_tool() -> str:
            if section in self.config:
                config_data = self.config[section]
                if isinstance(config_data, dict):
                    config_dict = cast("dict[str, Any]", config_data)
                    available_keys: list[str] = list(config_dict.keys())
                else:
                    available_keys: list[str] = []
                result: dict[str, Any] = {
                    "section": section,
                    "configuration": config_data,
                    "available_keys": available_keys,
                    "description": self.get_section_description(section),
                }
                return yaml.dump(result, default_flow_style=False)
            return f"Configuration section '{section}' not found"

        self.dynamic_tools[tool_name] = section_tool
        logger.debug("Created dynamic tool: %s", tool_name)

    async def _update_openai_tools(self) -> None:
        """Create OpenAI-specific tools if OpenAI section exists."""
        if "openai" not in self.config:
            return

        openai_config = self.config["openai"]
        tool_name = "get_current_model_capabilities"

        # Check if tool already exists
        if tool_name in self.dynamic_tools:
            return

        @self.mcp_server.tool(
            name=tool_name,
            description="Get capabilities and limits of the currently configured OpenAI model",
        )
        async def model_capabilities() -> str:
            model = openai_config.get("model", "unknown")
            max_tokens = openai_config.get("max_tokens", "unknown")
            temperature = openai_config.get("temperature", "unknown")

            capabilities = {
                "current_model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "model_capabilities": self.get_model_info(model),
                "current_settings": openai_config,
            }
            return yaml.dump(capabilities, default_flow_style=False)

        self.dynamic_tools[tool_name] = model_capabilities
        logger.debug("Created OpenAI-specific dynamic tools")

    async def _update_logging_tools(self) -> None:
        """Create logging-specific tools if logging section exists."""
        if "logging" not in self.config:
            return

        logging_config = self.config["logging"]
        current_level = logging_config.get("level", "INFO")
        tool_name = "analyze_logging_performance"

        # Check if tool already exists
        if tool_name in self.dynamic_tools:
            return

        @self.mcp_server.tool(
            name=tool_name,
            description="Analyze current logging configuration and suggest optimizations",
        )
        async def analyze_logging() -> str:
            analysis: dict[str, Any] = {
                "current_config": logging_config,
                "performance_impact": self.get_logging_performance_impact(
                    current_level
                ),
                "recommendations": self.get_logging_recommendations(
                    current_level, enabled=logging_config.get("enabled", True)
                ),
            }
            return yaml.dump(analysis, default_flow_style=False)

        self.dynamic_tools[tool_name] = analyze_logging
        logger.debug("Created logging-specific dynamic tools")

    async def _update_chatbot_tools(self) -> None:
        """Create chatbot-specific tools if chatbot section exists."""
        if "chatbot" not in self.config:
            return

        chatbot_config = self.config["chatbot"]
        tool_name = "analyze_conversation_settings"

        # Check if tool already exists
        if tool_name in self.dynamic_tools:
            return

        @self.mcp_server.tool(
            name=tool_name,
            description="Analyze current chatbot conversation settings and memory usage",
        )
        async def analyze_conversation() -> str:
            max_history = chatbot_config.get("max_conversation_history", 100)
            system_prompt = chatbot_config.get("system_prompt", "")

            analysis = {
                "current_settings": chatbot_config,
                "memory_usage": f"Storing up to {max_history} messages",
                "prompt_analysis": {
                    "length": len(system_prompt),
                    "tone": self.analyze_prompt_tone(system_prompt),
                },
            }
            return yaml.dump(analysis, default_flow_style=False)

        self.dynamic_tools[tool_name] = analyze_conversation
        logger.debug("Created chatbot-specific dynamic tools")

    def get_section_description(self, section: str) -> str:
        """Get description for a configuration section."""
        descriptions = {
            "openai": (
                "OpenAI API configuration including model, temperature, and token limits"
            ),
            "chatbot": (
                "Chatbot behavior settings including conversation history and system prompts"
            ),
            "logging": (
                "Logging configuration including level, file location, and enabling/disabling"
            ),
        }
        return descriptions.get(section, f"Configuration settings for {section}")

    def get_model_info(self, model: str) -> dict[str, Any]:
        """Get information about OpenAI model capabilities."""
        model_info = {
            "gpt-4o-mini": {
                "context_window": 128000,
                "training_data": "2023-10",
                "best_for": "fast responses",
            },
            "gpt-4o": {
                "context_window": 128000,
                "training_data": "2023-10",
                "best_for": "complex reasoning",
            },
        }
        return model_info.get(
            model, {"context_window": "unknown", "best_for": "general use"}
        )

    def get_logging_performance_impact(self, level: str) -> str:
        """Analyze performance impact of logging level."""
        impacts = {
            "DEBUG": "High I/O impact, detailed information",
            "INFO": "Moderate I/O impact, standard information",
            "WARNING": "Low I/O impact, only warnings and errors",
        }
        return impacts.get(level, "Unknown impact")

    def get_logging_recommendations(self, level: str, *, enabled: bool) -> list[str]:
        """Get logging recommendations."""
        recommendations: list[str] = []
        if level == "DEBUG":
            recommendations.append("Consider INFO level for production")
        if not enabled:
            recommendations.append("Enable logging for troubleshooting")
        return recommendations

    def analyze_prompt_tone(self, prompt: str) -> str:
        """Analyze the tone of system prompt."""
        prompt_lower = prompt.lower()
        if "sarcastic" in prompt_lower:
            return "sarcastic/humorous"
        if "helpful" in prompt_lower:
            return "helpful/professional"
        return "neutral"

    async def regenerate_all_tools(self) -> None:
        """Update dynamic tools based on current configuration without recreating existing ones."""
        logger.info("Updating dynamic tools based on configuration...")
        # Don't clear existing tools - just update configuration and create any missing ones
        await self.transform_tools_based_on_config()
