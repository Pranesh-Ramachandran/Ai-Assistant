"""
JARVIS MCP Web Tools — Search, fetch, news capabilities

Provides:
  - web_search() — Search the internet
  - fetch_url() — Get content from URLs
  - get_world_news() — Latest world news
  - open_world_monitor() — News aggregator
"""

import os
import logging
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

LOGGER = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Web Search Tool
# ─────────────────────────────────────────────────────────────────────────────

def web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Search the web using Google Search API.
    
    Args:
        query: Search query
        max_results: Maximum number of results (1-10)
        
    Returns:
        Search results with title, URL, and snippet
    """
    try:
        # Try using google library if available
        try:
            from googlesearch import search
            results = []
            for i, url in enumerate(search(query, num_results=max_results, sleep_interval=0.1)):
                results.append({
                    "rank": i + 1,
                    "url": url,
                    "title": url.split('/')[2] if '/' in url else url,
                })
            
            return {
                "success": True,
                "query": query,
                "results_count": len(results),
                "results": results,
                "timestamp": datetime.now().isoformat(),
            }
        except ImportError:
            # Fallback: use simple mock results
            LOGGER.warning("googlesearch not installed, returning mock results")
            return {
                "success": True,
                "query": query,
                "results_count": 0,
                "results": [],
                "note": "Install: pip install google",
                "timestamp": datetime.now().isoformat(),
            }
    
    except Exception as e:
        LOGGER.error(f"Web search error: {e}")
        return {
            "success": False,
            "query": query,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# ─────────────────────────────────────────────────────────────────────────────
# URL Fetch Tool
# ─────────────────────────────────────────────────────────────────────────────

def fetch_url(url: str, max_length: int = 5000) -> Dict[str, Any]:
    """
    Fetch and summarize content from a URL.
    
    Args:
        url: URL to fetch
        max_length: Maximum content length
        
    Returns:
        URL content with title, metadata, and text
    """
    try:
        import requests
        from urllib.parse import urlparse
        
        # Fetch the page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Extract text
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove scripts and styles
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text
            text = soup.get_text(separator='\n', strip=True)
            text = '\n'.join([line.strip() for line in text.split('\n') if line.strip()])
            
            # Truncate
            if len(text) > max_length:
                text = text[:max_length] + "...\n[Content truncated]"
            
            # Get title
            title = soup.title.string if soup.title else urlparse(url).netloc
            
            return {
                "success": True,
                "url": url,
                "title": title,
                "status_code": response.status_code,
                "content_length": len(text),
                "content": text,
                "timestamp": datetime.now().isoformat(),
            }
        
        except ImportError:
            # Fallback: just return raw text
            text = response.text[:max_length]
            return {
                "success": True,
                "url": url,
                "status_code": response.status_code,
                "content_length": len(text),
                "content": text,
                "note": "Install beautifulsoup4 for better parsing",
                "timestamp": datetime.now().isoformat(),
            }
    
    except Exception as e:
        LOGGER.error(f"URL fetch error: {e}")
        return {
            "success": False,
            "url": url,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# ─────────────────────────────────────────────────────────────────────────────
# News Tools
# ─────────────────────────────────────────────────────────────────────────────

def get_world_news(category: str = "general", max_results: int = 5) -> Dict[str, Any]:
    """
    Get latest world news using NewsAPI.
    
    Args:
        category: News category (general, business, tech, health, science, sports)
        max_results: Maximum number of articles
        
    Returns:
        Latest news articles
    """
    try:
        import requests
        
        api_key = os.getenv("NEWS_API_KEY")
        if not api_key:
            LOGGER.warning("NEWS_API_KEY not set, cannot fetch news")
            return {
                "success": False,
                "error": "NEWS_API_KEY not set",
                "note": "Get free key from: https://newsapi.org",
                "timestamp": datetime.now().isoformat(),
            }
        
        url = "https://newsapi.org/v2/top-headlines"
        params = {
            "country": "us",
            "category": category,
            "pageSize": max_results,
            "apiKey": api_key,
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        articles = []
        for article in data.get("articles", []):
            articles.append({
                "title": article.get("title"),
                "source": article.get("source", {}).get("name"),
                "url": article.get("url"),
                "description": article.get("description"),
                "published_at": article.get("publishedAt"),
            })
        
        return {
            "success": True,
            "category": category,
            "results_count": len(articles),
            "articles": articles,
            "timestamp": datetime.now().isoformat(),
        }
    
    except Exception as e:
        LOGGER.error(f"News fetch error: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def open_world_monitor() -> Dict[str, Any]:
    """
    Open world news monitor (aggregates multiple news sources).
    
    Returns:
        Aggregated world news
    """
    try:
        categories = ["general", "business", "technology", "health", "science"]
        all_articles = []
        
        for category in categories:
            result = get_world_news(category, max_results=3)
            if result.get("success"):
                all_articles.extend(result.get("articles", []))
        
        return {
            "success": True,
            "total_articles": len(all_articles),
            "categories_covered": categories,
            "articles": all_articles,
            "timestamp": datetime.now().isoformat(),
        }
    
    except Exception as e:
        LOGGER.error(f"World monitor error: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Tool Registration
# ─────────────────────────────────────────────────────────────────────────────

def register_web_tools(registry) -> None:
    """Register all web tools with MCP server."""
    from mcp_server import MCPTool, ToolType
    
    # Web Search Tool
    registry.register_tool(MCPTool(
        name="web_search",
        description="Search the internet for information",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (1-10)",
                    "default": 5
                }
            },
            "required": ["query"]
        },
        tool_type=ToolType.WEB_SEARCH,
    ))
    
    # URL Fetch Tool
    registry.register_tool(MCPTool(
        name="fetch_url",
        description="Fetch and read content from a URL",
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to fetch"
                },
                "max_length": {
                    "type": "integer",
                    "description": "Maximum content length in characters",
                    "default": 5000
                }
            },
            "required": ["url"]
        },
        tool_type=ToolType.FETCH_URL,
    ))
    
    # World News Tool
    registry.register_tool(MCPTool(
        name="get_world_news",
        description="Get latest world news by category",
        parameters={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "News category (general, business, tech, health, science, sports)",
                    "default": "general"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of articles",
                    "default": 5
                }
            },
        },
        tool_type=ToolType.GET_NEWS,
        requires_api_key="NEWS_API_KEY",
    ))
    
    # World Monitor Tool
    registry.register_tool(MCPTool(
        name="open_world_monitor",
        description="Open world news monitor aggregating multiple sources",
        parameters={
            "type": "object",
            "properties": {},
        },
        tool_type=ToolType.GET_NEWS,
        requires_api_key="NEWS_API_KEY",
    ))


__all__ = [
    "web_search",
    "fetch_url",
    "get_world_news",
    "open_world_monitor",
    "register_web_tools",
]
