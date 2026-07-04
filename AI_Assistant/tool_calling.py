"""
JARVIS Tool Calling System — LLM invokes tools dynamically

Enables the LLM to:
  - Request tool execution
  - Pass parameters
  - Handle results
  - Chain multiple tools
  - Fallback on errors

Architecture:
  LLM generates tool call
    ↓
  Tool Executor validates parameters
    ↓
  Execute tool function
    ↓
  Return result to LLM
    ↓
  LLM incorporates into response
"""

import json
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
import inspect

LOGGER = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Tool Call Definition
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ToolCall:
    """Represents a tool call request."""
    tool_name: str
    parameters: Dict[str, Any]
    call_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "call_id": self.call_id,
        }


@dataclass
class ToolResult:
    """Represents a tool execution result."""
    tool_name: str
    call_id: Optional[str]
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "call_id": self.call_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Tool Executor
# ─────────────────────────────────────────────────────────────────────────────

class ToolExecutor:
    """Executes tool calls from the LLM."""
    
    def __init__(self):
        """Initialize executor."""
        self.tools: Dict[str, Callable] = {}
        self.call_history: List[ToolResult] = []
        self._import_tools()
    
    def _import_tools(self) -> None:
        """Import all tool functions."""
        # Web tools
        try:
            from mcp_web_tools import web_search, fetch_url, get_world_news, open_world_monitor
            self.register_tool("web_search", web_search)
            self.register_tool("fetch_url", fetch_url)
            self.register_tool("get_world_news", get_world_news)
            self.register_tool("open_world_monitor", open_world_monitor)
            LOGGER.info("✓ Web tools registered")
        except ImportError as e:
            LOGGER.warning(f"Web tools not available: {e}")
        
        # System tools
        try:
            from mcp_system_tools import (
                get_system_info, get_current_time, get_disk_usage,
                list_running_processes, get_environment_stats
            )
            self.register_tool("get_system_info", get_system_info)
            self.register_tool("get_current_time", get_current_time)
            self.register_tool("get_disk_usage", get_disk_usage)
            self.register_tool("list_running_processes", list_running_processes)
            self.register_tool("get_environment_stats", get_environment_stats)
            LOGGER.info("✓ System tools registered")
        except ImportError as e:
            LOGGER.warning(f"System tools not available: {e}")
    
    def register_tool(self, name: str, func: Callable) -> None:
        """Register a tool function.
        
        Args:
            name: Tool name
            func: Callable tool function
        """
        self.tools[name] = func
        LOGGER.debug(f"Registered tool: {name}")
    
    def parse_tool_call(self, llm_response: str) -> Optional[ToolCall]:
        """
        Parse LLM response for tool calls.
        
        Expects format like:
        ```json
        {
          "tool_call": {
            "tool_name": "web_search",
            "parameters": {"query": "..."},
            "call_id": "call_123"
          }
        }
        ```
        """
        try:
            # Try to extract JSON from response
            if "```json" in llm_response:
                json_str = llm_response.split("```json")[1].split("```")[0]
            elif "{" in llm_response:
                json_str = llm_response[llm_response.find("{"):llm_response.rfind("}")+1]
            else:
                return None
            
            data = json.loads(json_str)
            
            if "tool_call" in data:
                tc = data["tool_call"]
                return ToolCall(
                    tool_name=tc.get("tool_name"),
                    parameters=tc.get("parameters", {}),
                    call_id=tc.get("call_id"),
                )
        
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            LOGGER.debug(f"Could not parse tool call: {e}")
        
        return None
    
    def execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """
        Execute a tool call.
        
        Args:
            tool_call: ToolCall to execute
            
        Returns:
            ToolResult with outcome
        """
        import time
        
        start_time = time.time()
        
        try:
            # Check if tool exists
            if tool_call.tool_name not in self.tools:
                return ToolResult(
                    tool_name=tool_call.tool_name,
                    call_id=tool_call.call_id,
                    success=False,
                    result=None,
                    error=f"Tool '{tool_call.tool_name}' not found",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )
            
            # Get tool function
            tool_func = self.tools[tool_call.tool_name]
            
            # Validate parameters
            sig = inspect.signature(tool_func)
            try:
                # Bind arguments to check validity
                bound = sig.bind_partial(**tool_call.parameters)
                bound.apply_defaults()
            except TypeError as e:
                return ToolResult(
                    tool_name=tool_call.tool_name,
                    call_id=tool_call.call_id,
                    success=False,
                    result=None,
                    error=f"Parameter error: {e}",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )
            
            # Execute tool
            LOGGER.info(f"Executing tool: {tool_call.tool_name}")
            result = tool_func(**tool_call.parameters)
            
            tool_result = ToolResult(
                tool_name=tool_call.tool_name,
                call_id=tool_call.call_id,
                success=True,
                result=result,
                execution_time_ms=(time.time() - start_time) * 1000,
            )
            
            # Store in history
            self.call_history.append(tool_result)
            
            LOGGER.info(f"Tool succeeded: {tool_call.tool_name} ({tool_result.execution_time_ms:.0f}ms)")
            
            return tool_result
        
        except Exception as e:
            LOGGER.error(f"Tool execution error: {e}")
            return ToolResult(
                tool_name=tool_call.tool_name,
                call_id=tool_call.call_id,
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
            )
    
    def handle_llm_response(self, llm_response: str) -> Optional[ToolResult]:
        """
        Process LLM response and execute any tool calls.
        
        Args:
            llm_response: Response from LLM
            
        Returns:
            ToolResult if tool was called, None otherwise
        """
        tool_call = self.parse_tool_call(llm_response)
        
        if tool_call:
            LOGGER.debug(f"Parsed tool call: {tool_call.tool_name}")
            return self.execute_tool(tool_call)
        
        return None
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        return list(self.tools.keys())
    
    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get information about a specific tool."""
        if tool_name not in self.tools:
            return None
        
        func = self.tools[tool_name]
        sig = inspect.signature(func)
        
        return {
            "name": tool_name,
            "description": func.__doc__ or "No description",
            "parameters": {
                param_name: {
                    "type": param.annotation.__name__ if param.annotation != inspect.Parameter.empty else "Any",
                    "default": param.default if param.default != inspect.Parameter.empty else None,
                }
                for param_name, param in sig.parameters.items()
            },
        }
    
    def get_all_tools_info(self) -> List[Dict[str, Any]]:
        """Get information about all tools."""
        return [self.get_tool_info(name) for name in self.get_available_tools()]
    
    def get_call_history(self, limit: int = 10) -> List[ToolResult]:
        """Get recent tool calls."""
        return self.call_history[-limit:]


# ─────────────────────────────────────────────────────────────────────────────
# Global Executor
# ─────────────────────────────────────────────────────────────────────────────

_global_executor: Optional[ToolExecutor] = None


def init_tool_executor() -> ToolExecutor:
    """Initialize the global tool executor."""
    global _global_executor
    _global_executor = ToolExecutor()
    return _global_executor


def get_tool_executor() -> ToolExecutor:
    """Get the global tool executor (auto-initializes if needed)."""
    global _global_executor
    if _global_executor is None:
        _global_executor = ToolExecutor()
    return _global_executor


def execute_tool_call(tool_call: ToolCall) -> ToolResult:
    """Execute a tool call using the global executor."""
    return get_tool_executor().execute_tool(tool_call)


def handle_llm_response(llm_response: str) -> Optional[ToolResult]:
    """Process LLM response and execute tools if needed."""
    return get_tool_executor().handle_llm_response(llm_response)


__all__ = [
    "ToolCall",
    "ToolResult",
    "ToolExecutor",
    "init_tool_executor",
    "get_tool_executor",
    "execute_tool_call",
    "handle_llm_response",
]
