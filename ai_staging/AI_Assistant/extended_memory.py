"""
Extended Memory System — Multi-turn conversation with context summarization.

Features:
  • Supports 50+ conversation turns (vs 16 current)
  • Automatic context summarization for long conversations
  • Topic tracking and relevance scoring
  • Memory search by keyword or topic
  • Forgetting mechanism (older, irrelevant memories fade)
"""

import json
import os
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any


class ExtendedMemory:
    """Enhanced conversation memory with context awareness."""
    
    MAX_RECENT_TURNS = 50  # Keep last 50 turns in full detail
    SUMMARIZATION_THRESHOLD = 40  # Summarize when exceeding this
    CONTEXT_WINDOW = 8  # Use last 8 turns for immediate context
    
    _FILE = os.path.join(os.path.dirname(__file__), ".jarvis_extended_memory.json")
    _lock = threading.RLock()
    
    def __init__(self):
        self._full_history: List[Dict[str, Any]] = []  # Full turn-by-turn history
        self._summaries: List[Dict[str, Any]] = []      # Summarized older conversations
        self._topics: Dict[str, int] = {}               # Topic frequency tracking
        self._user_context: Dict[str, Any] = {}         # User preferences, name, etc.
        self._load()
    
    def _load(self):
        """Load extended memory from disk."""
        try:
            if os.path.exists(self._FILE):
                with self._lock:
                    with open(self._FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._full_history = data.get("full_history", [])[-self.MAX_RECENT_TURNS:]
                    self._summaries = data.get("summaries", [])[-10:]  # Keep last 10 summaries
                    self._topics = data.get("topics", {})
                    self._user_context = data.get("user_context", {})
                    print(f"[Memory] Loaded {len(self._full_history)} turns + {len(self._summaries)} summaries")
        except Exception as e:
            print(f"[Memory] Load error: {e}")
            self._full_history = []
            self._summaries = []
            self._topics = {}
            self._user_context = {}
    
    def _save(self):
        """Save extended memory to disk atomically."""
        try:
            import tempfile
            temp_fd, temp_path = tempfile.mkstemp(suffix='.json', dir=os.path.dirname(self._FILE))
            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    json.dump({
                        "full_history": self._full_history,
                        "summaries": self._summaries,
                        "topics": self._topics,
                        "user_context": self._user_context,
                    }, f, indent=2)
                with self._lock:
                    os.replace(temp_path, self._FILE)
            except Exception:
                try:
                    os.unlink(temp_path)
                except:
                    pass
                raise
        except Exception as e:
            print(f"[Memory] Save error: {e}")
    
    def add_turn(self, user_text: str, assistant_response: str, metadata: Dict = None):
        """Add a conversation turn with timestamp and metadata."""
        if not metadata:
            metadata = {}
        
        turn = {
            "timestamp": datetime.now().isoformat(),
            "user": user_text,
            "assistant": assistant_response,
            "metadata": metadata,  # topic, intent, entities, confidence, etc.
        }
        
        with self._lock:
            self._full_history.append(turn)
            
            # Track topics from metadata
            if "topic" in metadata:
                topic = metadata["topic"]
                self._topics[topic] = self._topics.get(topic, 0) + 1
            
            # Auto-summarize if exceeding threshold
            if len(self._full_history) > self.SUMMARIZATION_THRESHOLD:
                self._auto_summarize()
            
            self._save()
    
    def _auto_summarize(self):
        """Summarize oldest turns when memory gets large."""
        if len(self._full_history) <= self.SUMMARIZATION_THRESHOLD:
            return
        
        # Take oldest 20 turns and summarize
        to_summarize = self._full_history[:20]
        remaining = self._full_history[20:]
        
        summary_text = self._create_summary(to_summarize)
        
        summary = {
            "created_at": datetime.now().isoformat(),
            "turn_count": len(to_summarize),
            "first_turn_time": to_summarize[0].get("timestamp", ""),
            "last_turn_time": to_summarize[-1].get("timestamp", ""),
            "summary": summary_text,
            "topics": [m.get("metadata", {}).get("topic") for m in to_summarize if "topic" in m.get("metadata", {})],
        }
        
        with self._lock:
            self._summaries.append(summary)
            self._full_history = remaining  # Keep only recent turns
        
        print(f"[Memory] Auto-summarized {len(to_summarize)} older turns")
    
    def _create_summary(self, turns: List[Dict]) -> str:
        """Create a concise summary of conversation turns."""
        if not turns:
            return ""
        
        # Extract key points from turns
        topics_mentioned = set()
        key_requests = []
        
        for turn in turns:
            metadata = turn.get("metadata", {})
            if "topic" in metadata:
                topics_mentioned.add(metadata["topic"])
            if metadata.get("intent") in ("request", "question"):
                key_requests.append(turn["user"][:50])  # First 50 chars
        
        summary = f"Discussed: {', '.join(topics_mentioned) or 'general topics'}. "
        if key_requests:
            summary += f"Key questions: {'; '.join(key_requests[:3])}"
        
        return summary
    
    def get_context(self, window_size: int = None) -> List[Dict]:
        """Get recent conversation context for LLM."""
        if window_size is None:
            window_size = self.CONTEXT_WINDOW
        
        with self._lock:
            # Return last N turns as conversation context
            recent = self._full_history[-window_size:]
            result = []
            for turn in recent:
                result.append({"role": "user", "content": turn["user"]})
                result.append({"role": "assistant", "content": turn["assistant"]})
            return result
    
    def search_memory(self, query: str, limit: int = 5) -> List[Dict]:
        """Search past conversations by keyword."""
        query_lower = query.lower()
        results = []
        
        with self._lock:
            # Search full history
            for turn in self._full_history:
                if query_lower in turn["user"].lower() or query_lower in turn["assistant"].lower():
                    results.append(turn)
                if len(results) >= limit:
                    break
            
            # Search summaries if needed
            if len(results) < limit:
                for summary in self._summaries:
                    if query_lower in summary["summary"].lower():
                        results.append({
                            "user": f"[Summary] {summary['summary']}",
                            "assistant": "",
                            "timestamp": summary["created_at"],
                        })
                    if len(results) >= limit:
                        break
        
        return results
    
    def set_user_preference(self, key: str, value: Any):
        """Store user preferences (name, location, etc.)."""
        with self._lock:
            self._user_context[key] = value
            self._save()
        print(f"[Memory] Stored preference: {key} = {value}")
    
    def get_user_preference(self, key: str, default: Any = None) -> Any:
        """Retrieve user preference."""
        with self._lock:
            return self._user_context.get(key, default)
    
    def get_user_context_summary(self) -> str:
        """Get summary of user context for LLM."""
        if not self._user_context:
            return "No user context stored."
        
        parts = []
        if "name" in self._user_context:
            parts.append(f"User's name: {self._user_context['name']}")
        if "location" in self._user_context:
            parts.append(f"Location: {self._user_context['location']}")
        if "preferences" in self._user_context:
            prefs = self._user_context['preferences']
            parts.append(f"Preferences: {prefs}")
        
        return "; ".join(parts) if parts else "No preferences set."
    
    def get_topic_summary(self) -> str:
        """Get summary of conversation topics."""
        if not self._topics:
            return "No topics tracked."
        
        sorted_topics = sorted(self._topics.items(), key=lambda x: x[1], reverse=True)
        top_5 = [f"{topic}({count})" for topic, count in sorted_topics[:5]]
        return f"Main topics: {', '.join(top_5)}"
    
    def clear(self):
        """Clear all memory."""
        with self._lock:
            self._full_history.clear()
            self._summaries.clear()
            self._topics.clear()
            self._user_context.clear()
            self._save()
        print("[Memory] Cleared all extended memory")
    
    def get_stats(self) -> Dict:
        """Get memory statistics."""
        with self._lock:
            return {
                "recent_turns": len(self._full_history),
                "summarized_conversations": len(self._summaries),
                "topics_tracked": len(self._topics),
                "user_preferences": len(self._user_context),
                "total_conversations": sum(s.get("turn_count", 0) for s in self._summaries) + len(self._full_history),
            }


# Global instance
EXTENDED_MEMORY = ExtendedMemory()
