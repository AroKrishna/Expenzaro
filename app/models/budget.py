# app/models/budget.py
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Enum as SAEnum, Boolean, Index
from sqlalchemy.orm import relationship
from app.core.database import Base

class BudgetPeriod(str, enum.Enum):
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"

class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Budget details
    name = Column(String(200), nullable=False)  # Budget name (e.g., "Monthly Food Budget")
    limit_amount = Column(Numeric(precision=12, scale=2), nullable=False)
    period = Column(SAEnum(BudgetPeriod, name="budget_period"), nullable=False)
    
    # Period dates
    start_date = Column(DateTime, nullable=False, index=True)
    end_date = Column(DateTime, nullable=False, index=True)
    
    # Budget status
    is_active = Column(Boolean, default=True, nullable=False)
    alert_threshold = Column(Numeric(precision=5, scale=2), default=80.0)  # Alert when 80% of budget is reached
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", backref="budgets")
    category = relationship("Category", backref="budgets")

    # Indexes for performance
    __table_args__ = (
        Index("idx_user_period", "user_id", "start_date", "end_date"),
        Index("idx_user_category_active", "user_id", "category_id", "is_active"),
    )

    def __repr__(self):
        return f"<Budget(id={self.id}, user_id={self.user_id}, name='{self.name}', limit={self.limit_amount})>"
    
    @property
    def is_current(self):
        """Check if budget is currently active based on dates"""
        now = datetime.utcnow()
        return self.start_date <= now <= self.end_date and self.is_active