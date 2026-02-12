import logging
import uuid
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import json

logger = logging.getLogger(__name__)

@dataclass
class Ticket:
    """Represents a support ticket"""
    ticket_id: str
    description: str
    priority: str  # 'low', 'medium', 'high'
    category: str  # 'technical', 'billing', 'general', 'other'
    status: str = 'open'
    created_at: float = None
    updated_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.updated_at is None:
            self.updated_at = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Ticket':
        return cls(**data)

class TicketManager:
    """Manages support tickets"""
    
    def __init__(self, storage_path: Optional[Path] = None):
        if storage_path is None:
            storage_path = Path("data/tickets.json")
        self.storage_path = storage_path
        self.tickets: Dict[str, Ticket] = {}
        self._load_tickets()
    
    def _load_tickets(self) -> None:
        """Load tickets from storage"""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tickets = {
                        ticket_id: Ticket.from_dict(ticket_data)
                        for ticket_id, ticket_data in data.items()
                    }
                logger.info(f"Loaded {len(self.tickets)} tickets")
        except Exception as e:
            logger.error(f"Error loading tickets: {e}")
            self.tickets = {}
    
    def _save_tickets(self) -> None:
        """Save tickets to storage"""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                data = {
                    ticket_id: ticket.to_dict()
                    for ticket_id, ticket in self.tickets.items()
                }
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving tickets: {e}")
    
    def create_ticket(self, description: str, priority: str = 'medium', 
                     category: str = 'general') -> Ticket:
        """Create a new support ticket"""
        ticket_id = f"TK-{uuid.uuid4().hex[:8].upper()}"
        
        # Validate priority
        if priority not in ['low', 'medium', 'high']:
            priority = 'medium'
        
        # Validate category
        if category not in ['technical', 'billing', 'general', 'other']:
            category = 'general'
        
        ticket = Ticket(
            ticket_id=ticket_id,
            description=description,
            priority=priority,
            category=category
        )
        
        self.tickets[ticket_id] = ticket
        self._save_tickets()
        
        logger.info(f"Created ticket {ticket_id} with priority {priority}")
        return ticket
    
    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        """Get a ticket by ID"""
        return self.tickets.get(ticket_id)
    
    def update_ticket_status(self, ticket_id: str, status: str) -> bool:
        """Update ticket status"""
        if ticket_id not in self.tickets:
            return False
        
        valid_statuses = ['open', 'in_progress', 'resolved', 'closed']
        if status not in valid_statuses:
            return False
        
        self.tickets[ticket_id].status = status
        self.tickets[ticket_id].updated_at = time.time()
        self._save_tickets()
        
        logger.info(f"Updated ticket {ticket_id} status to {status}")
        return True
    
    def get_tickets_by_status(self, status: str) -> list[Ticket]:
        """Get tickets by status"""
        return [ticket for ticket in self.tickets.values() if ticket.status == status]
    
    def get_tickets_by_priority(self, priority: str) -> list[Ticket]:
        """Get tickets by priority"""
        return [ticket for ticket in self.tickets.values() if ticket.priority == priority]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get ticket statistics"""
        total = len(self.tickets)
        if total == 0:
            return {
                'total_tickets': 0,
                'by_status': {},
                'by_priority': {},
                'by_category': {}
            }
        
        by_status = {}
        by_priority = {}
        by_category = {}
        
        for ticket in self.tickets.values():
            # Count by status
            by_status[ticket.status] = by_status.get(ticket.status, 0) + 1
            # Count by priority
            by_priority[ticket.priority] = by_priority.get(ticket.priority, 0) + 1
            # Count by category
            by_category[ticket.category] = by_category.get(ticket.category, 0) + 1
        
        return {
            'total_tickets': total,
            'by_status': by_status,
            'by_priority': by_priority,
            'by_category': by_category
        }

# Global ticket manager instance
ticket_manager = TicketManager()