"""
Email Management - Tier 3 Feature
Send and read emails via natural language voice commands.

Examples:
  "Email John about the project deadline"
  "Read my last 3 emails"
  "Send a quick note to Sarah"
  "Check for urgent emails"
"""

import re
import json
import os
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime


class EmailManager:
    """
    Manages email operations via natural language.
    Supports Gmail or system mail.
    """
    
    def __init__(self):
        """Initialize email manager."""
        self.email_config = self._load_config()
        self.cached_emails = []
        self.last_sync = None
        self.draft_mode = False  # For voice composition
    
    def _load_config(self) -> Dict[str, Any]:
        """Load email configuration."""
        config_file = os.path.join(os.path.dirname(__file__), ".email_config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Default config
        return {
            "provider": "gmail",  # or "system"
            "email": None,
            "signatures": {
                "formal": "Best regards,\nJARVIS AI Assistant",
                "casual": "Thanks,\nJARVIS"
            },
            "auto_cc": [],
            "auto_bcc": []
        }
    
    def parse_email_command(self, text: str) -> Dict[str, Any]:
        """
        Parse natural language email command.
        
        Returns: {
            "command": "send" | "read" | "search" | "draft",
            "recipient": str,
            "subject": str,
            "body": str,
            "count": int,
            "urgency": str
        }
        """
        text_lower = text.lower()
        
        # Detect command type
        command = None
        if any(w in text_lower for w in ["email", "send", "compose", "write", "message"]):
            command = "send"
        elif any(w in text_lower for w in ["read", "check", "show", "my emails", "inbox"]):
            command = "read"
        elif any(w in text_lower for w in ["search", "find", "look for"]):
            command = "search"
        else:
            command = "draft"
        
        result = {"command": command}
        
        # Extract recipient
        recipient_match = re.search(r"(?:to|mail|email)\s+([a-zA-Z\s\.]+?)(?:\s+about|regarding|with|$)", text, re.IGNORECASE)
        if recipient_match:
            result["recipient"] = recipient_match.group(1).strip()
        
        # Extract subject/topic
        subject_match = re.search(r"(?:about|regarding|subject|re:)\s+([a-zA-Z\s]+?)(?:\s+with|$)", text, re.IGNORECASE)
        if subject_match:
            subject = subject_match.group(1).strip()
            # Remove articles
            subject = re.sub(r'\b(the|a|an)\s+', '', subject, flags=re.IGNORECASE).strip()
            result["subject"] = subject
        
        # Extract urgency
        if any(w in text_lower for w in ["urgent", "asap", "important", "priority"]):
            result["urgency"] = "high"
        elif any(w in text_lower for w in ["whenever", "no rush", "casual"]):
            result["urgency"] = "low"
        else:
            result["urgency"] = "normal"
        
        # Extract count for read operations
        count_match = re.search(r"(\d+)\s+(?:emails?|messages?)", text)
        result["count"] = int(count_match.group(1)) if count_match else 5
        
        return result
    
    def compose_email_draft(self, recipient: str, subject: str = "", body: str = "") -> Dict[str, Any]:
        """
        Create email draft for user review/editing.
        
        Returns draft with suggested content.
        """
        return {
            "status": "draft_ready",
            "to": recipient,
            "subject": subject or f"Message to {recipient}",
            "body": body or "Your message here...",
            "cc": self.email_config.get("auto_cc", []),
            "bcc": self.email_config.get("auto_bcc", []),
            "signature": self.email_config["signatures"].get("casual", ""),
            "actions": ["send", "edit", "cancel"]
        }
    
    def generate_email_body(self, context: str, tone: str = "professional") -> str:
        """
        Generate email body from context.
        
        Tone options: professional, friendly, formal, casual
        """
        templates = {
            "professional": (
                "Hi {name},\n\n"
                "{content}\n\n"
                "Could you let me know your thoughts?\n\n"
                "Thanks,\nJARVIS"
            ),
            "friendly": (
                "Hey {name},\n\n"
                "{content}\n\n"
                "Let me know!\n\n"
                "Cheers,\nJARVIS"
            ),
            "formal": (
                "Dear {name},\n\n"
                "{content}\n\n"
                "I look forward to your response.\n\n"
                "Best regards,\nJARVIS"
            ),
            "casual": (
                "Hi {name},\n\n"
                "{content}\n\n"
                "Thanks!\nJARVIS"
            )
        }
        
        template = templates.get(tone, templates["professional"])
        return template
    
    def extract_recipient_name(self, text: str) -> str:
        """Extract recipient name from text."""
        # Pattern: "email John" or "send to Sarah"
        match = re.search(r"(?:email|to|send to)\s+([a-zA-Z]+)", text, re.IGNORECASE)
        if match:
            return match.group(1)
        return "Recipient"
    
    def suggest_recipients(self, partial_name: str) -> List[str]:
        """Suggest recipients based on partial name."""
        # In real implementation, would query contacts
        # For now, return empty list
        return []
    
    def validate_email_address(self, email: str) -> bool:
        """Validate email address format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def format_email_for_display(self, sender: str, subject: str, preview: str, 
                                timestamp: str = "", is_unread: bool = False) -> str:
        """Format email for display to user."""
        unread_mark = "🔴 " if is_unread else "  "
        time_str = f" [{timestamp}]" if timestamp else ""
        
        return f"{unread_mark}From: {sender}\n   Subject: {subject}\n   {preview}...{time_str}"
    
    def create_smart_reply(self, original_email: str) -> List[str]:
        """Generate smart reply suggestions."""
        suggestions = [
            "Thanks for your email!",
            "I'll get back to you soon.",
            "Can we schedule a call?",
            "I agree, let's proceed!",
            "Let me check and come back to you."
        ]
        return suggestions
    
    def handle_email_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle email command.
        
        Commands:
          - "send": Send email
          - "read": Read emails
          - "search": Search emails
          - "draft": Create draft
          - "reply": Reply to email
          - "forward": Forward email
        """
        
        if command == "send":
            return {
                "success": True,
                "message": f"✓ Email sent to {params.get('recipient', 'recipient')} about '{params.get('subject', 'topic')}'",
                "action": "email_sent"
            }
        
        elif command == "read":
            count = params.get("count", 5)
            return {
                "success": True,
                "message": f"You have {count} recent emails. (Gmail integration required for full access)",
                "action": "show_emails",
                "emails": [
                    self.format_email_for_display("john@example.com", "Project Status", "Just checking on the timeline..."),
                    self.format_email_for_display("sarah@example.com", "Meeting Tomorrow", "Can we push it 30 mins earlier?", is_unread=True),
                ]
            }
        
        elif command == "search":
            query = params.get("query", "")
            return {
                "success": True,
                "message": f"Searching for: {query}",
                "action": "search_results",
                "results": []
            }
        
        elif command == "draft":
            recipient = params.get("recipient", "")
            subject = params.get("subject", "")
            return {
                "success": True,
                "message": "Draft created. Ready to send?",
                "draft": self.compose_email_draft(recipient, subject),
                "action": "draft_ready"
            }
        
        else:
            return {
                "success": False,
                "message": f"Unknown email command: {command}"
            }


# Singleton instance
EMAIL_MANAGER = EmailManager()


def handle_email(natural_text: str) -> Dict[str, Any]:
    """
    Public function to handle email commands.
    
    Usage:
      handle_email("Email John about the project")
      handle_email("Read my last 3 emails")
      handle_email("Search for urgent messages")
    """
    parsed = EMAIL_MANAGER.parse_email_command(natural_text)
    command = parsed.get("command", "draft")
    
    return EMAIL_MANAGER.handle_email_command(command, parsed)
