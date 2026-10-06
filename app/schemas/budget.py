# app/schemas/budget.py
from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, validator
from app.models.budget import BudgetPeriod

class BudgetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category_id: int
    limit_amount: Decimal = Field(..., gt=0, description="Budget limit must be positive")
    period: BudgetPeriod
    start_date: datetime
    end_date: datetime
    alert_threshold: Optional[Decimal] = Field(80.0, ge=0, le=100, description="Alert threshold percentage (0-100)")
    is_active: bool = True

    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Budget name cannot be empty')
        return v.strip()

    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('End date must be after start date')
        return v

class BudgetCreate(BudgetBase):
    pass

class BudgetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    category_id: Optional[int] = None
    limit_amount: Optional[Decimal] = Field(None, gt=0)
    period: Optional[BudgetPeriod] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    alert_threshold: Optional[Decimal] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None

    @validator('name')
    def name_must_not_be_empty(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Budget name cannot be empty')
        return v.strip() if v else v

    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if v is not None and 'start_date' in values and values['start_date'] is not None:
            if v <= values['start_date']:
                raise ValueError('End date must be after start date')
        return v

class BudgetOut(BudgetBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    category_name: Optional[str] = None
    category_type: Optional[str] = None
    spent_amount: Optional[Decimal] = None
    remaining_amount: Optional[Decimal] = None
    percentage_used: Optional[float] = None
    is_current: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)

class BudgetProgress(BaseModel):
    """Budget progress tracking"""
    budget_id: int
    budget_name: str
    category_name: str
    limit_amount: Decimal
    spent_amount: Decimal
    remaining_amount: Decimal
    percentage_used: float
    alert_threshold: Decimal
    is_over_threshold: bool
    is_exceeded: bool
    days_remaining: int
    period: BudgetPeriod
    start_date: datetime
    end_date: datetime

class BudgetSummary(BaseModel):
    """Summary of all budgets for a user"""
    total_budgets: int
    active_budgets: int
    exceeded_budgets: int
    warning_budgets: int  # Over threshold but not exceeded
    total_budget_amount: Decimal
    total_spent_amount: Decimal
    overall_percentage: float

class BudgetAlert(BaseModel):
    """Budget alert information"""
    budget_id: int
    budget_name: str
    category_name: str
    alert_type: str  # 'warning' or 'exceeded'
    percentage_used: float
    spent_amount: Decimal
    limit_amount: Decimal
    message: str