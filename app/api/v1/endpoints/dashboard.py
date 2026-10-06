# app/api/v1/endpoints/dashboard.py
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.crud import transaction as transaction_crud
from app.crud import budget as budget_crud
from app.crud import alert as alert_crud

router = APIRouter()

@router.get("/overview")
def get_dashboard_overview(
    period_days: int = Query(30, ge=1, le=365, description="Number of days for overview"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive dashboard overview"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=period_days)
    
    # Get transaction summary
    transaction_summary = transaction_crud.get_transaction_summary(
        db, current_user.id, start_date, end_date
    )
    
    # Get budget summary
    budget_summary = budget_crud.get_budget_summary(db, current_user.id)
    
    # Get alert summary
    alert_summary = alert_crud.get_alert_summary(db, current_user.id)
    
    # Get recent transactions (last 10)
    recent_transactions = transaction_crud.get_transactions(
        db, current_user.id, skip=0, limit=10, sort_by="date", sort_order="desc"
    )
    
    # Get spending by category
    spending_by_category = transaction_crud.get_spending_by_category(
        db, current_user.id, start_date, end_date
    )
    
    # Calculate savings rate
    savings_rate = 0.0
    if float(transaction_summary.total_income) > 0:
        savings_rate = float(transaction_summary.net_amount) / float(transaction_summary.total_income) * 100
    
    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": period_days
        },
        "financial_summary": {
            "total_income": float(transaction_summary.total_income),
            "total_expenses": float(transaction_summary.total_expense),
            "net_amount": float(transaction_summary.net_amount),
            "savings_rate": round(savings_rate, 2),
            "transaction_count": transaction_summary.transaction_count
        },
        "budget_summary": {
            "total_budgets": budget_summary.total_budgets,
            "active_budgets": budget_summary.active_budgets,
            "exceeded_budgets": budget_summary.exceeded_budgets,
            "warning_budgets": budget_summary.warning_budgets,
            "budget_utilization": round(budget_summary.overall_percentage, 2)
        },
        "alert_summary": {
            "total_alerts": alert_summary.total_alerts,
            "unread_alerts": alert_summary.unread_alerts,
            "critical_alerts": alert_summary.critical_alerts
        },
        "spending_by_category": spending_by_category,
        "recent_transactions": [
            {
                "id": t.id,
                "date": t.date.isoformat(),
                "amount": float(t.amount),
                "description": t.description,
                "merchant": t.merchant,
                "transaction_type": t.transaction_type,
                "category_name": t.category.name if t.category else None
            }
            for t in recent_transactions
        ]
    }

@router.get("/financial-metrics")
def get_financial_metrics(
    compare_period: bool = Query(True, description="Include comparison with previous period"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed financial metrics with trend analysis"""
    
    # Current month
    now = datetime.utcnow()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    current_month_end = now
    
    # Previous month
    if current_month_start.month == 1:
        prev_month_start = current_month_start.replace(year=current_month_start.year - 1, month=12)
    else:
        prev_month_start = current_month_start.replace(month=current_month_start.month - 1)
    
    prev_month_end = current_month_start - timedelta(days=1)
    
    # Get current month summary
    current_summary = transaction_crud.get_transaction_summary(
        db, current_user.id, current_month_start, current_month_end
    )
    
    metrics = {
        "current_month": {
            "period": {
                "start": current_month_start.isoformat(),
                "end": current_month_end.isoformat()
            },
            "income": float(current_summary.total_income),
            "expenses": float(current_summary.total_expense),
            "net": float(current_summary.net_amount),
            "transaction_count": current_summary.transaction_count
        }
    }
    
    if compare_period:
        # Get previous month summary
        prev_summary = transaction_crud.get_transaction_summary(
            db, current_user.id, prev_month_start, prev_month_end
        )
        
        # Calculate changes
        income_change = 0.0
        expense_change = 0.0
        if float(prev_summary.total_income) > 0:
            income_change = ((float(current_summary.total_income) - float(prev_summary.total_income)) 
                           / float(prev_summary.total_income)) * 100
        
        if float(prev_summary.total_expense) > 0:
            expense_change = ((float(current_summary.total_expense) - float(prev_summary.total_expense)) 
                            / float(prev_summary.total_expense)) * 100
        
        metrics["previous_month"] = {
            "period": {
                "start": prev_month_start.isoformat(),
                "end": prev_month_end.isoformat()
            },
            "income": float(prev_summary.total_income),
            "expenses": float(prev_summary.total_expense),
            "net": float(prev_summary.net_amount),
            "transaction_count": prev_summary.transaction_count
        }
        
        metrics["trends"] = {
            "income_change_percent": round(income_change, 2),
            "expense_change_percent": round(expense_change, 2),
            "income_trend": "up" if income_change > 0 else "down" if income_change < 0 else "stable",
            "expense_trend": "up" if expense_change > 0 else "down" if expense_change < 0 else "stable"
        }
    
    return metrics

@router.get("/spending-analytics")
def get_spending_analytics(
    period_months: int = Query(6, ge=1, le=24, description="Number of months to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive spending analytics"""
    
    # Get monthly trends
    monthly_trends = transaction_crud.get_monthly_trends(db, current_user.id, period_months)
    
    # Get spending by category for current month
    now = datetime.utcnow()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    spending_by_category = transaction_crud.get_spending_by_category(
        db, current_user.id, current_month_start, now
    )
    
    # Get top merchants
    top_merchants = transaction_crud.get_top_merchants(
        db, current_user.id, limit=10, start_date=current_month_start, end_date=now
    )
    
    # Process monthly trends for better visualization
    income_trends = []
    expense_trends = []
    
    for trend in monthly_trends:
        month_label = f"{trend['year']}-{trend['month']:02d}"
        if trend['transaction_type'] == 'income':
            income_trends.append({
                "month": month_label,
                "amount": trend['total_amount'],
                "count": trend['transaction_count']
            })
        else:
            expense_trends.append({
                "month": month_label,
                "amount": trend['total_amount'],
                "count": trend['transaction_count']
            })
    
    # Calculate category percentages
    total_spending = sum(cat['total_amount'] for cat in spending_by_category)
    for category in spending_by_category:
        category['percentage'] = round((category['total_amount'] / total_spending) * 100, 2) if total_spending > 0 else 0
    
    return {
        "period_months": period_months,
        "monthly_trends": {
            "income": income_trends,
            "expenses": expense_trends
        },
        "category_breakdown": spending_by_category,
        "top_merchants": top_merchants,
        "insights": {
            "highest_spending_category": max(spending_by_category, key=lambda x: x['total_amount']) if spending_by_category else None,
            "total_categories": len(spending_by_category),
            "average_transaction_size": round(total_spending / sum(cat['transaction_count'] for cat in spending_by_category), 2) if spending_by_category else 0
        }
    }

@router.get("/budget-dashboard")
def get_budget_dashboard(
    include_inactive: bool = Query(False, description="Include inactive budgets"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive budget dashboard data"""
    
    # Get all budget progress
    budget_progress = budget_crud.get_all_budget_progress(db, current_user.id, active_only=not include_inactive)
    
    # Get budget summary
    budget_summary = budget_crud.get_budget_summary(db, current_user.id)
    
    # Get budget alerts
    from app.services.budget_tracker import budget_tracker
    budget_alerts = budget_tracker.get_budgets_needing_alerts(db, current_user.id)
    
    # Process budget progress for dashboard
    budget_data = []
    for progress in budget_progress:
        budget_data.append({
            "id": progress.budget_id,
            "name": progress.budget_name,
            "category": progress.category_name,
            "limit_amount": float(progress.limit_amount),
            "spent_amount": float(progress.spent_amount),
            "remaining_amount": float(progress.remaining_amount),
            "percentage_used": round(progress.percentage_used, 2),
            "is_over_threshold": progress.is_over_threshold,
            "is_exceeded": progress.is_exceeded,
            "days_remaining": progress.days_remaining,
            "period": progress.period,
            "status": "exceeded" if progress.is_exceeded else "warning" if progress.is_over_threshold else "normal"
        })
    
    # Sort by percentage used (highest first)
    budget_data.sort(key=lambda x: x['percentage_used'], reverse=True)
    
    return {
        "summary": {
            "total_budgets": budget_summary.total_budgets,
            "active_budgets": budget_summary.active_budgets,
            "exceeded_budgets": budget_summary.exceeded_budgets,
            "warning_budgets": budget_summary.warning_budgets,
            "total_allocated": float(budget_summary.total_budget_amount),
            "total_spent": float(budget_summary.total_spent_amount),
            "overall_utilization": round(budget_summary.overall_percentage, 2)
        },
        "budgets": budget_data,
        "alerts": [
            {
                "budget_id": alert.budget_id,
                "budget_name": alert.budget_name,
                "category": alert.category_name,
                "percentage_used": round(alert.percentage_used, 2),
                "status": "exceeded" if alert.is_exceeded else "warning",
                "message": f"Budget is at {alert.percentage_used:.1f}% of limit"
            }
            for alert in budget_alerts
        ],
        "insights": {
            "most_utilized_budget": max(budget_data, key=lambda x: x['percentage_used']) if budget_data else None,
            "total_remaining": sum(b['remaining_amount'] for b in budget_data),
            "budgets_on_track": len([b for b in budget_data if not b['is_over_threshold']])
        }
    }

@router.get("/alerts-dashboard")
def get_alerts_dashboard(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of alerts to return"),
    include_read: bool = Query(False, description="Include read alerts"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get alerts dashboard data"""
    
    from app.schemas.alert import AlertFilter
    from app.models.alert import AlertStatus
    
    # Get alerts
    filters = AlertFilter(
        status=None if include_read else AlertStatus.unread
    )
    
    alerts = alert_crud.get_alerts(db, current_user.id, 0, limit, filters)
    
    # Get alert summary
    alert_summary = alert_crud.get_alert_summary(db, current_user.id)
    
    # Process alerts for dashboard
    alert_data = []
    for alert in alerts:
        alert_data.append({
            "id": alert.id,
            "title": alert.title,
            "message": alert.message,
            "type": alert.alert_type,
            "priority": alert.priority,
            "status": alert.status,
            "created_at": alert.created_at.isoformat(),
            "read_at": alert.read_at.isoformat() if alert.read_at else None,
            "transaction_amount": float(alert.transaction.amount) if alert.transaction else None,
            "budget_name": alert.budget.name if alert.budget else None,
            "category_name": alert.category.name if alert.category else None
        })
    
    # Group alerts by type
    alerts_by_type = {}
    for alert in alert_data:
        alert_type = alert['type']
        if alert_type not in alerts_by_type:
            alerts_by_type[alert_type] = []
        alerts_by_type[alert_type].append(alert)
    
    return {
        "summary": {
            "total_alerts": alert_summary.total_alerts,
            "unread_alerts": alert_summary.unread_alerts,
            "high_priority_alerts": alert_summary.high_priority_alerts,
            "critical_alerts": alert_summary.critical_alerts
        },
        "alerts": alert_data,
        "alerts_by_type": alerts_by_type,
        "recent_activity": {
            "latest_alert": alert_data[0] if alert_data else None,
            "alerts_today": len([a for a in alert_data if a['created_at'].startswith(datetime.utcnow().strftime('%Y-%m-%d'))])
        }
    }

@router.get("/performance-metrics")
def get_performance_metrics(
    months_back: int = Query(12, ge=3, le=24, description="Number of months to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get financial performance metrics and KPIs"""
    
    # Calculate time periods
    now = datetime.utcnow()
    start_date = now - timedelta(days=months_back * 30)
    
    # Get monthly trends
    monthly_trends = transaction_crud.get_monthly_trends(db, current_user.id, months_back)
    
    # Calculate performance metrics
    monthly_income = [t for t in monthly_trends if t['transaction_type'] == 'income']
    monthly_expenses = [t for t in monthly_trends if t['transaction_type'] == 'expense']
    
    # Calculate averages
    avg_monthly_income = sum(m['total_amount'] for m in monthly_income) / len(monthly_income) if monthly_income else 0
    avg_monthly_expenses = sum(m['total_amount'] for m in monthly_expenses) / len(monthly_expenses) if monthly_expenses else 0
    avg_savings_rate = ((avg_monthly_income - avg_monthly_expenses) / avg_monthly_income * 100) if avg_monthly_income > 0 else 0
    
    # Calculate trends
    income_trend = "stable"
    expense_trend = "stable"
    
    if len(monthly_income) >= 2:
        recent_income = monthly_income[-1]['total_amount']
        older_income = monthly_income[0]['total_amount']
        if recent_income > older_income * 1.1:
            income_trend = "increasing"
        elif recent_income < older_income * 0.9:
            income_trend = "decreasing"
    
    if len(monthly_expenses) >= 2:
        recent_expenses = monthly_expenses[-1]['total_amount']
        older_expenses = monthly_expenses[0]['total_amount']
        if recent_expenses > older_expenses * 1.1:
            expense_trend = "increasing"
        elif recent_expenses < older_expenses * 0.9:
            expense_trend = "decreasing"
    
    # Get budget performance
    budget_summary = budget_crud.get_budget_summary(db, current_user.id)
    budget_adherence = 100 - budget_summary.overall_percentage if budget_summary.overall_percentage <= 100 else 0
    
    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": now.isoformat(),
            "months": months_back
        },
        "key_metrics": {
            "average_monthly_income": round(avg_monthly_income, 2),
            "average_monthly_expenses": round(avg_monthly_expenses, 2),
            "average_savings_rate": round(avg_savings_rate, 2),
            "budget_adherence_rate": round(budget_adherence, 2)
        },
        "trends": {
            "income_trend": income_trend,
            "expense_trend": expense_trend,
            "financial_health": "excellent" if avg_savings_rate > 20 else "good" if avg_savings_rate > 10 else "fair" if avg_savings_rate > 0 else "needs_improvement"
        },
        "monthly_data": {
            "income": monthly_income,
            "expenses": monthly_expenses
        },
        "insights": {
            "highest_income_month": max(monthly_income, key=lambda x: x['total_amount']) if monthly_income else None,
            "highest_expense_month": max(monthly_expenses, key=lambda x: x['total_amount']) if monthly_expenses else None,
            "best_savings_month": None,  # Can be calculated from income - expenses
            "total_transactions": sum(m['transaction_count'] for m in monthly_trends)
        }
    }

@router.get("/quick-stats")
def get_quick_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get quick statistics for dashboard widgets"""
    
    # Current month
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # This week
    week_start = now - timedelta(days=now.weekday())
    
    # Today
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Get summaries
    month_summary = transaction_crud.get_transaction_summary(db, current_user.id, month_start, now)
    week_summary = transaction_crud.get_transaction_summary(db, current_user.id, week_start, now)
    today_summary = transaction_crud.get_transaction_summary(db, current_user.id, today_start, now)
    
    # Get totals
    all_time_summary = transaction_crud.get_transaction_summary(db, current_user.id)
    
    # Get budget info
    budget_summary = budget_crud.get_budget_summary(db, current_user.id)
    
    # Get alert count
    alert_summary = alert_crud.get_alert_summary(db, current_user.id)
    
    return {
        "today": {
            "income": float(today_summary.total_income),
            "expenses": float(today_summary.total_expense),
            "transactions": today_summary.transaction_count
        },
        "this_week": {
            "income": float(week_summary.total_income),
            "expenses": float(week_summary.total_expense),
            "transactions": week_summary.transaction_count
        },
        "this_month": {
            "income": float(month_summary.total_income),
            "expenses": float(month_summary.total_expense),
            "net": float(month_summary.net_amount),
            "transactions": month_summary.transaction_count
        },
        "all_time": {
            "income": float(all_time_summary.total_income),
            "expenses": float(all_time_summary.total_expense),
            "net": float(all_time_summary.net_amount),
            "transactions": all_time_summary.transaction_count
        },
        "budgets": {
            "active": budget_summary.active_budgets,
            "exceeded": budget_summary.exceeded_budgets,
            "utilization": round(budget_summary.overall_percentage, 1)
        },
        "alerts": {
            "unread": alert_summary.unread_alerts,
            "critical": alert_summary.critical_alerts
        }
    }