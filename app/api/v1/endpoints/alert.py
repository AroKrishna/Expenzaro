# app/api/v1/endpoints/alert.py
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.alert import AlertType, AlertStatus
from app.crud import alert as alert_crud
from app.schemas.alert import (
    AlertCreate, AlertUpdate, AlertOut, AlertFilter, 
    AlertSummary, AlertMarkRead, AlertBulkAction
)

router = APIRouter()

@router.get("/", response_model=List[AlertOut])
def get_alerts(
    skip: int = Query(0, ge=0, description="Number of alerts to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of alerts to return"),
    status: Optional[AlertStatus] = Query(None, description="Filter by alert status"),
    alert_type: Optional[AlertType] = Query(None, description="Filter by alert type"),
    priority: Optional[str] = Query(None, regex="^(low|medium|high|critical)$", description="Filter by priority"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    unread_only: bool = Query(False, description="Only return unread alerts"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get alerts with filtering"""
    filters = AlertFilter(
        status=AlertStatus.unread if unread_only else status,
        alert_type=alert_type,
        priority=priority,
        start_date=start_date,
        end_date=end_date
    )
    
    alerts = alert_crud.get_alerts(db, current_user.id, skip, limit, filters)
    
    # Enrich with related information
    enriched_alerts = []
    for alert in alerts:
        alert_dict = {
            **alert.__dict__,
            'transaction_amount': float(alert.transaction.amount) if alert.transaction else None,
            'budget_name': alert.budget.name if alert.budget else None,
            'category_name': alert.category.name if alert.category else None
        }
        enriched_alerts.append(AlertOut(**alert_dict))
    
    return enriched_alerts

@router.get("/summary", response_model=AlertSummary)
def get_alert_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get alert summary statistics"""
    return alert_crud.get_alert_summary(db, current_user.id)

@router.get("/{alert_id}", response_model=AlertOut)
def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific alert"""
    alert = alert_crud.get_alert(db, alert_id, current_user.id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    # Enrich with related information
    alert_dict = {
        **alert.__dict__,
        'transaction_amount': float(alert.transaction.amount) if alert.transaction else None,
        'budget_name': alert.budget.name if alert.budget else None,
        'category_name': alert.category.name if alert.category else None
    }
    
    return AlertOut(**alert_dict)

@router.post("/", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
def create_alert(
    alert_data: AlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new alert (for testing or admin purposes)"""
    # Validate related entities belong to user
    if alert_data.transaction_id:
        from app.models.transaction import Transaction
        transaction = db.query(Transaction).filter(
            Transaction.id == alert_data.transaction_id,
            Transaction.user_id == current_user.id
        ).first()
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transaction not found or doesn't belong to user"
            )
    
    if alert_data.budget_id:
        from app.models.budget import Budget
        budget = db.query(Budget).filter(
            Budget.id == alert_data.budget_id,
            Budget.user_id == current_user.id
        ).first()
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Budget not found or doesn't belong to user"
            )
    
    if alert_data.category_id:
        from app.models.category import Category
        category = db.query(Category).filter(
            Category.id == alert_data.category_id,
            Category.user_id == current_user.id
        ).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found or doesn't belong to user"
            )
    
    alert = alert_crud.create_alert(db, alert_data, current_user.id)
    return AlertOut(**alert.__dict__)

@router.put("/{alert_id}", response_model=AlertOut)
def update_alert(
    alert_id: int,
    alert_update: AlertUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an alert"""
    alert = alert_crud.update_alert(db, alert_id, alert_update, current_user.id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    return AlertOut(**alert.__dict__)

@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an alert"""
    success = alert_crud.delete_alert(db, alert_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    return None

@router.post("/mark-read")
def mark_alerts_as_read(
    alert_data: AlertMarkRead,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark multiple alerts as read"""
    updated_count = alert_crud.mark_alerts_as_read(
        db, alert_data.alert_ids, current_user.id
    )
    
    return {
        "message": f"Marked {updated_count} alerts as read",
        "updated_count": updated_count
    }

@router.post("/bulk-action")
def bulk_alert_action(
    action_data: AlertBulkAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Perform bulk actions on alerts"""
    if action_data.action == "mark_read":
        updated_count = alert_crud.mark_alerts_as_read(
            db, action_data.alert_ids, current_user.id
        )
        return {
            "message": f"Marked {updated_count} alerts as read",
            "updated_count": updated_count
        }
    
    elif action_data.action == "dismiss":
        updated_count = alert_crud.dismiss_alerts(
            db, action_data.alert_ids, current_user.id
        )
        return {
            "message": f"Dismissed {updated_count} alerts",
            "updated_count": updated_count
        }
    
    elif action_data.action == "delete":
        deleted_count = 0
        for alert_id in action_data.alert_ids:
            if alert_crud.delete_alert(db, alert_id, current_user.id):
                deleted_count += 1
        
        return {
            "message": f"Deleted {deleted_count} alerts",
            "deleted_count": deleted_count
        }
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be 'mark_read', 'dismiss', or 'delete'"
        )

# Budget tracking endpoints
@router.post("/check-budgets")
def check_user_budgets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually trigger budget check for current user"""
    from app.services.budget_tracker import budget_tracker
    
    results = budget_tracker.check_user_budgets(db, current_user.id)
    
    return {
        "message": f"Checked {results['budgets_checked']} budgets, created {results['alerts_created']} alerts",
        **results
    }

@router.get("/insights")
def get_spending_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get personalized spending insights"""
    from app.services.budget_tracker import budget_tracker
    
    insights = budget_tracker.generate_spending_insights(db, current_user.id)
    
    return {
        "insights": insights,
        "insights_count": len(insights)
    }

@router.post("/test-alert")
def create_test_alert(
    alert_type: AlertType = AlertType.budget_warning,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a test alert (for development/testing)"""
    test_alert = AlertCreate(
        title="Test Alert",
        message="This is a test alert to verify the alert system is working correctly.",
        alert_type=alert_type,
        priority="low"
    )
    
    alert = alert_crud.create_alert(db, test_alert, current_user.id)
    
    return {
        "message": "Test alert created successfully",
        "alert": AlertOut(**alert.__dict__)
    }