# app/models/transaction.py
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Enum as SAEnum, Text, Index
from sqlalchemy.orm import relationship
from app.core.database import Base

class TransactionType(str, enum.Enum):
    income = "income"
    expense = "expense"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Core transaction data
    date = Column(DateTime, nullable=False, index=True)
    amount = Column(Numeric(precision=12, scale=2), nullable=False)  # Support large amounts with 2 decimal places
    description = Column(String(500), nullable=False)
    merchant = Column(String(200), nullable=True)
    transaction_type = Column(SAEnum(TransactionType, name="transaction_type"), nullable=False, index=True)
    
    # Additional metadata
    raw_description = Column(Text, nullable=True)  # Original description from bank/CSV
    reference_id = Column(String(100), nullable=True)  # External reference (bank transaction ID)
    notes = Column(Text, nullable=True)  # User notes
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", backref="transactions")
    category = relationship("Category", backref="transactions")

    # Indexes for performance
    __table_args__ = (
        Index("idx_user_date", "user_id", "date"),
        Index("idx_user_category", "user_id", "category_id"),
        Index("idx_user_type_date", "user_id", "transaction_type", "date"),
    )

    def __repr__(self):
        return f"<Transaction(id={self.id}, user_id={self.user_id}, amount={self.amount}, date={self.date})>"