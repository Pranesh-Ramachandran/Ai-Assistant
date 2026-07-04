"""
JARVIS MCP System Tools — System information and utilities

Provides:
  - get_system_info() — CPU, RAM, disk, OS info
  - get_current_time() — Current time and timezone
  - get_disk_usage() — Storage information
  - list_running_processes() — Active processes
  - get_environment_stats() — System environment
"""

import os
import logging
import platform
import psutil
from typing import Dict, Any, List
from datetime import datetime
import socket

LOGGER = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# System Information
# ─────────────────────────────────────────────────────────────────────────────

def get_system_info() -> Dict[str, Any]:
    """
    Get comprehensive system information.
    
    Returns:
        System details including OS, CPU, RAM, hostname
    """
    try:
        import cpuinfo
        cpu_info = cpuinfo.get_cpu_info()
        cpu_brand = cpu_info.get('brand_raw', 'Unknown')
    except ImportError:
        cpu_brand = platform.processor()
    
    try:
        total_ram = psutil.virtual_memory().total / (1024**3)  # Convert to GB
        available_ram = psutil.virtual_memory().available / (1024**3)
        cpu_percent = psutil.cpu_percent(interval=1)
    except Exception as e:
        LOGGER.warning(f"Could not get system stats: {e}")
        total_ram = available_ram = cpu_percent = None
    
    return {
        "success": True,
        "system": {
            "hostname": socket.gethostname(),
            "os": platform.system(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
        },
        "cpu": {
            "brand": cpu_brand,
            "cores": os.cpu_count(),
            "current_usage_percent": cpu_percent,
        },
        "memory": {
            "total_gb": total_ram,
            "available_gb": available_ram,
            "used_percent": psutil.virtual_memory().percent if psutil else None,
        },
        "timestamp": datetime.now().isoformat(),
    }


def get_current_time() -> Dict[str, Any]:
    """
    Get current time and timezone information.
    
    Returns:
        Current datetime with timezone
    """
    import time
    import tzlocal
    
    try:
        timezone = tzlocal.get_localzone()
    except Exception:
        timezone = "UTC"
    
    now = datetime.now()
    
    return {
        "success": True,
        "current_time": now.isoformat(),
        "unix_timestamp": now.timestamp(),
        "timezone": str(timezone),
        "year": now.year,
        "month": now.month,
        "day": now.day,
        "hour": now.hour,
        "minute": now.minute,
        "second": now.second,
        "day_of_week": now.strftime("%A"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Storage Information
# ─────────────────────────────────────────────────────────────────────────────

def get_disk_usage() -> Dict[str, Any]:
    """
    Get disk usage information for all drives.
    
    Returns:
        Disk usage per drive
    """
    try:
        drives = {}
        
        # Get all disk partitions
        partitions = psutil.disk_partitions()
        
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                drives[partition.device] = {
                    "mount": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total_gb": usage.total / (1024**3),
                    "used_gb": usage.used / (1024**3),
                    "free_gb": usage.free / (1024**3),
                    "percent_used": usage.percent,
                }
            except PermissionError:
                continue
        
        return {
            "success": True,
            "drives": drives,
            "timestamp": datetime.now().isoformat(),
        }
    
    except Exception as e:
        LOGGER.error(f"Disk usage error: {e}")
        return {
            "success": False,
            "error": str(e),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Process Information
# ─────────────────────────────────────────────────────────────────────────────

def list_running_processes(limit: int = 10) -> Dict[str, Any]:
    """
    List running processes sorted by memory usage.
    
    Args:
        limit: Maximum number of processes to return
        
    Returns:
        List of running processes with CPU/memory info
    """
    try:
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent']):
            try:
                processes.append({
                    "pid": proc.info['pid'],
                    "name": proc.info['name'],
                    "memory_percent": proc.info['memory_percent'],
                    "cpu_percent": proc.info['cpu_percent'],
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by memory usage
        processes.sort(key=lambda x: x['memory_percent'], reverse=True)
        
        return {
            "success": True,
            "total_processes": len(processes),
            "top_processes": processes[:limit],
            "timestamp": datetime.now().isoformat(),
        }
    
    except Exception as e:
        LOGGER.error(f"Process list error: {e}")
        return {
            "success": False,
            "error": str(e),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Environment Statistics
# ─────────────────────────────────────────────────────────────────────────────

def get_environment_stats() -> Dict[str, Any]:
    """
    Get system environment statistics.
    
    Returns:
        Network, uptime, and other environment info
    """
    try:
        # Network interfaces
        network_stats = psutil.net_if_stats()
        network = {
            iface: {
                "is_up": stat.isup,
                "mtu": stat.mtu,
                "speed": stat.speed,
            }
            for iface, stat in network_stats.items()
        }
        
        # Boot time
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        
        return {
            "success": True,
            "network_interfaces": network,
            "boot_time": boot_time.isoformat(),
            "uptime_seconds": int(uptime.total_seconds()),
            "uptime_hours": uptime.total_seconds() / 3600,
            "timestamp": datetime.now().isoformat(),
        }
    
    except Exception as e:
        LOGGER.error(f"Environment stats error: {e}")
        return {
            "success": False,
            "error": str(e),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Tool Registration
# ─────────────────────────────────────────────────────────────────────────────

def register_system_tools(registry) -> None:
    """Register all system tools with MCP server."""
    from mcp_server import MCPTool, ToolType
    
    # System Info Tool
    registry.register_tool(MCPTool(
        name="get_system_info",
        description="Get comprehensive system information (OS, CPU, RAM, etc)",
        parameters={
            "type": "object",
            "properties": {},
        },
        tool_type=ToolType.SYSTEM_INFO,
    ))
    
    # Current Time Tool
    registry.register_tool(MCPTool(
        name="get_current_time",
        description="Get current time with timezone information",
        parameters={
            "type": "object",
            "properties": {},
        },
        tool_type=ToolType.CURRENT_TIME,
    ))
    
    # Disk Usage Tool
    registry.register_tool(MCPTool(
        name="get_disk_usage",
        description="Get disk usage statistics for all drives",
        parameters={
            "type": "object",
            "properties": {},
        },
        tool_type=ToolType.STORAGE,
    ))
    
    # Process List Tool
    registry.register_tool(MCPTool(
        name="list_running_processes",
        description="List running processes sorted by memory usage",
        parameters={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of processes to return",
                    "default": 10
                }
            },
        },
        tool_type=ToolType.SYSTEM_INFO,
    ))
    
    # Environment Stats Tool
    registry.register_tool(MCPTool(
        name="get_environment_stats",
        description="Get system environment statistics (network, uptime, etc)",
        parameters={
            "type": "object",
            "properties": {},
        },
        tool_type=ToolType.SYSTEM_INFO,
    ))


__all__ = [
    "get_system_info",
    "get_current_time",
    "get_disk_usage",
    "list_running_processes",
    "get_environment_stats",
    "register_system_tools",
]
