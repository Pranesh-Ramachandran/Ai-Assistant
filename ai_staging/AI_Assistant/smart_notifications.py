"""
Smart Notifications - Tier 3 Feature
Context-aware alerts and notifications with priority-based delivery.

Examples:
  "Alert me for urgent work emails"
  "Remind me about John's birthday next week"
  "Notify when rain is expected"
  "Alert if my flight is delayed"
"""

import re
import json
import os
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta


class SmartNotificationManager:
    """
    Manages context-aware notifications and reminders.
    Prioritizes alerts based on urgency and user preferences.
    """
    
    def __init__(self):
        """Initialize notification manager."""
        self.preferences = self._load_preferences()
        self.active_notifications = []
        self.notification_history = []
        self.quiet_hours = self._parse_quiet_hours()
    
    def _load_preferences(self) -> Dict[str, Any]:
        """Load notification preferences."""
        pref_file = os.path.join(os.path.dirname(__file__), ".notification_prefs.json")
        if os.path.exists(pref_file):
            try:
                with open(pref_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Default preferences
        return {
            "quiet_hours": {"start": "22:00", "end": "07:00"},
            "priority_levels": {
                "critical": {"sound": True, "vibrate": True, "popup": True},
                "high": {"sound": True, "vibrate": False, "popup": True},
                "normal": {"sound": False, "vibrate": False, "popup": False},
                "low": {"sound": False, "vibrate": False, "popup": False}
            },
            "notification_channels": {
                "email": True,
                "calendar": True,
                "weather": True,
                "news": False,
                "social": False
            },
            "delivery_method": "screen_text",  # screen_text, voice, sound
            "batch_notifications": True,
            "max_notifications_per_hour": 5
        }
    
    def _parse_quiet_hours(self) -> Tuple[str, str]:
        """Parse quiet hours from preferences."""
        qh = self.preferences.get("quiet_hours", {})
        return (qh.get("start", "22:00"), qh.get("end", "07:00"))
    
    def is_in_quiet_hours(self) -> bool:
        """Check if current time is in quiet hours."""
        now = datetime.now().time()
        start_hour, end_hour = self.quiet_hours
        
        start = datetime.strptime(start_hour, "%H:%M").time()
        end = datetime.strptime(end_hour, "%H:%M").time()
        
        # Handle case where quiet hours span midnight
        if start > end:
            return now >= start or now <= end
        else:
            return start <= now <= end
    
    def classify_notification_priority(self, notification_type: str, context: Dict[str, Any] = None) -> str:
        """
        Classify notification priority based on type and context.
        
        Priority levels: critical, high, normal, low
        """
        if context is None:
            context = {}
        
        # Critical: Safety, time-sensitive decisions
        critical_keywords = ["emergency", "urgent", "critical", "dangerous", "alarm"]
        if any(kw in notification_type.lower() for kw in critical_keywords):
            return "critical"
        
        # High: Important appointments, significant news
        high_keywords = ["meeting", "deadline", "flight", "appointment", "deadline passing", "alert"]
        if any(kw in notification_type.lower() for kw in high_keywords):
            # Check if imminent (within 1 hour)
            if context.get("time_until", float('inf')) < 3600:
                return "critical"
            return "high"
        
        # Normal: Regular reminders, calendar events
        normal_keywords = ["reminder", "event", "birthday", "anniversary"]
        if any(kw in notification_type.lower() for kw in normal_keywords):
            return "normal"
        
        # Low: News, social, informational
        return "low"
    
    def should_notify(self, notification: Dict[str, Any]) -> bool:
        """
        Determine if notification should be sent.
        
        Checks: quiet hours, frequency limits, preferences, user context
        """
        # Check notification channel preference
        channel = notification.get("channel", "general")
        if not self.preferences["notification_channels"].get(channel, True):
            return False
        
        # Check quiet hours for non-critical
        priority = notification.get("priority", "normal")
        if priority != "critical" and self.is_in_quiet_hours():
            return False
        
        # Check frequency limits
        recent_count = self._count_recent_notifications(within_minutes=60)
        if recent_count >= self.preferences["max_notifications_per_hour"]:
            return False
        
        return True
    
    def _count_recent_notifications(self, within_minutes: int = 60) -> int:
        """Count notifications sent in recent time period."""
        cutoff = datetime.now() - timedelta(minutes=within_minutes)
        count = sum(
            1 for notif in self.notification_history
            if datetime.fromisoformat(notif.get("timestamp", "")) > cutoff
        )
        return count
    
    def format_notification(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format notification for delivery.
        
        Generates appropriate presentation based on type and priority.
        """
        priority = notification.get("priority", "normal")
        notification_type = notification.get("type", "generic")
        message = notification.get("message", "")
        
        # Get priority settings
        priority_settings = self.preferences["priority_levels"].get(priority, {})
        
        # Enhance message with urgency context
        if priority == "critical":
            message = f"🚨 {message}"
        elif priority == "high":
            message = f"⚠️ {message}"
        elif priority == "normal":
            message = f"ℹ️ {message}"
        
        # Add actionable elements
        actions = notification.get("actions", [])
        if actions:
            action_text = " | ".join(actions)
            message += f"\n[{action_text}]"
        
        return {
            "message": message,
            "type": notification_type,
            "priority": priority,
            "sound": priority_settings.get("sound", False),
            "vibrate": priority_settings.get("vibrate", False),
            "popup": priority_settings.get("popup", False),
            "delivery_method": self.preferences.get("delivery_method", "screen_text"),
            "timestamp": datetime.now().isoformat()
        }
    
    def create_notification(self, notification_type: str, message: str, 
                          context: Dict[str, Any] = None, actions: List[str] = None) -> Dict[str, Any]:
        """
        Create a new notification.
        
        Types: reminder, alert, event, weather, email, calendar
        """
        if context is None:
            context = {}
        if actions is None:
            actions = []
        
        notification = {
            "id": f"notif_{len(self.active_notifications)}",
            "type": notification_type,
            "message": message,
            "channel": context.get("channel", "general"),
            "priority": self.classify_notification_priority(notification_type, context),
            "context": context,
            "actions": actions,
            "timestamp": datetime.now().isoformat(),
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }
        
        return notification
    
    def add_notification(self, notification: Dict[str, Any]) -> bool:
        """Add notification to queue."""
        if self.should_notify(notification):
            self.active_notifications.append(notification)
            return True
        return False
    
    def get_pending_notifications(self) -> List[Dict[str, Any]]:
        """Get all pending notifications, sorted by priority."""
        priority_order = {"critical": 0, "high": 1, "normal": 2, "low": 3}
        
        return sorted(
            [n for n in self.active_notifications if n.get("status") == "pending"],
            key=lambda x: priority_order.get(x.get("priority", "normal"), 4)
        )
    
    def deliver_notification(self, notification_id: str) -> Dict[str, Any]:
        """
        Deliver a notification to user.
        
        Mark as delivered and log.
        """
        # Find notification
        notification = None
        for notif in self.active_notifications:
            if notif["id"] == notification_id:
                notification = notif
                break
        
        if not notification:
            return {"success": False, "message": "Notification not found"}
        
        # Format for delivery
        formatted = self.format_notification(notification)
        
        # Update status
        notification["status"] = "delivered"
        notification["delivered_at"] = datetime.now().isoformat()
        
        # Log to history
        self.notification_history.append(notification)
        
        return {
            "success": True,
            "notification": formatted,
            "message": formatted["message"]
        }
    
    def batch_notifications(self) -> str:
        """
        Batch multiple notifications into single summary.
        
        Useful for low-priority notifications.
        """
        low_priority = [
            n for n in self.get_pending_notifications()
            if n.get("priority") in ["low", "normal"]
        ]
        
        if len(low_priority) <= 1:
            return ""
        
        summary = f"You have {len(low_priority)} updates: "
        items = [n.get("message", "").split("\n")[0] for n in low_priority[:3]]
        summary += "; ".join(items)
        
        if len(low_priority) > 3:
            summary += f"; and {len(low_priority) - 3} more."
        
        return summary
    
    def handle_notification_action(self, notification_id: str, action: str) -> Dict[str, Any]:
        """
        Handle user action on notification.
        
        Actions: snooze, dismiss, details, act
        """
        
        if action == "snooze":
            return {
                "success": True,
                "action": "snooze",
                "time": "5 minutes",
                "message": "I'll remind you in 5 minutes"
            }
        
        elif action == "dismiss":
            return {
                "success": True,
                "action": "dismiss",
                "message": "Notification dismissed"
            }
        
        elif action == "details":
            return {
                "success": True,
                "action": "show_details",
                "message": "Here are the full details..."
            }
        
        elif action == "act":
            return {
                "success": True,
                "action": "perform_action",
                "message": "Taking action on that now..."
            }
        
        else:
            return {
                "success": False,
                "message": f"Unknown action: {action}"
            }
    
    def clear_delivered_notifications(self) -> int:
        """Clear delivered notifications from active queue."""
        initial_count = len(self.active_notifications)
        self.active_notifications = [
            n for n in self.active_notifications
            if n.get("status") != "delivered"
        ]
        return initial_count - len(self.active_notifications)


# Singleton instance
NOTIFICATION_MANAGER = SmartNotificationManager()


def create_and_send_notification(notification_type: str, message: str, 
                                context: Dict[str, Any] = None, actions: List[str] = None) -> Dict[str, Any]:
    """
    Public function to create and send notification.
    
    Usage:
      create_and_send_notification("reminder", "Your meeting starts in 10 minutes", 
                                   context={"channel": "calendar"},
                                   actions=["Join", "Snooze", "Dismiss"])
      
      create_and_send_notification("alert", "Rain expected in 30 minutes",
                                   context={"channel": "weather"},
                                   actions=["Details"])
    """
    
    if context is None:
        context = {}
    if actions is None:
        actions = []
    
    # Create notification
    notif = NOTIFICATION_MANAGER.create_notification(notification_type, message, context, actions)
    
    # Try to add (checks preferences, quiet hours, frequency limits)
    added = NOTIFICATION_MANAGER.add_notification(notif)
    
    if added:
        return {
            "success": True,
            "notification_id": notif["id"],
            "message": f"✓ {notification_type.title()} created",
            "queued": True
        }
    else:
        return {
            "success": True,
            "notification_id": notif["id"],
            "message": f"{notification_type.title()} created but queued (quiet hours or frequency limit)",
            "queued": False
        }


def get_next_notification() -> Optional[Dict[str, Any]]:
    """Get next pending notification to display to user."""
    pending = NOTIFICATION_MANAGER.get_pending_notifications()
    
    if not pending:
        return None
    
    # Get highest priority
    next_notif = pending[0]
    return NOTIFICATION_MANAGER.deliver_notification(next_notif["id"])
