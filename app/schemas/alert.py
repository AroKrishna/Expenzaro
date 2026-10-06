# app/schemas/alert.py
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.alert import AlertType, AlertStatus

class AlertBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1)
    alert_type: AlertType
    priority: str = Field("medium", pattern="^(low|medium|high|critical)$")
    action_url: Optional[str] = Field(None, max_length=500)
    
    # Optional related entity IDs
    transaction_id: Optional[int] = None
    budget_id: Optional[int] = None
    category_id: Optional[int] = None

class AlertCreate(AlertBase):
    pass

class AlertUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    message: Optional[str] = Field(None, min_length=1)
    alert_type: Optional[AlertType] = None
    status: Optional[AlertStatus] = None
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|critical)$")
    action_url: Optional[str] = Field(None, max_length=500)

class AlertOut(AlertBase):
    id: int
    user_id: int
    status: AlertStatus
    created_at: datetime
    read_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    
    # Related entity information (if available)
    transaction_amount: Optional[float] = None
    budget_name: Optional[str] = None
    category_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class AlertMarkRead(BaseModel):
    """Schema for marking alerts as read"""
    alert_ids: list[int] = Field(..., min_items=1, max_items=100)

class AlertFilter(BaseModel):
    """Filter parameters for alert queries"""
    status: Optional[AlertStatus] = None
    alert_type: Optional[AlertType] = None
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|critical)$")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    category_id: Optional[int] = None
    budget_id: Optional[int] = None

class AlertSummary(BaseModel):
    """Summary of alerts for a user"""
    total_alerts: int
    unread_alerts: int
    high_priority_alerts: int
    critical_alerts: int
    alerts_by_type: dict[str, int]
    latest_alert: Optional[AlertOut] = None

class AlertBulkAction(BaseModel):
    """Schema for bulk actions on alerts"""
    alert_ids: list[int] = Field(..., min_items=1, max_items=100)
    action: str = Field(..., pattern="^(mark_read|dismiss|delete)$")