"""
JARVIS Prompt Templates — LLM reasoning prompts

Provides structured prompts for:
  - Extended reasoning with tools
  - Information summarization
  - Code explanation
  - Question answering with context
"""

import logging

LOGGER = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Prompt Templates
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are JARVIS, an advanced AI assistant powered by Friday's capabilities.

You have access to the following tools:
- web_search: Search the internet
- fetch_url: Get content from URLs
- get_world_news: Get latest news
- get_system_info: System information
- get_current_time: Current time/date
- get_disk_usage: Storage information
- list_running_processes: Running processes
- get_environment_stats: System environment

When you need information, use the appropriate tool. Format tool calls as:
```json
{
  "tool_call": {
    "tool_name": "tool_name",
    "parameters": {...},
    "call_id": "call_123"
  }
}
```

Always provide helpful, accurate, and concise responses.
"""

EXTENDED_REASONING_PROMPT = """You are helping with a complex query that may require:
1. Searching for current information
2. Analyzing multiple sources
3. Synthesizing information
4. Providing context-aware answers

Query: {user_query}

Tools available:
- web_search: For finding current information
- fetch_url: For reading detailed content
- get_world_news: For latest news
- get_system_info: For system details

Process:
1. Identify what information is needed
2. Use appropriate tools to gather data
3. Analyze and synthesize results
4. Provide comprehensive answer with sources

Begin your response:
"""

SUMMARIZATION_PROMPT = """Please summarize the following content concisely:

Content:
{content}

Key points to include:
- Main ideas
- Important details
- Actionable insights

Format:
- Brief summary (2-3 sentences)
- Key points (bullet list)
- Implications (if applicable)

Summary:
"""

CODE_EXPLANATION_PROMPT = """Explain the following code in detail:

Code:
```{language}
{code}
```

Explain:
1. What the code does
2. Key functions/classes
3. How it works step-by-step
4. Important concepts
5. Potential improvements

Explanation:
"""

QUESTION_ANSWERING_PROMPT = """Answer the following question using available context and tools if needed.

Question: {question}

Context (if available):
{context}

Tools you can use:
- web_search: Search the web for information
- fetch_url: Get detailed information from URLs
- get_world_news: Get latest news
- get_system_info: Get system information
- get_current_time: Get current time/date

Process:
1. If context is sufficient, answer directly
2. If you need current information, use web_search
3. For specific details, use fetch_url
4. Provide accurate, sourced answers

Answer:
"""

REASONING_PROMPT = """You are helping to reason through a complex problem.

Problem: {problem}

Approach:
1. Break down the problem into parts
2. Use available tools to gather information
3. Analyze each component
4. Synthesize into a solution
5. Verify your reasoning

Use tools as needed:
- web_search: Find relevant information
- fetch_url: Get detailed sources
- get_system_info: System details
- get_current_time: For time-sensitive information

Reasoning:
"""

GENERAL_RESPONSE_PROMPT = """Respond to the user query helpfully and accurately.

User: {user_message}

Available tools:
- web_search: Search the internet
- fetch_url: Read URL content
- get_world_news: Latest news
- get_system_info: System information
- get_current_time: Current time/date

If you need external information, use the tools.
Format tool calls as JSON (see system prompt).

Response:
"""

# ─────────────────────────────────────────────────────────────────────────────
# Prompt Registry
# ─────────────────────────────────────────────────────────────────────────────

class PromptRegistry:
    """Registry of available prompts."""
    
    def __init__(self):
        """Initialize prompt registry."""
        self.prompts = {
            "system": SYSTEM_PROMPT,
            "extended_reasoning": EXTENDED_REASONING_PROMPT,
            "summarization": SUMMARIZATION_PROMPT,
            "code_explanation": CODE_EXPLANATION_PROMPT,
            "question_answering": QUESTION_ANSWERING_PROMPT,
            "reasoning": REASONING_PROMPT,
            "general_response": GENERAL_RESPONSE_PROMPT,
        }
    
    def get_prompt(self, name: str, **kwargs) -> str:
        """Get a prompt template and format with variables."""
        if name not in self.prompts:
            LOGGER.warning(f"Prompt '{name}' not found")
            return None
        
        template = self.prompts[name]
        try:
            return template.format(**kwargs) if kwargs else template
        except KeyError as e:
            LOGGER.error(f"Missing variable in prompt: {e}")
            return template
    
    def get_system_prompt(self) -> str:
        """Get the system prompt."""
        return self.prompts["system"]
    
    def list_prompts(self) -> list:
        """List all available prompts."""
        return list(self.prompts.keys())
    
    def register_prompt(self, name: str, template: str) -> None:
        """Register a new prompt template."""
        self.prompts[name] = template
        LOGGER.info(f"Registered prompt: {name}")


# ─────────────────────────────────────────────────────────────────────────────
# Global Registry
# ─────────────────────────────────────────────────────────────────────────────

_global_prompt_registry: PromptRegistry = PromptRegistry()


def get_prompt(name: str, **kwargs) -> str:
    """Get a prompt from the global registry."""
    return _global_prompt_registry.get_prompt(name, **kwargs)


def get_system_prompt() -> str:
    """Get the system prompt."""
    return _global_prompt_registry.get_system_prompt()


def list_prompts() -> list:
    """List all available prompts."""
    return _global_prompt_registry.list_prompts()


def register_prompt(name: str, template: str) -> None:
    """Register a new prompt."""
    _global_prompt_registry.register_prompt(name, template)


def get_extended_reasoning_prompt(user_query: str) -> str:
    """Get extended reasoning prompt."""
    return get_prompt("extended_reasoning", user_query=user_query)


def get_question_answering_prompt(question: str, context: str = "") -> str:
    """Get question answering prompt."""
    return get_prompt("question_answering", question=question, context=context)


def get_reasoning_prompt(problem: str) -> str:
    """Get reasoning prompt."""
    return get_prompt("reasoning", problem=problem)


def get_summarization_prompt(content: str) -> str:
    """Get summarization prompt."""
    return get_prompt("summarization", content=content)


def get_code_explanation_prompt(code: str, language: str = "python") -> str:
    """Get code explanation prompt."""
    return get_prompt("code_explanation", code=code, language=language)


def get_general_response_prompt(user_message: str) -> str:
    """Get general response prompt."""
    return get_prompt("general_response", user_message=user_message)


__all__ = [
    "PromptRegistry",
    "SYSTEM_PROMPT",
    "EXTENDED_REASONING_PROMPT",
    "SUMMARIZATION_PROMPT",
    "CODE_EXPLANATION_PROMPT",
    "QUESTION_ANSWERING_PROMPT",
    "REASONING_PROMPT",
    "GENERAL_RESPONSE_PROMPT",
    "get_prompt",
    "get_system_prompt",
    "list_prompts",
    "register_prompt",
    "get_extended_reasoning_prompt",
    "get_question_answering_prompt",
    "get_reasoning_prompt",
    "get_summarization_prompt",
    "get_code_explanation_prompt",
    "get_general_response_prompt",
]
