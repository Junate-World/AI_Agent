import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from config import SESSION_TIMEOUT, MAX_SESSION_MESSAGES

logger = logging.getLogger(__name__)

@dataclass
class Message:
    """Represents a chat message"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        return cls(**data)

@dataclass
class Session:
    """Represents a user session"""
    session_id: str
    messages: List[Message]
    created_at: float
    last_activity: float
    
    def __post_init__(self):
        if not self.messages:
            self.messages = []
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the session"""
        message = Message(
            role=role,
            content=content,
            timestamp=time.time()
        )
        self.messages.append(message)
        self.last_activity = time.time()
        
        # Trim messages if exceeding limit
        if len(self.messages) > MAX_SESSION_MESSAGES:
            # Keep the first message (usually welcome) and last MAX_SESSION_MESSAGES-1
            self.messages = [self.messages[0]] + self.messages[-(MAX_SESSION_MESSAGES-1):]
    
    def get_recent_messages(self, limit: int = 10) -> List[Message]:
        """Get recent messages from the session"""
        return self.messages[-limit:] if self.messages else []
    
    def is_expired(self) -> bool:
        """Check if session has expired"""
        return time.time() - self.last_activity > SESSION_TIMEOUT
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'session_id': self.session_id,
            'messages': [msg.to_dict() for msg in self.messages],
            'created_at': self.created_at,
            'last_activity': self.last_activity
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        messages = [Message.from_dict(msg) for msg in data['messages']]
        return cls(
            session_id=data['session_id'],
            messages=messages,
            created_at=data['created_at'],
            last_activity=data['last_activity']
        )

class SessionManager:
    """Manages user sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID"""
        session = self.sessions.get(session_id)
        if session and session.is_expired():
            self.remove_session(session_id)
            return None
        return session
    
    def create_session(self, session_id: str) -> Session:
        """Create a new session"""
        now = time.time()
        session = Session(
            session_id=session_id,
            messages=[],
            created_at=now,
            last_activity=now
        )
        self.sessions[session_id] = session
        logger.info(f"Created new session: {session_id}")
        return session
    
    def get_or_create_session(self, session_id: str) -> Session:
        """Get existing session or create new one"""
        session = self.get_session(session_id)
        if not session:
            session = self.create_session(session_id)
        return session
    
    def remove_session(self, session_id: str) -> None:
        """Remove a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Removed session: {session_id}")
    
    def cleanup_expired_sessions(self) -> None:
        """Remove all expired sessions"""
        expired_sessions = [
            sid for sid, session in self.sessions.items()
            if session.is_expired()
        ]
        
        for sid in expired_sessions:
            self.remove_session(sid)
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    def get_session_count(self) -> int:
        """Get the number of active sessions"""
        return len(self.sessions)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about sessions"""
        total_messages = sum(len(session.messages) for session in self.sessions.values())
        return {
            'active_sessions': len(self.sessions),
            'total_messages': total_messages,
            'avg_messages_per_session': total_messages / len(self.sessions) if self.sessions else 0
        }

# Global session manager instance
session_manager = SessionManager()