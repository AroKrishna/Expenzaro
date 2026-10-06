# app/schemas/transaction.py
from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, validator
from app.models.transaction import TransactionType

class TransactionBase(BaseModel):
    date: datetime
    amount: Decimal = Field(..., gt=0, description="Transaction amount must be positive")
    description: str = Field(..., min_length=1, max_length=500)
    merchant: Optional[str] = Field(None, max_length=200)
    transaction_type: TransactionType
    category_id: Optional[int] = None
    raw_description: Optional[str] = None
    reference_id: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None

    @validator('description')
    def description_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Description cannot be empty')
        return v.strip()

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    date: Optional[datetime] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    merchant: Optional[str] = Field(None, max_length=200)
    transaction_type: Optional[TransactionType] = None
    category_id: Optional[int] = None
    raw_description: Optional[str] = None
    reference_id: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None

    @validator('description')
    def description_must_not_be_empty(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Description cannot be empty')
        return v.strip() if v else v

class TransactionOut(TransactionBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    # Optional nested category information
    category_name: Optional[str] = None
    category_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class TransactionSummary(BaseModel):
    """Summary statistics for transactions"""
    total_income: Decimal
    total_expense: Decimal
    net_amount: Decimal
    transaction_count: int
    period_start: datetime
    period_end: datetime

class TransactionFilter(BaseModel):
    """Filter parameters for transaction queries"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    category_id: Optional[int] = None
    transaction_type: Optional[TransactionType] = None
    min_amount: Optional[Decimal] = Field(None, ge=0)
    max_amount: Optional[Decimal] = Field(None, ge=0)
    merchant: Optional[str] = None
    description_search: Optional[str] = None
    
    @validator('max_amount')
    def max_amount_greater_than_min(cls, v, values):
        if v is not None and 'min_amount' in values and values['min_amount'] is not None:
            if v < values['min_amount']:
                raise ValueError('max_amount must be greater than min_amount')
        return v

class BulkTransactionCreate(BaseModel):
    """Schema for bulk transaction creation via CSV"""
    transactions: list[TransactionCreate] = Field(..., min_items=1, max_items=1000)
    
    class Config:
        schema_extra = {
            "example": {
                "transactions": [
                    {
                        "date": "2024-01-15T10:30:00",
                        "amount": 25.50,
                        "description": "Coffee Shop",
                        "merchant": "Starbucks",
                        "transaction_type": "expense",
                        "category_id": 1
                    }
                ]
            }
        }