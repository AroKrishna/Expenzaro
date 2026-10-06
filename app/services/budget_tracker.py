# app/services/budget_tracker.py
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from decimal import Decimal

from app.models.transaction import Transaction, TransactionType
from app.models.budget import Budget
from app.models.alert import AlertType
from app.crud import budget as budget_crud
from app.crud import alert as alert_crud

class BudgetTracker:
    """
    Service for tracking budget usage and generating alerts when limits are approached or exceeded.
    """
    
    def __init__(self):
        self.alert_thresholds = [50, 75, 90, 100]  # Percentage thresholds for alerts
    
    def check_budget_after_transaction(
        self, 
        db: Session, 
        user_id: int, 
        transaction: Transaction
    ) -> List[Dict[str, Any]]:
        """
        Check budgets after a transaction is created and generate alerts if needed.
        
        Args:
            db: Database session
            user_id: User ID
            transaction: The transaction that was just created
            
        Returns:
            List of alerts created
        """
        alerts_created = []
        
        # Only check budgets for expense transactions with categories
        if (transaction.transaction_type != TransactionType.expense or 
            not transaction.category_id):
            return alerts_created
        
        # Get active budgets for this category
        active_budgets = db.query(Budget).filter(
            Budget.user_id == user_id,
            Budget.category_id == transaction.category_id,
            Budget.is_active == True,
            Budget.start_date <= transaction.date,
            Budget.end_date >= transaction.date
        ).all()
        
        for budget in active_budgets:
            progress = budget_crud.get_budget_progress(db, budget.id, user_id)
            if not progress:
                continue
            
            # Check if we need to create alerts
            alert_info = self._determine_alert_needed(progress, budget)
            
            if alert_info:
                # Check for duplicate alerts to avoid spam
                if not alert_crud.check_for_duplicate_alerts(
                    db, user_id, alert_info['alert_type'], budget_id=budget.id, hours_threshold=6
                ):
                    alert = alert_crud.create_budget_alert(
                        db=db,
                        user_id=user_id,
                        budget_id=budget.id,
                        alert_type=alert_info['alert_type'],
                        title=alert_info['title'],
                        message=alert_info['message'],
                        priority=alert_info['priority']
                    )
                    alerts_created.append({
                        'alert_id': alert.id,
                        'budget_id': budget.id,
                        'alert_type': alert_info['alert_type'],
                        'message': alert_info['message']
                    })
        
        return alerts_created
    
    def _determine_alert_needed(self, progress, budget) -> Optional[Dict[str, Any]]:
        """
        Determine if an alert is needed based on budget progress.
        """
        percentage_used = progress.percentage_used
        
        if progress.is_exceeded:
            overage = progress.spent_amount - progress.limit_amount
            return {
                'alert_type': AlertType.budget_exceeded,
                'title': f"Budget Exceeded: {progress.budget_name}",
                'message': (
                    f"Your '{progress.budget_name}' budget has been exceeded by "
                    f"${overage:.2f}. You've spent ${progress.spent_amount:.2f} "
                    f"out of ${progress.limit_amount:.2f} ({percentage_used:.1f}%)."
                ),
                'priority': 'high'
            }
        elif progress.is_over_threshold:
            return {
                'alert_type': AlertType.budget_warning,
                'title': f"Budget Warning: {progress.budget_name}",
                'message': (
                    f"Your '{progress.budget_name}' budget is at {percentage_used:.1f}% "
                    f"(${progress.spent_amount:.2f} of ${progress.limit_amount:.2f}). "
                    f"You have ${progress.remaining_amount:.2f} remaining."
                ),
                'priority': 'medium'
            }
        
        return None
    
    def check_all_budgets_daily(self, db: Session) -> Dict[str, Any]:
        """
        Daily check for all users' budgets to generate alerts.
        This would typically be run as a scheduled task.
        """
        from app.models.user import User
        
        results = {
            'users_checked': 0,
            'budgets_checked': 0,
            'alerts_created': 0,
            'details': []
        }
        
        # Get all users
        users = db.query(User).filter(User.is_active == True).all()
        
        for user in users:
            user_results = self.check_user_budgets(db, user.id)
            results['users_checked'] += 1
            results['budgets_checked'] += user_results['budgets_checked']
            results['alerts_created'] += user_results['alerts_created']
            
            if user_results['alerts_created'] > 0:
                results['details'].append({
                    'user_id': user.id,
                    'user_email': user.email,
                    **user_results
                })
        
        return results
    
    def check_user_budgets(self, db: Session, user_id: int) -> Dict[str, Any]:
        """
        Check all budgets for a specific user and generate alerts.
        """
        results = {
            'budgets_checked': 0,
            'alerts_created': 0,
            'budget_details': []
        }
        
        # Get all active budgets for user
        active_budgets = budget_crud.get_budgets(
            db, user_id, active_only=True, current_only=True, limit=1000
        )
        
        for budget in active_budgets:
            results['budgets_checked'] += 1
            
            progress = budget_crud.get_budget_progress(db, budget.id, user_id)
            if not progress:
                continue
            
            alert_info = self._determine_alert_needed(progress, budget)
            
            if alert_info:
                # Check for recent similar alerts
                if not alert_crud.check_for_duplicate_alerts(
                    db, user_id, alert_info['alert_type'], budget_id=budget.id, hours_threshold=24
                ):
                    alert = alert_crud.create_budget_alert(
                        db=db,
                        user_id=user_id,
                        budget_id=budget.id,
                        alert_type=alert_info['alert_type'],
                        title=alert_info['title'],
                        message=alert_info['message'],
                        priority=alert_info['priority']
                    )
                    
                    results['alerts_created'] += 1
                    results['budget_details'].append({
                        'budget_id': budget.id,
                        'budget_name': budget.name,
                        'percentage_used': progress.percentage_used,
                        'alert_created': True,
                        'alert_type': alert_info['alert_type']
                    })
                else:
                    results['budget_details'].append({
                        'budget_id': budget.id,
                        'budget_name': budget.name,
                        'percentage_used': progress.percentage_used,
                        'alert_created': False,
                        'reason': 'Recent alert exists'
                    })
            else:
                results['budget_details'].append({
                    'budget_id': budget.id,
                    'budget_name': budget.name,
                    'percentage_used': progress.percentage_used,
                    'alert_created': False,
                    'reason': 'No alert needed'
                })
        
        return results
    
    def detect_unusual_spending(self, db: Session, user_id: int, transaction: Transaction) -> Optional[Dict[str, Any]]:
        """
        Detect if a transaction represents unusual spending patterns.
        """
        # Only check expense transactions
        if transaction.transaction_type != TransactionType.expense:
            return None
        
        # Get historical data for this category
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        historical_transactions = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.category_id == transaction.category_id,
            Transaction.transaction_type == TransactionType.expense,
            Transaction.date >= thirty_days_ago,
            Transaction.id != transaction.id  # Exclude current transaction
        ).all()
        
        if len(historical_transactions) < 5:  # Need enough data
            return None
        
        # Calculate statistics
        amounts = [float(t.amount) for t in historical_transactions]
        avg_amount = sum(amounts) / len(amounts)
        max_amount = max(amounts)
        
        current_amount = float(transaction.amount)
        
        # Check for unusual patterns
        is_large_transaction = current_amount > (avg_amount * 3)  # 3x average
        is_record_high = current_amount > max_amount * 1.5  # 50% higher than previous max
        
        if is_large_transaction or is_record_high:
            return {
                'transaction_id': transaction.id,
                'amount': current_amount,
                'average_amount': avg_amount,
                'max_previous': max_amount,
                'is_large': is_large_transaction,
                'is_record': is_record_high,
                'alert_type': AlertType.unusual_spending
            }
        
        return None
    
    def create_monthly_summary_alerts(self, db: Session) -> Dict[str, Any]:
        """
        Create monthly summary alerts for all users.
        Run this at the end of each month.
        """
        from app.models.user import User
        from app.crud.transaction import get_transaction_summary
        
        results = {
            'users_processed': 0,
            'alerts_created': 0,
            'summaries': []
        }
        
        # Get all active users
        users = db.query(User).filter(User.is_active == True).all()
        
        # Calculate date range for last month
        today = datetime.utcnow()
        first_day_current_month = today.replace(day=1)
        last_day_previous_month = first_day_current_month - timedelta(days=1)
        first_day_previous_month = last_day_previous_month.replace(day=1)
        
        for user in users:
            results['users_processed'] += 1
            
            # Get monthly summary
            from app.crud import transaction as transaction_crud
            summary = transaction_crud.get_transaction_summary(
                db, user.id, first_day_previous_month, last_day_previous_month
            )
            
            if summary.transaction_count > 0:
                # Create summary message
                month_name = last_day_previous_month.strftime('%B %Y')
                message = (
                    f"Monthly Summary for {month_name}:\n"
                    f"• Total Income: ${summary.total_income:.2f}\n"
                    f"• Total Expenses: ${summary.total_expense:.2f}\n"
                    f"• Net Amount: ${summary.net_amount:.2f}\n"
                    f"• Transactions: {summary.transaction_count}"
                )
                
                # Check if summary alert already exists for this month
                if not alert_crud.check_for_duplicate_alerts(
                    db, user.id, AlertType.monthly_summary, hours_threshold=24*7  # One week
                ):
                    alert = alert_crud.create_alert(
                        db=db,
                        alert={
                            'title': f'Monthly Summary - {month_name}',
                            'message': message,
                            'alert_type': AlertType.monthly_summary,
                            'priority': 'low'
                        },
                        user_id=user.id
                    )
                    
                    results['alerts_created'] += 1
                    results['summaries'].append({
                        'user_id': user.id,
                        'user_email': user.email,
                        'total_income': float(summary.total_income),
                        'total_expense': float(summary.total_expense),
                        'net_amount': float(summary.net_amount),
                        'transaction_count': summary.transaction_count
                    })
        
        return results
    
    def generate_spending_insights(self, db: Session, user_id: int) -> List[Dict[str, Any]]:
        """
        Generate insights about spending patterns and trends.
        """
        insights = []
        
        # Get spending trends for last 3 months
        from app.crud import transaction as transaction_crud
        trends = transaction_crud.get_monthly_trends(db, user_id, months=3)
        
        if len(trends) >= 2:
            # Compare current month vs previous month
            current_month_expenses = [t for t in trends if t['transaction_type'] == 'expense'][-1:]
            previous_month_expenses = [t for t in trends if t['transaction_type'] == 'expense'][-2:-1]
            
            if current_month_expenses and previous_month_expenses:
                current = current_month_expenses[0]['total_amount']
                previous = previous_month_expenses[0]['total_amount']
                
                if previous > 0:
                    change_percent = ((current - previous) / previous) * 100
                    
                    if abs(change_percent) > 20:  # Significant change
                        insights.append({
                            'type': 'spending_trend',
                            'message': (
                                f"Your spending {'increased' if change_percent > 0 else 'decreased'} "
                                f"by {abs(change_percent):.1f}% compared to last month "
                                f"(${current:.2f} vs ${previous:.2f})"
                            ),
                            'change_percent': change_percent,
                            'current_amount': current,
                            'previous_amount': previous
                        })
        
        # Get top spending categories
        spending_by_category = transaction_crud.get_spending_by_category(
            db, user_id, 
            start_date=datetime.utcnow() - timedelta(days=30)
        )
        
        if spending_by_category:
            # Find top spending category
            top_category = max(spending_by_category, key=lambda x: x['total_amount'])
            total_spending = sum(c['total_amount'] for c in spending_by_category)
            
            if total_spending > 0:
                percentage = (top_category['total_amount'] / total_spending) * 100
                
                if percentage > 40:  # If one category dominates
                    insights.append({
                        'type': 'category_dominance',
                        'message': (
                            f"'{top_category['category_name']}' accounts for "
                            f"{percentage:.1f}% of your spending this month "
                            f"(${top_category['total_amount']:.2f})"
                        ),
                        'category': top_category['category_name'],
                        'percentage': percentage,
                        'amount': top_category['total_amount']
                    })
        
        return insights

# Global instance
budget_tracker = BudgetTracker()