import logging
import uuid
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import json
from enum import Enum

logger = logging.getLogger(__name__)

class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

@dataclass
class Order:
    """Represents a customer order"""
    order_id: str
    customer_name: str
    customer_email: str
    items: list[Dict[str, Any]]
    total_amount: float
    status: str
    created_at: float = None
    updated_at: float = None
    tracking_number: Optional[str] = None
    estimated_delivery: Optional[float] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.updated_at is None:
            self.updated_at = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Order':
        return cls(**data)

class OrderManager:
    """Manages customer orders"""
    
    def __init__(self, storage_path: Optional[Path] = None):
        if storage_path is None:
            storage_path = Path("data/orders.json")
        self.storage_path = storage_path
        self.orders: Dict[str, Order] = {}
        self._load_orders()
        self._create_sample_orders()
    
    def _load_orders(self) -> None:
        """Load orders from storage"""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.orders = {
                        order_id: Order.from_dict(order_data)
                        for order_id, order_data in data.items()
                    }
                logger.info(f"Loaded {len(self.orders)} orders")
        except Exception as e:
            logger.error(f"Error loading orders: {e}")
            self.orders = {}
    
    def _save_orders(self) -> None:
        """Save orders to storage"""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                data = {
                    order_id: order.to_dict()
                    for order_id, order in self.orders.items()
                }
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving orders: {e}")
    
    def _create_sample_orders(self) -> None:
        """Create some sample orders for testing"""
        if len(self.orders) > 0:
            return  # Don't create samples if orders already exist
        
        sample_orders = [
            {
                "order_id": "ORD-001",
                "customer_name": "John Doe",
                "customer_email": "john@example.com",
                "items": [
                    {"name": "Wireless Headphones", "quantity": 1, "price": 79.99},
                    {"name": "Phone Case", "quantity": 2, "price": 15.99}
                ],
                "total_amount": 111.97,
                "status": OrderStatus.DELIVERED.value,
                "tracking_number": "TRK123456789",
                "estimated_delivery": time.time() - 86400  # Delivered yesterday
            },
            {
                "order_id": "ORD-002",
                "customer_name": "Jane Smith",
                "customer_email": "jane@example.com",
                "items": [
                    {"name": "Laptop Stand", "quantity": 1, "price": 49.99}
                ],
                "total_amount": 49.99,
                "status": OrderStatus.SHIPPED.value,
                "tracking_number": "TRK987654321",
                "estimated_delivery": time.time() + 172800  # 2 days from now
            },
            {
                "order_id": "ORD-003",
                "customer_name": "Bob Johnson",
                "customer_email": "bob@example.com",
                "items": [
                    {"name": "USB-C Cable", "quantity": 3, "price": 12.99},
                    {"name": "Mouse Pad", "quantity": 1, "price": 19.99}
                ],
                "total_amount": 58.96,
                "status": OrderStatus.PROCESSING.value,
                "tracking_number": None,
                "estimated_delivery": time.time() + 432000  # 5 days from now
            }
        ]
        
        for order_data in sample_orders:
            order = Order(**order_data)
            self.orders[order.order_id] = order
        
        self._save_orders()
        logger.info(f"Created {len(sample_orders)} sample orders")
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get an order by ID"""
        return self.orders.get(order_id.upper())
    
    def update_order_status(self, order_id: str, status: str, 
                           tracking_number: Optional[str] = None,
                           estimated_delivery: Optional[float] = None) -> bool:
        """Update order status"""
        order_id = order_id.upper()
        if order_id not in self.orders:
            return False
        
        # Validate status
        valid_statuses = [s.value for s in OrderStatus]
        if status not in valid_statuses:
            return False
        
        self.orders[order_id].status = status
        self.orders[order_id].updated_at = time.time()
        
        if tracking_number:
            self.orders[order_id].tracking_number = tracking_number
        
        if estimated_delivery:
            self.orders[order_id].estimated_delivery = estimated_delivery
        
        self._save_orders()
        
        logger.info(f"Updated order {order_id} status to {status}")
        return True
    
    def get_orders_by_status(self, status: str) -> list[Order]:
        """Get orders by status"""
        return [order for order in self.orders.values() if order.status == status]
    
    def get_orders_by_customer(self, customer_email: str) -> list[Order]:
        """Get orders by customer email"""
        return [order for order in self.orders.values() 
                if order.customer_email.lower() == customer_email.lower()]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get order statistics"""
        total = len(self.orders)
        if total == 0:
            return {
                'total_orders': 0,
                'by_status': {},
                'total_revenue': 0.0,
                'average_order_value': 0.0
            }
        
        by_status = {}
        total_revenue = 0.0
        
        for order in self.orders.values():
            # Count by status
            by_status[order.status] = by_status.get(order.status, 0) + 1
            total_revenue += order.total_amount
        
        return {
            'total_orders': total,
            'by_status': by_status,
            'total_revenue': round(total_revenue, 2),
            'average_order_value': round(total_revenue / total, 2)
        }
    
    def format_order_status(self, order: Order) -> str:
        """Format order information for display"""
        status_emoji = {
            OrderStatus.PENDING.value: "⏳",
            OrderStatus.CONFIRMED.value: "✅",
            OrderStatus.PROCESSING.value: "🔄",
            OrderStatus.SHIPPED.value: "📦",
            OrderStatus.DELIVERED.value: "✅",
            OrderStatus.CANCELLED.value: "❌",
            OrderStatus.REFUNDED.value: "💰"
        }
        
        emoji = status_emoji.get(order.status, "📋")
        
        result = f"{emoji} **Order {order.order_id}**\n"
        result += f"**Status:** {order.status.replace('_', ' ').title()}\n"
        result += f"**Customer:** {order.customer_name} ({order.customer_email})\n"
        result += f"**Total:** ${order.total_amount:.2f}\n"
        
        if order.tracking_number:
            result += f"**Tracking:** {order.tracking_number}\n"
        
        if order.estimated_delivery:
            delivery_date = time.strftime('%Y-%m-%d', time.localtime(order.estimated_delivery))
            result += f"**Estimated Delivery:** {delivery_date}\n"
        
        result += f"**Items:**\n"
        for item in order.items:
            result += f"  - {item['name']} x{item['quantity']} (${item['price']:.2f})\n"
        
        return result

# Global order manager instance
order_manager = OrderManager()