# app/crud/alert.py
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc

from app.models.alert import Alert, AlertType, AlertStatus
from app.schemas.alert import AlertCreate, AlertUpdate, AlertFilter, AlertSummary

def create_alert(db: Session, alert: AlertCreate, user_id: int) -> Alert:
    """Create a new alert"""
    db_alert = Alert(
        user_id=user_id,
        **alert.dict()
    )
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert

def get_alert(db: Session, alert_id: int, user_id: int) -> Optional[Alert]:
    """Get a specific alert by ID"""
    return db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.user_id == user_id
    ).options(
        joinedload(Alert.transaction),
        joinedload(Alert.budget),
        joinedload(Alert.category)
    ).first()

def get_alerts(
    db: Session, 
    user_id: int, 
    skip: int = 0, 
    limit: int = 100,
    filters: Optional[AlertFilter] = None
) -> List[Alert]:
    """Get alerts with filtering"""
    query = db.query(Alert).filter(Alert.user_id == user_id)
    
    # Apply filters
    if filters:
        if filters.status:
            query = query.filter(Alert.status == filters.status)
        if filters.alert_type:
            query = query.filter(Alert.alert_type == filters.alert_type)
        if filters.priority:
            query = query.filter(Alert.priority == filters.priority)
        if filters.start_date:
            query = query.filter(Alert.created_at >= filters.start_date)
        if filters.end_date:
            query = query.filter(Alert.created_at <= filters.end_date)
        if filters.category_id:
            query = query.filter(Alert.category_id == filters.category_id)
        if filters.budget_id:
            query = query.filter(Alert.budget_id == filters.budget_id)
    
    # Include related information
    query = query.options(
        joinedload(Alert.transaction),
        joinedload(Alert.budget),
        joinedload(Alert.category)
    )
    
    return query.order_by(desc(Alert.created_at)).offset(skip).limit(limit).all()

def update_alert(
    db: Session, 
    alert_id: int, 
    alert_update: AlertUpdate, 
    user_id: int
) -> Optional[Alert]:
    """Update an alert"""
    db_alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.user_id == user_id
    ).first()
    
    if not db_alert:
        return None
    
    # Update only provided fields
    update_data = alert_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_alert, field, value)
    
    db.commit()
    db.refresh(db_alert)
    return db_alert

def delete_alert(db: Session, alert_id: int, user_id: int) -> bool:
    """Delete an alert"""
    db_alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.user_id == user_id
    ).first()
    
    if not db_alert:
        return False
    
    db.delete(db_alert)
    db.commit()
    return True

def mark_alerts_as_read(db: Session, alert_ids: List[int], user_id: int) -> int:
    """Mark multiple alerts as read"""
    updated_count = db.query(Alert).filter(
        Alert.id.in_(alert_ids),
        Alert.user_id == user_id,
        Alert.status == AlertStatus.unread
    ).update({
        Alert.status: AlertStatus.read,
        Alert.read_at: datetime.utcnow()
    }, synchronize_session=False)
    
    db.commit()
    return updated_count

def dismiss_alerts(db: Session, alert_ids: List[int], user_id: int) -> int:
    """Dismiss multiple alerts"""
    updated_count = db.query(Alert).filter(
        Alert.id.in_(alert_ids),
        Alert.user_id == user_id
    ).update({
        Alert.status: AlertStatus.dismissed,
        Alert.dismissed_at: datetime.utcnow()
    }, synchronize_session=False)
    
    db.commit()
    return updated_count

def get_alert_summary(db: Session, user_id: int) -> AlertSummary:
    """Get alert summary statistics"""
    total_alerts = db.query(Alert).filter(Alert.user_id == user_id).count()
    
    unread_alerts = db.query(Alert).filter(
        Alert.user_id == user_id,
        Alert.status == AlertStatus.unread
    ).count()
    
    high_priority_alerts = db.query(Alert).filter(
        Alert.user_id == user_id,
        Alert.priority == 'high',
        Alert.status == AlertStatus.unread
    ).count()
    
    critical_alerts = db.query(Alert).filter(
        Alert.user_id == user_id,
        Alert.priority == 'critical',
        Alert.status == AlertStatus.unread
    ).count()
    
    # Get alerts by type
    alerts_by_type = db.query(
        Alert.alert_type,
        func.count(Alert.id).label('count')
    ).filter(
        Alert.user_id == user_id,
        Alert.status == AlertStatus.unread
    ).group_by(Alert.alert_type).all()
    
    alerts_by_type_dict = {str(result.alert_type): result.count for result in alerts_by_type}
    
    # Get latest alert
    latest_alert = db.query(Alert).filter(
        Alert.user_id == user_id
    ).order_by(desc(Alert.created_at)).first()
    
    return AlertSummary(
        total_alerts=total_alerts,
        unread_alerts=unread_alerts,
        high_priority_alerts=high_priority_alerts,
        critical_alerts=critical_alerts,
        alerts_by_type=alerts_by_type_dict,
        latest_alert=latest_alert
    )

def create_budget_alert(
    db: Session,
    user_id: int,
    budget_id: int,
    alert_type: AlertType,
    title: str,
    message: str,
    priority: str = "medium"
) -> Alert:
    """Create a budget-related alert"""
    alert_data = AlertCreate(
        title=title,
        message=message,
        alert_type=alert_type,
        priority=priority,
        budget_id=budget_id
    )
    
    return create_alert(db, alert_data, user_id)

def create_transaction_alert(
    db: Session,
    user_id: int,
    transaction_id: int,
    alert_type: AlertType,
    title: str,
    message: str,
    priority: str = "medium"
) -> Alert:
    """Create a transaction-related alert"""
    alert_data = AlertCreate(
        title=title,
        message=message,
        alert_type=alert_type,
        priority=priority,
        transaction_id=transaction_id
    )
    
    return create_alert(db, alert_data, user_id)

def check_for_duplicate_alerts(
    db: Session,
    user_id: int,
    alert_type: AlertType,
    budget_id: Optional[int] = None,
    transaction_id: Optional[int] = None,
    hours_threshold: int = 24
) -> bool:
    """Check if a similar alert was created recently to avoid spam"""
    threshold_time = datetime.utcnow() - timedelta(hours=hours_threshold)
    
    query = db.query(Alert).filter(
        Alert.user_id == user_id,
        Alert.alert_type == alert_type,
        Alert.created_at >= threshold_time
    )
    
    if budget_id:
        query = query.filter(Alert.budget_id == budget_id)
    if transaction_id:
        query = query.filter(Alert.transaction_id == transaction_id)
    
    return query.first() is not None

def cleanup_old_alerts(db: Session, days_old: int = 30) -> int:
    """Clean up old dismissed alerts"""
    from datetime import timedelta
    
    threshold_date = datetime.utcnow() - timedelta(days=days_old)
    
    deleted_count = db.query(Alert).filter(
        Alert.status == AlertStatus.dismissed,
        Alert.dismissed_at < threshold_date
    ).delete()
    
    db.commit()
    return deleted_count