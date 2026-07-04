"""
JARVIS MCP Server — Model Context Protocol integration for tool calling

Based on Friday's FastMCP architecture but integrated with JARVIS.
Provides tools, prompts, and resources for LLM reasoning and execution.

Architecture:
  MCP Server (port 8000 SSE)
    ├─ Tools
    │   ├─ web_search()
    │   ├─ fetch_url()
    │   ├─ get_world_news()
    │   ├─ get_system_info()
    │   ├─ get_current_time()
    │   └─ ...
    ├─ Prompts
    │   ├─ reasoning (extended context)
    │   ├─ summarization
    │   └─ code_explanation
    └─ Resources
        ├─ jarvis://info (system info)
        ├─ jarvis://config (settings)
        └─ jarvis://status (health)
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

LOGGER = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# MCP Tool Definition
# ─────────────────────────────────────────────────────────────────────────────

class ToolType(Enum):
    """Types of MCP tools."""
    WEB_SEARCH = "web_search"
    FETCH_URL = "fetch_url"
    GET_NEWS = "get_news"
    SYSTEM_INFO = "system_info"
    CURRENT_TIME = "current_time"
    WEATHER = "weather"
    FINANCE = "finance"
    CALCULATOR = "calculator"
    STORAGE = "storage"
    CUSTOM = "custom"


class MCPTool:
    """Represents a single MCP tool."""
    
    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        tool_type: ToolType = ToolType.CUSTOM,
        enabled: bool = True,
        requires_api_key: Optional[str] = None,
    ):
        """Initialize a tool.
        
        Args:
            name: Tool name (lowercase, snake_case)
            description: Human-readable description
            parameters: JSON schema for parameters
            tool_type: Tool category
            enabled: Whether tool is available
            requires_api_key: API key environment variable name
        """
        self.name = name
        self.description = description
        self.parameters = parameters
        self.tool_type = tool_type
        self.enabled = enabled
        self.requires_api_key = requires_api_key

    def is_available(self) -> bool:
        """Check if tool is available (API key present if required)."""
        if not self.enabled:
            return False
        
        if self.requires_api_key:
            return bool(os.getenv(self.requires_api_key))
        
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize tool to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "type": self.tool_type.value,
            "enabled": self.enabled,
            "available": self.is_available(),
        }


# ─────────────────────────────────────────────────────────────────────────────
# MCP Prompt Definition
# ─────────────────────────────────────────────────────────────────────────────

class MCPPrompt:
    """Represents a reusable prompt template."""
    
    def __init__(
        self,
        name: str,
        description: str,
        template: str,
        input_schema: Dict[str, Any],
    ):
        """Initialize a prompt.
        
        Args:
            name: Prompt name
            description: What the prompt does
            template: Prompt template with {variable} placeholders
            input_schema: JSON schema for template variables
        """
        self.name = name
        self.description = description
        self.template = template
        self.input_schema = input_schema

    def render(self, **kwargs) -> str:
        """Render prompt with variables."""
        return self.template.format(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize prompt to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "template": self.template,
            "input_schema": self.input_schema,
        }


# ─────────────────────────────────────────────────────────────────────────────
# MCP Resource Definition
# ─────────────────────────────────────────────────────────────────────────────

class MCPResource:
    """Represents a resource that can be queried."""
    
    def __init__(
        self,
        uri: str,
        name: str,
        description: str,
        mime_type: str = "application/json",
    ):
        """Initialize a resource.
        
        Args:
            uri: Resource URI (e.g., "jarvis://info")
            name: Resource name
            description: Resource description
            mime_type: Content type
        """
        self.uri = uri
        self.name = name
        self.description = description
        self.mime_type = mime_type

    def to_dict(self) -> Dict[str, Any]:
        """Serialize resource to dictionary."""
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mime_type": self.mime_type,
        }


# ─────────────────────────────────────────────────────────────────────────────
# MCP Server Registry
# ─────────────────────────────────────────────────────────────────────────────

class MCPServerRegistry:
    """Registry for all MCP tools, prompts, and resources."""
    
    def __init__(self, name: str = "JARVIS"):
        """Initialize registry.
        
        Args:
            name: Server name
        """
        self.name = name
        self.tools: Dict[str, MCPTool] = {}
        self.prompts: Dict[str, MCPPrompt] = {}
        self.resources: Dict[str, MCPResource] = {}
        self._initialized = False

    def register_tool(self, tool: MCPTool) -> None:
        """Register a tool."""
        self.tools[tool.name] = tool
        LOGGER.info(f"Registered tool: {tool.name}")

    def register_prompt(self, prompt: MCPPrompt) -> None:
        """Register a prompt."""
        self.prompts[prompt.name] = prompt
        LOGGER.info(f"Registered prompt: {prompt.name}")

    def register_resource(self, resource: MCPResource) -> None:
        """Register a resource."""
        self.resources[resource.uri] = resource
        LOGGER.info(f"Registered resource: {resource.uri}")

    def get_tool(self, name: str) -> Optional[MCPTool]:
        """Get tool by name."""
        return self.tools.get(name)

    def get_available_tools(self) -> List[MCPTool]:
        """Get list of available tools."""
        return [t for t in self.tools.values() if t.is_available()]

    def get_available_prompts(self) -> List[MCPPrompt]:
        """Get list of available prompts."""
        return list(self.prompts.values())

    def get_available_resources(self) -> List[MCPResource]:
        """Get list of available resources."""
        return list(self.resources.values())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize registry to dictionary."""
        return {
            "server": self.name,
            "tools": {
                "total": len(self.tools),
                "available": len(self.get_available_tools()),
                "list": [t.to_dict() for t in self.get_available_tools()],
            },
            "prompts": {
                "total": len(self.prompts),
                "list": [p.to_dict() for p in self.prompts.values()],
            },
            "resources": {
                "total": len(self.resources),
                "list": [r.to_dict() for r in self.resources.values()],
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# Global Registry Instance
# ─────────────────────────────────────────────────────────────────────────────

_global_registry: Optional[MCPServerRegistry] = None


def init_mcp_server(name: str = "JARVIS") -> MCPServerRegistry:
    """Initialize the global MCP server registry."""
    global _global_registry
    _global_registry = MCPServerRegistry(name)
    return _global_registry


def get_mcp_server() -> MCPServerRegistry:
    """Get the global MCP server registry (auto-initializes if needed)."""
    global _global_registry
    if _global_registry is None:
        _global_registry = MCPServerRegistry()
    return _global_registry


def register_tool(tool: MCPTool) -> None:
    """Register a tool with the global server."""
    get_mcp_server().register_tool(tool)


def register_prompt(prompt: MCPPrompt) -> None:
    """Register a prompt with the global server."""
    get_mcp_server().register_prompt(prompt)


def register_resource(resource: MCPResource) -> None:
    """Register a resource with the global server."""
    get_mcp_server().register_resource(resource)


def get_available_tools() -> List[MCPTool]:
    """Get list of available tools."""
    return get_mcp_server().get_available_tools()


def get_available_prompts() -> List[MCPPrompt]:
    """Get list of available prompts."""
    return get_mcp_server().get_available_prompts()


def get_mcp_status() -> Dict[str, Any]:
    """Get MCP server status."""
    return get_mcp_server().to_dict()


__all__ = [
    "MCPTool",
    "MCPPrompt",
    "MCPResource",
    "MCPServerRegistry",
    "ToolType",
    "init_mcp_server",
    "get_mcp_server",
    "register_tool",
    "register_prompt",
    "register_resource",
    "get_available_tools",
    "get_available_prompts",
    "get_mcp_status",
]
