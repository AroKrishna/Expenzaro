# app/models/alert.py
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SAEnum, Boolean, Text, Index
from sqlalchemy.orm import relationship
from app.core.database import Base

class AlertType(str, enum.Enum):
    budget_exceeded = "budget_exceeded"
    budget_warning = "budget_warning"
    unusual_spending = "unusual_spending"
    large_transaction = "large_transaction"
    category_overspend = "category_overspend"
    monthly_summary = "monthly_summary"
    fraud_alert = "fraud_alert"
    goal_achieved = "goal_achieved"

class AlertStatus(str, enum.Enum):
    unread = "unread"
    read = "read"
    dismissed = "dismissed"

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Alert content
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    alert_type = Column(SAEnum(AlertType, name="alert_type"), nullable=False, index=True)
    status = Column(SAEnum(AlertStatus, name="alert_status"), default=AlertStatus.unread, nullable=False)
    
    # Alert priority and metadata
    priority = Column(String(20), default="medium")  # low, medium, high, critical
    action_url = Column(String(500), nullable=True)  # URL to take action on alert
    
    # Related entities (optional foreign keys)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=True)
    budget_id = Column(Integer, ForeignKey("budgets.id", ondelete="CASCADE"), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    read_at = Column(DateTime, nullable=True)
    dismissed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", backref="alerts")
    transaction = relationship("Transaction", backref="alerts")
    budget = relationship("Budget", backref="alerts")
    category = relationship("Category", backref="alerts")

    # Indexes for performance
    __table_args__ = (
        Index("idx_user_status", "user_id", "status"),
        Index("idx_user_type_created", "user_id", "alert_type", "created_at"),
        Index("idx_user_unread", "user_id", "status", "created_at"),
    )

    def __repr__(self):
        return f"<Alert(id={self.id}, user_id={self.user_id}, type='{self.alert_type}', status='{self.status}')>"
    
    def mark_as_read(self):
        """Mark alert as read"""
        self.status = AlertStatus.read
        self.read_at = datetime.utcnow()
    
    def dismiss(self):
        """Dismiss alert"""
        self.status = AlertStatus.dismissed
        self.dismissed_at = datetime.utcnow()