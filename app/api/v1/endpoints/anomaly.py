# app/api/v1/endpoints/anomaly.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.anomaly_detection import AnomalyDetector

router = APIRouter(prefix="/anomaly", tags=["Anomaly Detection"])

# Initialize anomaly detector
anomaly_detector = AnomalyDetector()

@router.get("/transaction/{transaction_id}")
def analyze_transaction_anomaly(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze a specific transaction for anomalies.
    
    Returns detailed anomaly analysis including:
    - Anomaly score (0-1)
    - Whether transaction is classified as anomalous
    - Confidence level
    - Detailed analysis breakdown
    - Recommendations
    """
    try:
        analysis = anomaly_detector.detect_transaction_anomalies(
            db, current_user.id, transaction_id
        )
        
        if "error" in analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=analysis["error"]
            )
        
        return analysis
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing transaction: {str(e)}"
        )

@router.get("/scan/recent")
def scan_recent_transactions(
    days_back: int = Query(default=7, ge=1, le=30, description="Number of days to scan back"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Scan recent transactions for anomalies.
    
    Parameters:
    - days_back: Number of days to look back (1-30 days)
    
    Returns:
    - Summary of scan results
    - List of detected anomalies
    - Anomaly rate statistics
    """
    try:
        scan_results = anomaly_detector.scan_recent_transactions(
            db, current_user.id, days_back
        )
        return scan_results
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error scanning transactions: {str(e)}"
        )

@router.get("/patterns/analysis")
def analyze_spending_patterns(
    analysis_days: int = Query(default=30, ge=7, le=90, description="Number of days for pattern analysis"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze overall spending patterns to identify behavioral anomalies.
    
    Parameters:
    - analysis_days: Number of days for analysis (7-90 days)
    
    Returns:
    - Spending pattern analysis
    - Pattern-based anomalies
    - Overall pattern health score
    """
    try:
        pattern_analysis = anomaly_detector.analyze_spending_patterns(
            db, current_user.id, analysis_days
        )
        return pattern_analysis
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing patterns: {str(e)}"
        )

@router.get("/fraud/detection/{transaction_id}")
def detect_fraud_indicators(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Specific fraud detection analysis for a transaction.
    
    Returns:
    - Fraud risk score
    - Specific fraud indicators detected
    - Risk level classification
    - Recommended actions
    """
    try:
        fraud_analysis = anomaly_detector.detect_fraud_indicators(
            db, current_user.id, transaction_id
        )
        
        if "error" in fraud_analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=fraud_analysis["error"]
            )
        
        return fraud_analysis
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error detecting fraud: {str(e)}"
        )

@router.get("/dashboard/summary")
def get_anomaly_dashboard_summary(
    days: int = Query(default=7, ge=1, le=30, description="Number of days for summary"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get anomaly detection dashboard summary.
    
    Returns:
    - Recent anomaly statistics
    - Top anomalous transactions
    - Pattern health overview
    - Fraud risk summary
    """
    try:
        # Get recent scan results
        scan_results = anomaly_detector.scan_recent_transactions(db, current_user.id, days)
        
        # Get pattern analysis
        pattern_analysis = anomaly_detector.analyze_spending_patterns(db, current_user.id, days)
        
        # Combine into dashboard summary
        summary = {
            "period_days": days,
            "total_transactions": scan_results["total_transactions_scanned"],
            "anomalies_detected": scan_results["anomalies_detected"],
            "anomaly_rate": scan_results["anomaly_rate"],
            "pattern_health_score": pattern_analysis.get("overall_pattern_health", 0),
            "top_anomalies": scan_results["anomalies"][:5],  # Top 5 anomalies
            "pattern_anomalies_count": len(pattern_analysis.get("pattern_anomalies", [])),
            "fraud_alerts": len([
                a for a in scan_results["anomalies"] 
                if a.get("anomaly_score", 0) > 0.8
            ]),
            "last_updated": scan_results["scan_timestamp"]
        }
        
        return summary
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating dashboard summary: {str(e)}"
        )

@router.get("/settings")
def get_anomaly_detection_settings():
    """
    Get current anomaly detection settings and thresholds.
    """
    return {
        "z_score_threshold": anomaly_detector.z_score_threshold,
        "high_amount_multiplier": anomaly_detector.high_amount_multiplier,
        "time_window_days": anomaly_detector.time_window_days,
        "min_transactions_for_analysis": anomaly_detector.min_transactions_for_analysis,
        "merchant_frequency_threshold": anomaly_detector.merchant_frequency_threshold
    }

@router.put("/settings")
def update_anomaly_detection_settings(
    z_score_threshold: Optional[float] = None,
    high_amount_multiplier: Optional[float] = None,
    time_window_days: Optional[int] = None,
    min_transactions_for_analysis: Optional[int] = None,
    merchant_frequency_threshold: Optional[float] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Update anomaly detection settings (user-specific customization).
    Note: In a production system, these would be stored per user in the database.
    """
    updates = {}
    
    if z_score_threshold is not None:
        if 1.0 <= z_score_threshold <= 5.0:
            anomaly_detector.z_score_threshold = z_score_threshold
            updates["z_score_threshold"] = z_score_threshold
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="z_score_threshold must be between 1.0 and 5.0"
            )
    
    if high_amount_multiplier is not None:
        if 1.5 <= high_amount_multiplier <= 10.0:
            anomaly_detector.high_amount_multiplier = high_amount_multiplier
            updates["high_amount_multiplier"] = high_amount_multiplier
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="high_amount_multiplier must be between 1.5 and 10.0"
            )
    
    if time_window_days is not None:
        if 7 <= time_window_days <= 90:
            anomaly_detector.time_window_days = time_window_days
            updates["time_window_days"] = time_window_days
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="time_window_days must be between 7 and 90"
            )
    
    if min_transactions_for_analysis is not None:
        if 3 <= min_transactions_for_analysis <= 20:
            anomaly_detector.min_transactions_for_analysis = min_transactions_for_analysis
            updates["min_transactions_for_analysis"] = min_transactions_for_analysis
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="min_transactions_for_analysis must be between 3 and 20"
            )
    
    if merchant_frequency_threshold is not None:
        if 0.01 <= merchant_frequency_threshold <= 0.5:
            anomaly_detector.merchant_frequency_threshold = merchant_frequency_threshold
            updates["merchant_frequency_threshold"] = merchant_frequency_threshold
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="merchant_frequency_threshold must be between 0.01 and 0.5"
            )
    
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid settings provided for update"
        )
    
    return {
        "message": "Anomaly detection settings updated successfully",
        "updated_settings": updates,
        "current_settings": {
            "z_score_threshold": anomaly_detector.z_score_threshold,
            "high_amount_multiplier": anomaly_detector.high_amount_multiplier,
            "time_window_days": anomaly_detector.time_window_days,
            "min_transactions_for_analysis": anomaly_detector.min_transactions_for_analysis,
            "merchant_frequency_threshold": anomaly_detector.merchant_frequency_threshold
        }
    }