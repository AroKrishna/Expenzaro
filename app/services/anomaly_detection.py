# app/services/anomaly_detection.py
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from decimal import Decimal
from collections import defaultdict, Counter

from app.models.transaction import Transaction, TransactionType
from app.models.category import Category
from app.crud import transaction as transaction_crud

class AnomalyDetector:
    """
    Anomaly detection service for identifying unusual transactions and potential fraud.
    Uses statistical methods including Z-score analysis, isolation forest concepts,
    and behavioral pattern analysis.
    """
    
    def __init__(self):
        self.min_transactions_for_analysis = 5
        self.z_score_threshold = 2.5  # Standard deviations for outlier detection
        self.high_amount_multiplier = 3.0  # Multiplier of average for "high amount" detection
        self.time_window_days = 30  # Days to look back for pattern analysis
        self.merchant_frequency_threshold = 0.1  # Minimum frequency for merchant pattern analysis
    
    def detect_transaction_anomalies(
        self, 
        db: Session, 
        user_id: int, 
        transaction_id: int
    ) -> Dict[str, Any]:
        """
        Analyze a specific transaction for anomalies.
        
        Args:
            db: Database session
            user_id: User ID
            transaction_id: Transaction to analyze
            
        Returns:
            Dictionary with anomaly analysis results
        """
        # Get the transaction
        transaction = transaction_crud.get_transaction(db, transaction_id, user_id)
        if not transaction:
            return {"error": "Transaction not found"}
        
        # Get historical data for comparison
        historical_data = self._get_historical_data(db, user_id, transaction.category_id)
        
        if len(historical_data) < self.min_transactions_for_analysis:
            return {
                "transaction_id": transaction_id,
                "anomaly_score": 0.0,
                "is_anomaly": False,
                "confidence": 0.0,
                "reason": "Insufficient historical data for analysis",
                "recommendations": []
            }
        
        # Perform multiple anomaly detection checks
        anomaly_checks = {
            "amount_analysis": self._analyze_amount_anomaly(transaction, historical_data),
            "time_analysis": self._analyze_time_anomaly(transaction, historical_data),
            "merchant_analysis": self._analyze_merchant_anomaly(transaction, historical_data),
            "frequency_analysis": self._analyze_frequency_anomaly(transaction, historical_data),
            "pattern_analysis": self._analyze_pattern_anomaly(transaction, historical_data)
        }
        
        # Combine anomaly scores
        overall_score = self._calculate_overall_anomaly_score(anomaly_checks)
        
        # Determine if transaction is anomalous
        is_anomaly = overall_score > 0.7  # Threshold for anomaly classification
        confidence = min(1.0, overall_score * 1.2)  # Confidence in the detection
        
        # Generate recommendations
        recommendations = self._generate_anomaly_recommendations(anomaly_checks, transaction)
        
        return {
            "transaction_id": transaction_id,
            "transaction_amount": float(transaction.amount),
            "transaction_date": transaction.date.isoformat(),
            "transaction_merchant": transaction.merchant,
            "anomaly_score": round(overall_score, 3),
            "is_anomaly": is_anomaly,
            "confidence": round(confidence, 3),
            "detailed_analysis": anomaly_checks,
            "recommendations": recommendations,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
    
    def scan_recent_transactions(
        self, 
        db: Session, 
        user_id: int, 
        days_back: int = 7
    ) -> Dict[str, Any]:
        """
        Scan recent transactions for anomalies.
        """
        start_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Get recent transactions
        from app.schemas.transaction import TransactionFilter
        filters = TransactionFilter(start_date=start_date)
        
        recent_transactions = transaction_crud.get_transactions(
            db, user_id, skip=0, limit=100, filters=filters
        )
        
        anomalies = []
        total_scanned = len(recent_transactions)
        
        for transaction in recent_transactions:
            analysis = self.detect_transaction_anomalies(db, user_id, transaction.id)
            
            if "error" not in analysis and analysis["is_anomaly"]:
                anomalies.append(analysis)
        
        # Sort by anomaly score (highest first)
        anomalies.sort(key=lambda x: x["anomaly_score"], reverse=True)
        
        return {
            "scan_period_days": days_back,
            "total_transactions_scanned": total_scanned,
            "anomalies_detected": len(anomalies),
            "anomaly_rate": round(len(anomalies) / total_scanned * 100, 2) if total_scanned > 0 else 0,
            "anomalies": anomalies,
            "scan_timestamp": datetime.utcnow().isoformat()
        }
    
    def analyze_spending_patterns(
        self, 
        db: Session, 
        user_id: int, 
        analysis_days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze overall spending patterns to identify behavioral anomalies.
        """
        start_date = datetime.utcnow() - timedelta(days=analysis_days)
        
        # Get transaction data
        transactions = transaction_crud.get_transactions(
            db, user_id, skip=0, limit=1000, 
            filters=transaction_crud.TransactionFilter(start_date=start_date)
        )
        
        if len(transactions) < self.min_transactions_for_analysis:
            return {
                "analysis_days": analysis_days,
                "transaction_count": len(transactions),
                "patterns": [],
                "anomalies": [],
                "message": "Insufficient data for pattern analysis"
            }
        
        # Analyze various patterns
        patterns = {
            "daily_spending": self._analyze_daily_spending_pattern(transactions),
            "hourly_patterns": self._analyze_hourly_patterns(transactions),
            "merchant_patterns": self._analyze_merchant_patterns(transactions),
            "category_deviation": self._analyze_category_spending_deviation(transactions),
            "amount_clustering": self._analyze_amount_clustering(transactions)
        }
        
        # Identify pattern-based anomalies
        pattern_anomalies = []
        
        for pattern_type, pattern_data in patterns.items():
            if pattern_data.get("anomalies"):
                pattern_anomalies.extend([
                    {
                        "type": pattern_type,
                        "description": anomaly,
                        "severity": pattern_data.get("severity", "medium")
                    }
                    for anomaly in pattern_data["anomalies"]
                ])
        
        return {
            "analysis_days": analysis_days,
            "transaction_count": len(transactions),
            "patterns": patterns,
            "pattern_anomalies": pattern_anomalies,
            "overall_pattern_health": self._calculate_pattern_health_score(patterns),
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
    
    def detect_fraud_indicators(
        self, 
        db: Session, 
        user_id: int, 
        transaction_id: int
    ) -> Dict[str, Any]:
        """
        Specific fraud detection analysis for a transaction.
        """
        transaction = transaction_crud.get_transaction(db, transaction_id, user_id)
        if not transaction:
            return {"error": "Transaction not found"}
        
        fraud_indicators = []
        risk_score = 0.0
        
        # Check for fraud indicators
        
        # 1. High amount compared to usual spending
        historical_data = self._get_historical_data(db, user_id, transaction.category_id)
        if historical_data:
            avg_amount = sum(historical_data) / len(historical_data)
            if float(transaction.amount) > avg_amount * 5:  # 5x normal amount
                fraud_indicators.append("Unusually high transaction amount")
                risk_score += 0.4
        
        # 2. Multiple transactions in short time period
        recent_transactions = self._get_recent_transactions_same_merchant(
            db, user_id, transaction.merchant, hours=2
        )
        if len(recent_transactions) > 3:
            fraud_indicators.append("Multiple transactions with same merchant in short period")
            risk_score += 0.3
        
        # 3. Unusual timing (very late night transactions)
        hour = transaction.date.hour
        if hour < 3 or hour > 23:  # Very late night
            fraud_indicators.append("Transaction at unusual time (late night/early morning)")
            risk_score += 0.2
        
        # 4. Round number amounts (potential testing)
        amount = float(transaction.amount)
        if amount == round(amount) and amount >= 100:  # Round hundreds
            fraud_indicators.append("Round number amount (potential testing transaction)")
            risk_score += 0.1
        
        # 5. New merchant with high amount
        merchant_history = self._get_merchant_transaction_history(
            db, user_id, transaction.merchant
        )
        if len(merchant_history) == 1 and float(transaction.amount) > 100:
            fraud_indicators.append("First transaction with merchant for significant amount")
            risk_score += 0.3
        
        # 6. Weekend/holiday high spending
        if transaction.date.weekday() >= 5:  # Weekend
            if float(transaction.amount) > avg_amount * 2 if historical_data else 200:
                fraud_indicators.append("High spending during weekend")
                risk_score += 0.1
        
        # Determine risk level
        if risk_score >= 0.8:
            risk_level = "critical"
        elif risk_score >= 0.6:
            risk_level = "high"
        elif risk_score >= 0.4:
            risk_level = "medium"
        elif risk_score >= 0.2:
            risk_level = "low"
        else:
            risk_level = "minimal"
        
        return {
            "transaction_id": transaction_id,
            "fraud_risk_score": round(risk_score, 3),
            "risk_level": risk_level,
            "fraud_indicators": fraud_indicators,
            "requires_review": risk_score >= 0.6,
            "recommended_actions": self._get_fraud_recommendations(risk_level, fraud_indicators),
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
    
    def _get_historical_data(
        self, 
        db: Session, 
        user_id: int, 
        category_id: Optional[int] = None
    ) -> List[float]:
        """Get historical transaction amounts for comparison."""
        # Get transactions from last 90 days
        start_date = datetime.utcnow() - timedelta(days=90)
        
        filters = transaction_crud.TransactionFilter(
            start_date=start_date,
            category_id=category_id,
            transaction_type=TransactionType.expense
        )
        
        transactions = transaction_crud.get_transactions(
            db, user_id, skip=0, limit=500, filters=filters
        )
        
        return [float(t.amount) for t in transactions]
    
    def _analyze_amount_anomaly(
        self, 
        transaction: Transaction, 
        historical_data: List[float]
    ) -> Dict[str, Any]:
        """Analyze if transaction amount is anomalous."""
        if not historical_data:
            return {"score": 0.0, "is_anomalous": False, "reason": "No historical data"}
        
        amount = float(transaction.amount)
        mean_amount = sum(historical_data) / len(historical_data)
        
        # Calculate standard deviation
        variance = sum((x - mean_amount) ** 2 for x in historical_data) / len(historical_data)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            z_score = 0
        else:
            z_score = abs(amount - mean_amount) / std_dev
        
        # Normalize z-score to 0-1 scale
        anomaly_score = min(1.0, z_score / self.z_score_threshold)
        
        return {
            "score": round(anomaly_score, 3),
            "is_anomalous": z_score > self.z_score_threshold,
            "z_score": round(z_score, 2),
            "mean_amount": round(mean_amount, 2),
            "std_deviation": round(std_dev, 2),
            "reason": f"Amount is {z_score:.1f} standard deviations from mean"
        }
    
    def _analyze_time_anomaly(
        self, 
        transaction: Transaction, 
        historical_data: List[float]
    ) -> Dict[str, Any]:
        """Analyze if transaction timing is anomalous."""
        hour = transaction.date.hour
        day_of_week = transaction.date.weekday()
        
        # Simple heuristics for time-based anomalies
        anomaly_score = 0.0
        reasons = []
        
        # Late night transactions (11 PM - 5 AM)
        if hour >= 23 or hour <= 5:
            anomaly_score += 0.3
            reasons.append(f"Late night transaction at {hour:02d}:00")
        
        # Very early morning business transactions
        if 5 < hour < 8 and float(transaction.amount) > 50:
            anomaly_score += 0.2
            reasons.append("Early morning business transaction")
        
        # Weekend large transactions
        if day_of_week >= 5 and float(transaction.amount) > 200:
            anomaly_score += 0.1
            reasons.append("Large weekend transaction")
        
        return {
            "score": round(min(1.0, anomaly_score), 3),
            "is_anomalous": anomaly_score > 0.3,
            "hour": hour,
            "day_of_week": day_of_week,
            "reasons": reasons
        }
    
    def _analyze_merchant_anomaly(
        self, 
        transaction: Transaction, 
        historical_data: List[float]
    ) -> Dict[str, Any]:
        """Analyze merchant-related anomalies."""
        if not transaction.merchant:
            return {"score": 0.0, "is_anomalous": False, "reason": "No merchant data"}
        
        # This is simplified - in a real implementation, you'd track merchant frequency
        # For now, we'll use basic heuristics
        
        anomaly_score = 0.0
        reasons = []
        
        # Check for suspicious merchant names
        suspicious_keywords = ["temp", "test", "unknown", "cash", "atm"]
        merchant_lower = transaction.merchant.lower()
        
        for keyword in suspicious_keywords:
            if keyword in merchant_lower:
                anomaly_score += 0.2
                reasons.append(f"Suspicious merchant keyword: {keyword}")
        
        # Very long merchant names might be suspicious
        if len(transaction.merchant) > 50:
            anomaly_score += 0.1
            reasons.append("Unusually long merchant name")
        
        return {
            "score": round(min(1.0, anomaly_score), 3),
            "is_anomalous": anomaly_score > 0.2,
            "merchant": transaction.merchant,
            "reasons": reasons
        }
    
    def _analyze_frequency_anomaly(
        self, 
        transaction: Transaction, 
        historical_data: List[float]
    ) -> Dict[str, Any]:
        """Analyze transaction frequency patterns."""
        # Simplified frequency analysis
        # In a real implementation, you'd analyze transaction frequency over time
        
        return {
            "score": 0.0,
            "is_anomalous": False,
            "reason": "Frequency analysis not yet implemented"
        }
    
    def _analyze_pattern_anomaly(
        self, 
        transaction: Transaction, 
        historical_data: List[float]
    ) -> Dict[str, Any]:
        """Analyze behavioral pattern anomalies."""
        # Simplified pattern analysis
        
        return {
            "score": 0.0,
            "is_anomalous": False,
            "reason": "Pattern analysis not yet implemented"
        }
    
    def _calculate_overall_anomaly_score(self, anomaly_checks: Dict[str, Dict[str, Any]]) -> float:
        """Calculate weighted overall anomaly score."""
        weights = {
            "amount_analysis": 0.4,
            "time_analysis": 0.2,
            "merchant_analysis": 0.2,
            "frequency_analysis": 0.1,
            "pattern_analysis": 0.1
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for check_type, weight in weights.items():
            if check_type in anomaly_checks:
                score = anomaly_checks[check_type].get("score", 0.0)
                total_score += score * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def _generate_anomaly_recommendations(
        self, 
        anomaly_checks: Dict[str, Dict[str, Any]], 
        transaction: Transaction
    ) -> List[str]:
        """Generate recommendations based on anomaly analysis."""
        recommendations = []
        
        # Amount-based recommendations
        if anomaly_checks.get("amount_analysis", {}).get("is_anomalous"):
            recommendations.append("Verify this large transaction amount")
        
        # Time-based recommendations
        if anomaly_checks.get("time_analysis", {}).get("is_anomalous"):
            recommendations.append("Check if late-night transaction was authorized")
        
        # Merchant-based recommendations
        if anomaly_checks.get("merchant_analysis", {}).get("is_anomalous"):
            recommendations.append("Verify merchant information and transaction legitimacy")
        
        # General recommendations
        if not recommendations:
            recommendations.append("Transaction appears normal based on current analysis")
        
        return recommendations
    
    def _analyze_daily_spending_pattern(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """Analyze daily spending patterns."""
        daily_amounts = defaultdict(float)
        
        for transaction in transactions:
            if transaction.transaction_type == TransactionType.expense:
                date_key = transaction.date.date()
                daily_amounts[date_key] += float(transaction.amount)
        
        amounts = list(daily_amounts.values())
        if not amounts:
            return {"anomalies": [], "pattern": "insufficient_data"}
        
        mean_daily = sum(amounts) / len(amounts)
        
        # Find days with unusually high spending
        anomalies = []
        for date, amount in daily_amounts.items():
            if amount > mean_daily * 3:  # 3x normal daily spending
                anomalies.append(f"High spending day: {date} (${amount:.2f})")
        
        return {
            "pattern": "analyzed",
            "mean_daily_spending": round(mean_daily, 2),
            "anomalies": anomalies,
            "severity": "high" if len(anomalies) > 2 else "medium" if anomalies else "low"
        }
    
    def _analyze_hourly_patterns(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """Analyze hourly transaction patterns."""
        hour_counts = Counter(t.date.hour for t in transactions)
        
        # Find unusual hours (very late night transactions)
        anomalies = []
        late_night_transactions = sum(
            count for hour, count in hour_counts.items()
            if hour >= 23 or hour <= 5
        )
        
        if late_night_transactions > len(transactions) * 0.2:  # More than 20% late night
            anomalies.append(f"{late_night_transactions} late night transactions detected")
        
        return {
            "pattern": "analyzed",
            "hour_distribution": dict(hour_counts),
            "anomalies": anomalies,
            "severity": "medium" if anomalies else "low"
        }
    
    def _analyze_merchant_patterns(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """Analyze merchant spending patterns."""
        merchant_counts = Counter(
            t.merchant for t in transactions 
            if t.merchant and t.transaction_type == TransactionType.expense
        )
        
        anomalies = []
        
        # Check for too many different merchants (might indicate card compromise)
        if len(merchant_counts) > len(transactions) * 0.8:  # Too many unique merchants
            anomalies.append("High number of unique merchants - potential card compromise")
        
        return {
            "pattern": "analyzed",
            "unique_merchants": len(merchant_counts),
            "top_merchants": dict(merchant_counts.most_common(5)),
            "anomalies": anomalies,
            "severity": "high" if "compromise" in str(anomalies) else "low"
        }
    
    def _analyze_category_spending_deviation(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """Analyze category spending deviations."""
        # Simplified category analysis
        return {
            "pattern": "analyzed",
            "anomalies": [],
            "severity": "low"
        }
    
    def _analyze_amount_clustering(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """Analyze amount clustering patterns."""
        amounts = [float(t.amount) for t in transactions if t.transaction_type == TransactionType.expense]
        
        if not amounts:
            return {"pattern": "no_data", "anomalies": []}
        
        # Check for too many round numbers (potential fraud testing)
        round_amounts = sum(1 for amount in amounts if amount == round(amount) and amount >= 10)
        
        anomalies = []
        if round_amounts > len(amounts) * 0.5:  # More than 50% round amounts
            anomalies.append("High frequency of round-number amounts detected")
        
        return {
            "pattern": "analyzed",
            "round_amount_percentage": round(round_amounts / len(amounts) * 100, 1),
            "anomalies": anomalies,
            "severity": "medium" if anomalies else "low"
        }
    
    def _calculate_pattern_health_score(self, patterns: Dict[str, Dict[str, Any]]) -> int:
        """Calculate overall pattern health score (0-100)."""
        base_score = 85
        
        for pattern_data in patterns.values():
            severity = pattern_data.get("severity", "low")
            anomaly_count = len(pattern_data.get("anomalies", []))
            
            if severity == "high":
                base_score -= anomaly_count * 15
            elif severity == "medium":
                base_score -= anomaly_count * 10
            else:
                base_score -= anomaly_count * 5
        
        return max(0, min(100, base_score))
    
    def _get_recent_transactions_same_merchant(
        self, 
        db: Session, 
        user_id: int, 
        merchant: Optional[str], 
        hours: int = 2
    ) -> List[Transaction]:
        """Get recent transactions with the same merchant."""
        if not merchant:
            return []
        
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        filters = transaction_crud.TransactionFilter(
            start_date=start_time,
            merchant=merchant
        )
        
        return transaction_crud.get_transactions(db, user_id, 0, 10, filters)
    
    def _get_merchant_transaction_history(
        self, 
        db: Session, 
        user_id: int, 
        merchant: Optional[str]
    ) -> List[Transaction]:
        """Get all historical transactions with a specific merchant."""
        if not merchant:
            return []
        
        filters = transaction_crud.TransactionFilter(merchant=merchant)
        
        return transaction_crud.get_transactions(db, user_id, 0, 100, filters)
    
    def _get_fraud_recommendations(self, risk_level: str, fraud_indicators: List[str]) -> List[str]:
        """Get recommendations based on fraud risk level."""
        recommendations = []
        
        if risk_level in ["critical", "high"]:
            recommendations.extend([
                "Contact your bank immediately to verify this transaction",
                "Consider freezing your card temporarily",
                "Review your recent account activity carefully"
            ])
        elif risk_level == "medium":
            recommendations.extend([
                "Verify this transaction was authorized by you",
                "Monitor your account for similar transactions"
            ])
        elif risk_level == "low":
            recommendations.append("Keep monitoring your account for unusual activity")
        else:
            recommendations.append("Transaction appears normal")
        
        return recommendations

# Global instance
anomaly_detector = AnomalyDetector()