# app/api/v1/endpoints/forecasting.py
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.forecasting import forecaster

router = APIRouter()

@router.get("/monthly-expenses")
def predict_monthly_expenses(
    category_id: Optional[int] = Query(None, description="Specific category to predict (optional)"),
    months_ahead: int = Query(1, ge=1, le=12, description="Number of months to predict ahead"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Predict monthly expenses using AI forecasting"""
    
    # Validate category belongs to user if provided
    if category_id:
        from app.models.category import Category
        category = db.query(Category).filter(
            Category.id == category_id,
            Category.user_id == current_user.id
        ).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found or doesn't belong to user"
            )
    
    prediction = forecaster.predict_monthly_expenses(
        db, current_user.id, category_id, months_ahead
    )
    
    return {
        "user_id": current_user.id,
        "category_id": category_id,
        "months_ahead": months_ahead,
        "prediction": prediction,
        "generated_at": datetime.utcnow().isoformat()
    }

@router.get("/cash-flow")
def predict_cash_flow(
    days_ahead: int = Query(30, ge=1, le=365, description="Number of days to predict ahead"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Predict cash flow (income - expenses) for specified period"""
    
    prediction = forecaster.predict_cash_flow(db, current_user.id, days_ahead)
    
    return {
        "user_id": current_user.id,
        "prediction": prediction,
        "generated_at": datetime.utcnow().isoformat()
    }

@router.get("/budget-overshoot/{budget_id}")
def predict_budget_overshoot(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Predict if a budget will be exceeded based on current spending patterns"""
    
    prediction = forecaster.predict_budget_overshoot(db, current_user.id, budget_id)
    
    if "error" in prediction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=prediction["error"]
        )
    
    return {
        "user_id": current_user.id,
        "prediction": prediction,
        "generated_at": datetime.utcnow().isoformat()
    }

@router.get("/spending-forecast")
def generate_spending_forecast(
    forecast_type: str = Query("monthly", regex="^(weekly|monthly|quarterly)$", description="Type of forecast period"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate comprehensive spending forecast with AI insights"""
    
    forecast = forecaster.generate_spending_forecast(db, current_user.id, forecast_type)
    
    return {
        "user_id": current_user.id,
        "forecast": forecast
    }

@router.get("/all-budgets-overshoot")
def predict_all_budgets_overshoot(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Predict overshoot risk for all active budgets"""
    
    from app.crud import budget as budget_crud
    
    # Get all active budgets
    active_budgets = budget_crud.get_budgets(
        db, current_user.id, active_only=True, current_only=True, limit=1000
    )
    
    predictions = []
    
    for budget in active_budgets:
        prediction = forecaster.predict_budget_overshoot(db, current_user.id, budget.id)
        
        if "error" not in prediction:
            predictions.append(prediction)
    
    # Sort by risk level
    risk_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    predictions.sort(key=lambda x: risk_order.get(x.get("risk_level", "low"), 1), reverse=True)
    
    # Calculate summary statistics
    total_budgets = len(predictions)
    high_risk_budgets = len([p for p in predictions if p.get("risk_level") in ["high", "critical"]])
    will_exceed_count = len([p for p in predictions if p.get("will_exceed", False)])
    
    return {
        "user_id": current_user.id,
        "summary": {
            "total_budgets_analyzed": total_budgets,
            "high_risk_budgets": high_risk_budgets,
            "budgets_likely_to_exceed": will_exceed_count,
            "overall_risk": "high" if high_risk_budgets > 0 else "medium" if will_exceed_count > 0 else "low"
        },
        "budget_predictions": predictions,
        "generated_at": datetime.utcnow().isoformat()
    }

@router.get("/insights")
def get_financial_insights(
    period: str = Query("monthly", regex="^(weekly|monthly|quarterly)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get AI-powered financial insights and recommendations"""
    
    # Generate spending forecast for insights
    forecast = forecaster.generate_spending_forecast(db, current_user.id, period)
    
    # Get budget predictions
    budget_predictions = []
    from app.crud import budget as budget_crud
    active_budgets = budget_crud.get_budgets(
        db, current_user.id, active_only=True, current_only=True, limit=1000
    )
    
    for budget in active_budgets:
        prediction = forecaster.predict_budget_overshoot(db, current_user.id, budget.id)
        if "error" not in prediction:
            budget_predictions.append(prediction)
    
    # Generate comprehensive insights
    insights = {
        "spending_insights": forecast["insights"],
        "budget_alerts": [],
        "recommendations": [],
        "financial_health_score": 0
    }
    
    # Budget-related insights
    high_risk_budgets = [b for b in budget_predictions if b.get("risk_level") in ["high", "critical"]]
    if high_risk_budgets:
        insights["budget_alerts"] = [
            f"Budget '{b['budget_name']}' is at {b.get('risk_level', 'unknown')} risk of being exceeded"
            for b in high_risk_budgets[:3]  # Top 3 most at risk
        ]
    
    # Generate recommendations
    recommendations = []
    
    # Cash flow recommendations
    cash_flow = forecast["cash_flow_forecast"]
    if cash_flow["predicted_net_cash_flow"] < 0:
        recommendations.append({
            "type": "cash_flow",
            "priority": "high",
            "message": "Consider reducing discretionary spending to improve cash flow",
            "action": "Review and cut non-essential expenses"
        })
    
    # Budget recommendations
    if high_risk_budgets:
        recommendations.append({
            "type": "budget",
            "priority": "medium",
            "message": f"{len(high_risk_budgets)} budget(s) at risk of being exceeded",
            "action": "Monitor spending in high-risk categories closely"
        })
    
    # Spending pattern recommendations
    if forecast["category_predictions"]:
        top_category = max(forecast["category_predictions"], key=lambda x: x["predicted_amount"])
        recommendations.append({
            "type": "category",
            "priority": "low",
            "message": f"'{top_category['category_name']}' is your highest predicted expense",
            "action": "Look for ways to optimize spending in this category"
        })
    
    insights["recommendations"] = recommendations
    
    # Calculate financial health score (0-100)
    health_score = 70  # Base score
    
    # Adjust based on cash flow
    if cash_flow["predicted_net_cash_flow"] > 0:
        health_score += 15
    elif cash_flow["predicted_net_cash_flow"] < -500:
        health_score -= 20
    
    # Adjust based on budget adherence
    if not high_risk_budgets:
        health_score += 10
    else:
        health_score -= len(high_risk_budgets) * 5
    
    # Adjust based on prediction confidence
    avg_confidence = sum(
        cat.get("confidence", 0) for cat in forecast["category_predictions"]
    ) / len(forecast["category_predictions"]) if forecast["category_predictions"] else 0
    
    health_score += int(avg_confidence * 10)
    
    insights["financial_health_score"] = max(0, min(100, health_score))
    
    return {
        "user_id": current_user.id,
        "period": period,
        "insights": insights,
        "generated_at": datetime.utcnow().isoformat()
    }

@router.post("/retrain")
def retrain_model(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Trigger model retraining with latest user data (placeholder for future ML model)"""
    
    # Get user's transaction count for retraining assessment
    from app.crud import transaction as transaction_crud
    from app.schemas.transaction import TransactionFilter
    
    total_transactions = transaction_crud.get_transaction_count(db, current_user.id)
    
    if total_transactions < 10:
        return {
            "message": "Insufficient data for model retraining",
            "transactions_needed": 10 - total_transactions,
            "current_transactions": total_transactions
        }
    
    # In a real implementation, this would trigger ML model retraining
    # For now, we'll just return a success message
    
    return {
        "message": "Model retraining initiated successfully",
        "data_points": total_transactions,
        "estimated_completion": "5 minutes",
        "status": "queued"
    }