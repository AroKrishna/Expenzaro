# app/api/v1/endpoints/budget.py
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.budget import BudgetPeriod
from app.crud import budget as budget_crud
from app.schemas.budget import (
    BudgetCreate, BudgetUpdate, BudgetOut, BudgetProgress, 
    BudgetSummary, BudgetAlert
)

router = APIRouter()

@router.post("/", response_model=BudgetOut, status_code=status.HTTP_201_CREATED)
def create_budget(
    budget_data: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new budget"""
    # Validate category belongs to user
    from app.models.category import Category
    category = db.query(Category).filter(
        Category.id == budget_data.category_id,
        Category.user_id == current_user.id
    ).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found or doesn't belong to user"
        )
    
    # Check for overlapping budgets
    existing_budget = db.query(budget_crud.Budget).filter(
        budget_crud.Budget.user_id == current_user.id,
        budget_crud.Budget.category_id == budget_data.category_id,
        budget_crud.Budget.is_active == True,
        budget_crud.Budget.start_date <= budget_data.end_date,
        budget_crud.Budget.end_date >= budget_data.start_date
    ).first()
    
    if existing_budget:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A budget already exists for this category in the specified period"
        )
    
    budget = budget_crud.create_budget(db, budget_data, current_user.id)
    
    # Enrich with category information
    budget_dict = {
        **budget.__dict__,
        'category_name': budget.category.name if budget.category else None,
        'category_type': budget.category.type if budget.category else None,
        'is_current': budget.is_current
    }
    
    return BudgetOut(**budget_dict)

@router.get("/", response_model=List[BudgetOut])
def get_budgets(
    skip: int = Query(0, ge=0, description="Number of budgets to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of budgets to return"),
    active_only: bool = Query(False, description="Only return active budgets"),
    current_only: bool = Query(False, description="Only return current budgets"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    period: Optional[BudgetPeriod] = Query(None, description="Filter by budget period"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get budgets with filtering"""
    budgets = budget_crud.get_budgets(db, current_user.id, skip, limit, active_only, current_only)
    
    # Apply additional filters
    if category_id:
        budgets = [b for b in budgets if b.category_id == category_id]
    if period:
        budgets = [b for b in budgets if b.period == period]
    
    # Enrich with category and progress information
    enriched_budgets = []
    for budget in budgets:
        progress = budget_crud.get_budget_progress(db, budget.id, current_user.id)
        budget_dict = {
            **budget.__dict__,
            'category_name': budget.category.name if budget.category else None,
            'category_type': budget.category.type if budget.category else None,
            'is_current': budget.is_current,
            'spent_amount': progress.spent_amount if progress else 0,
            'remaining_amount': progress.remaining_amount if progress else budget.limit_amount,
            'percentage_used': progress.percentage_used if progress else 0
        }
        enriched_budgets.append(BudgetOut(**budget_dict))
    
    return enriched_budgets

@router.get("/summary", response_model=BudgetSummary)
def get_budget_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get overall budget summary"""
    return budget_crud.get_budget_summary(db, current_user.id)

@router.get("/progress", response_model=List[BudgetProgress])
def get_all_budget_progress(
    active_only: bool = Query(True, description="Only return active budgets"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get progress for all budgets"""
    return budget_crud.get_all_budget_progress(db, current_user.id, active_only)

@router.get("/alerts")
def get_budget_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get budgets that need alerts"""
    budgets_needing_alerts = budget_crud.get_budgets_needing_alerts(db, current_user.id)
    
    alerts = []
    for progress in budgets_needing_alerts:
        alert_type = "exceeded" if progress.is_exceeded else "warning"
        message = f"Budget '{progress.budget_name}' "
        
        if progress.is_exceeded:
            overage = progress.spent_amount - progress.limit_amount
            message += f"exceeded by ${overage:.2f}"
        else:
            message += f"is at {progress.percentage_used:.1f}% of limit"
        
        alerts.append({
            "budget_id": progress.budget_id,
            "budget_name": progress.budget_name,
            "category_name": progress.category_name,
            "alert_type": alert_type,
            "percentage_used": progress.percentage_used,
            "spent_amount": float(progress.spent_amount),
            "limit_amount": float(progress.limit_amount),
            "message": message
        })
    
    return alerts

@router.get("/{budget_id}", response_model=BudgetOut)
def get_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific budget"""
    budget = budget_crud.get_budget(db, budget_id, current_user.id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )
    
    # Get progress information
    progress = budget_crud.get_budget_progress(db, budget_id, current_user.id)
    
    # Enrich with category and progress information
    budget_dict = {
        **budget.__dict__,
        'category_name': budget.category.name if budget.category else None,
        'category_type': budget.category.type if budget.category else None,
        'is_current': budget.is_current,
        'spent_amount': progress.spent_amount if progress else 0,
        'remaining_amount': progress.remaining_amount if progress else budget.limit_amount,
        'percentage_used': progress.percentage_used if progress else 0
    }
    
    return BudgetOut(**budget_dict)

@router.get("/{budget_id}/progress", response_model=BudgetProgress)
def get_budget_progress(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed budget progress"""
    progress = budget_crud.get_budget_progress(db, budget_id, current_user.id)
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )
    return progress

@router.get("/{budget_id}/history")
def get_budget_history(
    budget_id: int,
    months: int = Query(6, ge=1, le=24, description="Number of months of history"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get spending history for a budget"""
    # Verify budget belongs to user
    budget = budget_crud.get_budget(db, budget_id, current_user.id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )
    
    return budget_crud.get_budget_history(db, budget_id, current_user.id, months)

@router.put("/{budget_id}", response_model=BudgetOut)
def update_budget(
    budget_id: int,
    budget_update: BudgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a budget"""
    # Validate category belongs to user if being updated
    if budget_update.category_id:
        from app.models.category import Category
        category = db.query(Category).filter(
            Category.id == budget_update.category_id,
            Category.user_id == current_user.id
        ).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found or doesn't belong to user"
            )
    
    budget = budget_crud.update_budget(db, budget_id, budget_update, current_user.id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )
    
    # Get progress information
    progress = budget_crud.get_budget_progress(db, budget_id, current_user.id)
    
    # Enrich with category and progress information
    budget_dict = {
        **budget.__dict__,
        'category_name': budget.category.name if budget.category else None,
        'category_type': budget.category.type if budget.category else None,
        'is_current': budget.is_current,
        'spent_amount': progress.spent_amount if progress else 0,
        'remaining_amount': progress.remaining_amount if progress else budget.limit_amount,
        'percentage_used': progress.percentage_used if progress else 0
    }
    
    return BudgetOut(**budget_dict)

@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a budget"""
    success = budget_crud.delete_budget(db, budget_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )
    return None

@router.post("/check-violations")
def check_budget_violations(
    category_id: int,
    amount: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if a transaction would violate any budgets"""
    from decimal import Decimal
    violations = budget_crud.check_budget_violations(
        db, current_user.id, category_id, Decimal(str(amount))
    )
    return {"violations": violations}