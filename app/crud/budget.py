# app/crud/budget.py
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func, desc
from decimal import Decimal

from app.models.budget import Budget, BudgetPeriod
from app.models.transaction import Transaction, TransactionType
from app.models.category import Category
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetProgress, BudgetSummary

def create_budget(db: Session, budget: BudgetCreate, user_id: int) -> Budget:
    """Create a new budget"""
    db_budget = Budget(
        user_id=user_id,
        **budget.dict()
    )
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    return db_budget

def get_budget(db: Session, budget_id: int, user_id: int) -> Optional[Budget]:
    """Get a specific budget by ID"""
    return db.query(Budget).filter(
        Budget.id == budget_id,
        Budget.user_id == user_id
    ).options(joinedload(Budget.category)).first()

def get_budgets(
    db: Session, 
    user_id: int, 
    skip: int = 0, 
    limit: int = 100,
    active_only: bool = False,
    current_only: bool = False
) -> List[Budget]:
    """Get budgets with optional filtering"""
    query = db.query(Budget).filter(Budget.user_id == user_id)
    
    if active_only:
        query = query.filter(Budget.is_active == True)
    
    if current_only:
        now = datetime.utcnow()
        query = query.filter(
            Budget.start_date <= now,
            Budget.end_date >= now,
            Budget.is_active == True
        )
    
    # Include category information
    query = query.options(joinedload(Budget.category))
    
    return query.order_by(desc(Budget.created_at)).offset(skip).limit(limit).all()

def update_budget(
    db: Session, 
    budget_id: int, 
    budget_update: BudgetUpdate, 
    user_id: int
) -> Optional[Budget]:
    """Update a budget"""
    db_budget = db.query(Budget).filter(
        Budget.id == budget_id,
        Budget.user_id == user_id
    ).first()
    
    if not db_budget:
        return None
    
    # Update only provided fields
    update_data = budget_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_budget, field, value)
    
    db_budget.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_budget)
    return db_budget

def delete_budget(db: Session, budget_id: int, user_id: int) -> bool:
    """Delete a budget"""
    db_budget = db.query(Budget).filter(
        Budget.id == budget_id,
        Budget.user_id == user_id
    ).first()
    
    if not db_budget:
        return False
    
    db.delete(db_budget)
    db.commit()
    return True

def get_budget_progress(db: Session, budget_id: int, user_id: int) -> Optional[BudgetProgress]:
    """Get detailed budget progress information"""
    budget = db.query(Budget).filter(
        Budget.id == budget_id,
        Budget.user_id == user_id
    ).options(joinedload(Budget.category)).first()
    
    if not budget:
        return None
    
    # Calculate spent amount for this budget period
    spent_amount = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.user_id == user_id,
        Transaction.category_id == budget.category_id,
        Transaction.transaction_type == TransactionType.expense,
        Transaction.date >= budget.start_date,
        Transaction.date <= budget.end_date
    ).scalar() or Decimal('0')
    
    # Calculate progress metrics
    remaining_amount = budget.limit_amount - spent_amount
    percentage_used = float((spent_amount / budget.limit_amount) * 100) if budget.limit_amount > 0 else 0
    
    # Calculate days remaining
    now = datetime.utcnow()
    days_remaining = max(0, (budget.end_date - now).days) if budget.end_date > now else 0
    
    return BudgetProgress(
        budget_id=budget.id,
        budget_name=budget.name,
        category_name=budget.category.name if budget.category else "Unknown",
        limit_amount=budget.limit_amount,
        spent_amount=spent_amount,
        remaining_amount=remaining_amount,
        percentage_used=percentage_used,
        alert_threshold=budget.alert_threshold,
        is_over_threshold=percentage_used >= float(budget.alert_threshold),
        is_exceeded=spent_amount >= budget.limit_amount,
        days_remaining=days_remaining,
        period=budget.period,
        start_date=budget.start_date,
        end_date=budget.end_date
    )

def get_all_budget_progress(db: Session, user_id: int, active_only: bool = True) -> List[BudgetProgress]:
    """Get progress for all user budgets"""
    budgets = get_budgets(db, user_id, active_only=active_only, limit=1000)
    progress_list = []
    
    for budget in budgets:
        progress = get_budget_progress(db, budget.id, user_id)
        if progress:
            progress_list.append(progress)
    
    return progress_list

def get_budget_summary(db: Session, user_id: int) -> BudgetSummary:
    """Get overall budget summary for user"""
    # Get all active budgets
    active_budgets = get_budgets(db, user_id, active_only=True, limit=1000)
    total_budgets = len(get_budgets(db, user_id, limit=1000))
    
    # Calculate totals and counts
    total_budget_amount = Decimal('0')
    total_spent_amount = Decimal('0')
    exceeded_count = 0
    warning_count = 0
    
    for budget in active_budgets:
        progress = get_budget_progress(db, budget.id, user_id)
        if progress:
            total_budget_amount += progress.limit_amount
            total_spent_amount += progress.spent_amount
            
            if progress.is_exceeded:
                exceeded_count += 1
            elif progress.is_over_threshold:
                warning_count += 1
    
    overall_percentage = float((total_spent_amount / total_budget_amount) * 100) if total_budget_amount > 0 else 0
    
    return BudgetSummary(
        total_budgets=total_budgets,
        active_budgets=len(active_budgets),
        exceeded_budgets=exceeded_count,
        warning_budgets=warning_count,
        total_budget_amount=total_budget_amount,
        total_spent_amount=total_spent_amount,
        overall_percentage=overall_percentage
    )

def get_budgets_needing_alerts(db: Session, user_id: int) -> List[BudgetProgress]:
    """Get budgets that need alerts (over threshold or exceeded)"""
    progress_list = get_all_budget_progress(db, user_id, active_only=True)
    
    return [
        progress for progress in progress_list
        if progress.is_over_threshold or progress.is_exceeded
    ]

def check_budget_violations(db: Session, user_id: int, category_id: int, transaction_amount: Decimal) -> List[Dict[str, Any]]:
    """Check if a transaction would violate any budgets"""
    now = datetime.utcnow()
    
    # Get active budgets for this category
    active_budgets = db.query(Budget).filter(
        Budget.user_id == user_id,
        Budget.category_id == category_id,
        Budget.is_active == True,
        Budget.start_date <= now,
        Budget.end_date >= now
    ).all()
    
    violations = []
    
    for budget in active_budgets:
        # Calculate current spent amount
        spent_amount = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == user_id,
            Transaction.category_id == category_id,
            Transaction.transaction_type == TransactionType.expense,
            Transaction.date >= budget.start_date,
            Transaction.date <= budget.end_date
        ).scalar() or Decimal('0')
        
        # Calculate new total with this transaction
        new_total = spent_amount + transaction_amount
        new_percentage = float((new_total / budget.limit_amount) * 100) if budget.limit_amount > 0 else 0
        
        # Check for violations
        if new_total > budget.limit_amount:
            violations.append({
                'budget_id': budget.id,
                'budget_name': budget.name,
                'violation_type': 'exceeded',
                'current_amount': float(spent_amount),
                'new_amount': float(new_total),
                'limit_amount': float(budget.limit_amount),
                'percentage': new_percentage,
                'overage': float(new_total - budget.limit_amount)
            })
        elif new_percentage >= float(budget.alert_threshold):
            violations.append({
                'budget_id': budget.id,
                'budget_name': budget.name,
                'violation_type': 'warning',
                'current_amount': float(spent_amount),
                'new_amount': float(new_total),
                'limit_amount': float(budget.limit_amount),
                'percentage': new_percentage,
                'threshold': float(budget.alert_threshold)
            })
    
    return violations

def get_budget_history(db: Session, budget_id: int, user_id: int, months: int = 6) -> List[Dict[str, Any]]:
    """Get spending history for a budget over time"""
    budget = get_budget(db, budget_id, user_id)
    if not budget:
        return []
    
    # Get monthly spending for this category
    start_date = datetime.utcnow() - timedelta(days=months * 30)
    
    monthly_data = db.query(
        func.date_trunc('month', Transaction.date).label('month'),
        func.sum(Transaction.amount).label('total_amount'),
        func.count(Transaction.id).label('transaction_count')
    ).filter(
        Transaction.user_id == user_id,
        Transaction.category_id == budget.category_id,
        Transaction.transaction_type == TransactionType.expense,
        Transaction.date >= start_date
    ).group_by(
        func.date_trunc('month', Transaction.date)
    ).order_by(
        func.date_trunc('month', Transaction.date)
    ).all()
    
    return [
        {
            'month': result.month.strftime('%Y-%m'),
            'total_amount': float(result.total_amount),
            'transaction_count': result.transaction_count,
            'budget_limit': float(budget.limit_amount),
            'percentage_used': float((result.total_amount / budget.limit_amount) * 100) if budget.limit_amount > 0 else 0
        }
        for result in monthly_data
    ]