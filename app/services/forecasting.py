# app/services/forecasting.py
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from decimal import Decimal
from collections import defaultdict

from app.models.transaction import Transaction, TransactionType
from app.models.category import Category
from app.crud import transaction as transaction_crud

class FinancialForecaster:
    """
    AI-powered financial forecasting service using statistical methods and simple ML techniques.
    Provides expense predictions, cash flow forecasting, and spending trend analysis.
    """
    
    def __init__(self):
        self.min_data_points = 3  # Minimum transactions needed for forecasting
        self.default_forecast_days = 30
        self.seasonality_periods = [7, 30, 90]  # Weekly, monthly, quarterly patterns
    
    def predict_monthly_expenses(
        self, 
        db: Session, 
        user_id: int, 
        category_id: Optional[int] = None,
        months_ahead: int = 1
    ) -> Dict[str, Any]:
        """
        Predict monthly expenses using historical data and trend analysis.
        
        Args:
            db: Database session
            user_id: User ID
            category_id: Optional category to focus prediction on
            months_ahead: Number of months to predict ahead
            
        Returns:
            Dictionary with prediction results
        """
        # Get historical data (last 12 months)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=365)
        
        # Get monthly spending data
        monthly_data = self._get_monthly_spending_data(db, user_id, start_date, end_date, category_id)
        
        if len(monthly_data) < self.min_data_points:
            return {
                "prediction": 0.0,
                "confidence": 0.0,
                "trend": "insufficient_data",
                "historical_months": len(monthly_data),
                "message": "Insufficient historical data for accurate prediction"
            }
        
        # Calculate trend and seasonality
        trend_data = self._calculate_trend(monthly_data)
        seasonal_data = self._calculate_seasonality(monthly_data)
        
        # Make prediction
        base_prediction = self._predict_next_period(monthly_data, months_ahead)
        
        # Apply trend adjustment
        trend_adjusted = base_prediction * (1 + trend_data["monthly_growth_rate"] * months_ahead)
        
        # Apply seasonal adjustment
        next_month = (end_date.month + months_ahead - 1) % 12 + 1
        seasonal_factor = seasonal_data.get(next_month, 1.0)
        final_prediction = trend_adjusted * seasonal_factor
        
        # Calculate confidence based on data consistency
        confidence = self._calculate_confidence(monthly_data, trend_data)
        
        return {
            "prediction": round(float(final_prediction), 2),
            "confidence": round(confidence, 2),
            "trend": trend_data["trend_direction"],
            "trend_rate": round(trend_data["monthly_growth_rate"] * 100, 2),
            "seasonal_factor": round(seasonal_factor, 2),
            "historical_months": len(monthly_data),
            "historical_average": round(sum(monthly_data) / len(monthly_data), 2),
            "breakdown": {
                "base_prediction": round(float(base_prediction), 2),
                "trend_adjustment": round(float(trend_adjusted - base_prediction), 2),
                "seasonal_adjustment": round(float(final_prediction - trend_adjusted), 2)
            }
        }
    
    def predict_cash_flow(
        self, 
        db: Session, 
        user_id: int, 
        days_ahead: int = 30
    ) -> Dict[str, Any]:
        """
        Predict cash flow (income - expenses) for the specified period.
        """
        # Get income and expense predictions separately
        income_prediction = self._predict_category_spending(
            db, user_id, TransactionType.income, days_ahead
        )
        expense_prediction = self._predict_category_spending(
            db, user_id, TransactionType.expense, days_ahead
        )
        
        # Calculate net cash flow
        predicted_income = income_prediction["total_predicted"]
        predicted_expenses = expense_prediction["total_predicted"]
        net_cash_flow = predicted_income - predicted_expenses
        
        # Get current balance trend
        current_month_summary = transaction_crud.get_transaction_summary(
            db, user_id, 
            datetime.utcnow().replace(day=1), 
            datetime.utcnow()
        )
        
        current_net = float(current_month_summary.net_amount)
        
        return {
            "period_days": days_ahead,
            "predicted_income": round(predicted_income, 2),
            "predicted_expenses": round(predicted_expenses, 2),
            "predicted_net_cash_flow": round(net_cash_flow, 2),
            "current_month_net": round(current_net, 2),
            "cash_flow_trend": "positive" if net_cash_flow > 0 else "negative",
            "income_breakdown": income_prediction["category_breakdown"],
            "expense_breakdown": expense_prediction["category_breakdown"],
            "confidence": {
                "income": income_prediction["confidence"],
                "expenses": expense_prediction["confidence"],
                "overall": round((income_prediction["confidence"] + expense_prediction["confidence"]) / 2, 2)
            }
        }
    
    def predict_budget_overshoot(
        self, 
        db: Session, 
        user_id: int, 
        budget_id: int
    ) -> Dict[str, Any]:
        """
        Predict if a budget will be exceeded based on current spending patterns.
        """
        from app.crud import budget as budget_crud
        
        # Get budget information
        budget = budget_crud.get_budget(db, budget_id, user_id)
        if not budget:
            return {"error": "Budget not found"}
        
        # Get current progress
        progress = budget_crud.get_budget_progress(db, budget_id, user_id)
        if not progress:
            return {"error": "Cannot calculate budget progress"}
        
        # Calculate remaining days in budget period
        remaining_days = max(0, (budget.end_date - datetime.utcnow()).days)
        
        if remaining_days == 0:
            return {
                "budget_id": budget_id,
                "budget_name": budget.name,
                "prediction": "period_ended",
                "current_usage": round(progress.percentage_used, 2),
                "is_exceeded": progress.is_exceeded
            }
        
        # Get daily spending rate for this category
        days_elapsed = (datetime.utcnow() - budget.start_date).days + 1
        daily_avg_spending = float(progress.spent_amount) / days_elapsed if days_elapsed > 0 else 0
        
        # Predict spending for remaining period
        predicted_additional_spending = daily_avg_spending * remaining_days
        predicted_total_spending = float(progress.spent_amount) + predicted_additional_spending
        
        # Calculate overshoot probability
        overshoot_amount = max(0, predicted_total_spending - float(budget.limit_amount))
        overshoot_percentage = (predicted_total_spending / float(budget.limit_amount)) * 100
        
        # Determine risk level
        if overshoot_percentage < 80:
            risk_level = "low"
        elif overshoot_percentage < 100:
            risk_level = "medium"
        elif overshoot_percentage < 120:
            risk_level = "high"
        else:
            risk_level = "critical"
        
        return {
            "budget_id": budget_id,
            "budget_name": budget.name,
            "budget_limit": float(budget.limit_amount),
            "current_spent": float(progress.spent_amount),
            "current_usage_percentage": round(progress.percentage_used, 2),
            "remaining_days": remaining_days,
            "daily_average_spending": round(daily_avg_spending, 2),
            "predicted_total_spending": round(predicted_total_spending, 2),
            "predicted_usage_percentage": round(overshoot_percentage, 2),
            "predicted_overshoot": round(overshoot_amount, 2),
            "risk_level": risk_level,
            "will_exceed": predicted_total_spending > float(budget.limit_amount),
            "days_until_exceeded": self._calculate_days_until_exceeded(
                float(progress.spent_amount), 
                float(budget.limit_amount), 
                daily_avg_spending
            ) if daily_avg_spending > 0 else None
        }
    
    def generate_spending_forecast(
        self, 
        db: Session, 
        user_id: int, 
        forecast_type: str = "monthly"
    ) -> Dict[str, Any]:
        """
        Generate comprehensive spending forecast with insights.
        """
        if forecast_type == "monthly":
            days_ahead = 30
        elif forecast_type == "weekly":
            days_ahead = 7
        elif forecast_type == "quarterly":
            days_ahead = 90
        else:
            days_ahead = 30
        
        # Get predictions by category
        category_predictions = self._predict_by_category(db, user_id, days_ahead)
        
        # Get cash flow prediction
        cash_flow = self.predict_cash_flow(db, user_id, days_ahead)
        
        # Generate insights
        insights = self._generate_insights(db, user_id, category_predictions, cash_flow)
        
        return {
            "forecast_type": forecast_type,
            "period_days": days_ahead,
            "total_predicted_expenses": sum(cat["predicted_amount"] for cat in category_predictions),
            "category_predictions": category_predictions,
            "cash_flow_forecast": cash_flow,
            "insights": insights,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _get_monthly_spending_data(
        self, 
        db: Session, 
        user_id: int, 
        start_date: datetime, 
        end_date: datetime,
        category_id: Optional[int] = None
    ) -> List[float]:
        """Get monthly spending amounts for the specified period."""
        monthly_trends = transaction_crud.get_monthly_trends(db, user_id, 12)
        
        # Filter by category if specified
        if category_id:
            # Get category-specific data
            spending_data = transaction_crud.get_spending_by_category(
                db, user_id, start_date, end_date
            )
            # This is a simplified approach - in a real implementation,
            # you'd want month-by-month category data
            return [item["total_amount"] for item in spending_data if item.get("category_id") == category_id]
        
        # Get expense data only
        expense_data = [
            trend["total_amount"] 
            for trend in monthly_trends 
            if trend["transaction_type"] == "expense"
        ]
        
        return expense_data[-12:]  # Last 12 months
    
    def _calculate_trend(self, data: List[float]) -> Dict[str, Any]:
        """Calculate trend direction and growth rate using linear regression."""
        if len(data) < 2:
            return {"trend_direction": "stable", "monthly_growth_rate": 0.0}
        
        n = len(data)
        x_values = list(range(n))
        
        # Simple linear regression
        x_mean = sum(x_values) / n
        y_mean = sum(data) / n
        
        numerator = sum((x_values[i] - x_mean) * (data[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # Convert slope to monthly growth rate
        monthly_growth_rate = slope / y_mean if y_mean != 0 else 0
        
        if monthly_growth_rate > 0.05:  # More than 5% growth
            trend_direction = "increasing"
        elif monthly_growth_rate < -0.05:  # More than 5% decline
            trend_direction = "decreasing"
        else:
            trend_direction = "stable"
        
        return {
            "trend_direction": trend_direction,
            "monthly_growth_rate": monthly_growth_rate
        }
    
    def _calculate_seasonality(self, data: List[float]) -> Dict[int, float]:
        """Calculate seasonal factors for each month."""
        if len(data) < 12:
            return {i: 1.0 for i in range(1, 13)}
        
        # Group by month and calculate average factor
        monthly_averages = defaultdict(list)
        overall_average = sum(data) / len(data)
        
        for i, value in enumerate(data):
            month = (i % 12) + 1
            monthly_averages[month].append(value)
        
        seasonal_factors = {}
        for month in range(1, 13):
            if month in monthly_averages and monthly_averages[month]:
                month_avg = sum(monthly_averages[month]) / len(monthly_averages[month])
                seasonal_factors[month] = month_avg / overall_average if overall_average > 0 else 1.0
            else:
                seasonal_factors[month] = 1.0
        
        return seasonal_factors
    
    def _predict_next_period(self, data: List[float], periods_ahead: int = 1) -> float:
        """Predict next period using exponential smoothing."""
        if not data:
            return 0.0
        
        if len(data) == 1:
            return data[0]
        
        # Exponential smoothing with alpha = 0.3
        alpha = 0.3
        smoothed = data[0]
        
        for value in data[1:]:
            smoothed = alpha * value + (1 - alpha) * smoothed
        
        return smoothed
    
    def _calculate_confidence(self, data: List[float], trend_data: Dict[str, Any]) -> float:
        """Calculate prediction confidence based on data consistency."""
        if len(data) < 2:
            return 0.2
        
        # Calculate coefficient of variation
        mean_val = sum(data) / len(data)
        variance = sum((x - mean_val) ** 2 for x in data) / len(data)
        std_dev = math.sqrt(variance)
        
        if mean_val == 0:
            return 0.2
        
        cv = std_dev / mean_val
        
        # Lower coefficient of variation = higher confidence
        base_confidence = max(0.1, 1.0 - cv)
        
        # Adjust based on data quantity
        data_factor = min(1.0, len(data) / 12)  # Full confidence with 12+ months
        
        # Adjust based on trend stability
        trend_factor = 1.0 if trend_data["trend_direction"] == "stable" else 0.9
        
        return min(1.0, base_confidence * data_factor * trend_factor)
    
    def _predict_category_spending(
        self, 
        db: Session, 
        user_id: int, 
        transaction_type: TransactionType, 
        days_ahead: int
    ) -> Dict[str, Any]:
        """Predict spending by category for the specified period."""
        # Get spending by category for last 3 months
        start_date = datetime.utcnow() - timedelta(days=90)
        end_date = datetime.utcnow()
        
        category_spending = transaction_crud.get_spending_by_category(
            db, user_id, start_date, end_date
        )
        
        # Filter by transaction type
        filtered_spending = [
            cat for cat in category_spending 
            if cat["category_type"] == transaction_type.value
        ]
        
        total_predicted = 0.0
        category_breakdown = []
        confidence_scores = []
        
        for category in filtered_spending:
            # Calculate daily average for this category
            daily_avg = category["total_amount"] / 90  # 90 days
            predicted_amount = daily_avg * days_ahead
            
            # Simple confidence calculation based on transaction count
            confidence = min(1.0, category["transaction_count"] / 10)
            confidence_scores.append(confidence)
            
            category_breakdown.append({
                "category_name": category["category_name"],
                "historical_total": category["total_amount"],
                "daily_average": round(daily_avg, 2),
                "predicted_amount": round(predicted_amount, 2),
                "confidence": round(confidence, 2)
            })
            
            total_predicted += predicted_amount
        
        overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        return {
            "total_predicted": total_predicted,
            "confidence": round(overall_confidence, 2),
            "category_breakdown": category_breakdown
        }
    
    def _predict_by_category(self, db: Session, user_id: int, days_ahead: int) -> List[Dict[str, Any]]:
        """Generate predictions for each spending category."""
        expense_prediction = self._predict_category_spending(
            db, user_id, TransactionType.expense, days_ahead
        )
        
        return expense_prediction["category_breakdown"]
    
    def _generate_insights(
        self, 
        db: Session, 
        user_id: int, 
        category_predictions: List[Dict[str, Any]], 
        cash_flow: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable insights based on predictions."""
        insights = []
        
        # Cash flow insights
        if cash_flow["predicted_net_cash_flow"] < 0:
            insights.append(
                f"Warning: Predicted negative cash flow of ${abs(cash_flow['predicted_net_cash_flow']):.2f}. "
                "Consider reducing expenses or increasing income."
            )
        elif cash_flow["predicted_net_cash_flow"] > cash_flow["current_month_net"] * 1.2:
            insights.append(
                "Great news! Your cash flow is improving. Consider increasing your savings or investments."
            )
        
        # Category insights
        if category_predictions:
            highest_category = max(category_predictions, key=lambda x: x["predicted_amount"])
            insights.append(
                f"Your highest predicted expense category is '{highest_category['category_name']}' "
                f"at ${highest_category['predicted_amount']:.2f}."
            )
            
            # Low confidence warnings
            low_confidence_cats = [
                cat for cat in category_predictions 
                if cat["confidence"] < 0.5
            ]
            
            if low_confidence_cats:
                insights.append(
                    f"Predictions for {len(low_confidence_cats)} categories have low confidence due to limited data. "
                    "Add more transactions for better forecasting."
                )
        
        return insights
    
    def _calculate_days_until_exceeded(
        self, 
        current_spent: float, 
        budget_limit: float, 
        daily_spending: float
    ) -> Optional[int]:
        """Calculate how many days until budget is exceeded at current rate."""
        if daily_spending <= 0:
            return None
        
        remaining_budget = budget_limit - current_spent
        if remaining_budget <= 0:
            return 0
        
        return int(remaining_budget / daily_spending)

# Global instance
forecaster = FinancialForecaster()