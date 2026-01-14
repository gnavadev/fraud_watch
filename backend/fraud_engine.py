import numpy as np
from typing import Dict, Tuple, Any, List
import pandas as pd

# Mock list of excluded entities for Rule 1
EXCLUDED_EINS = ["411240047", "999999999"] 

def calculate_fraud_risk(data: Dict[str, Any], ml_model: Any = None) -> Tuple[float, str]:
    """
    Analyzes provider data and returns a probability (0-100) and reasons.
    
    Args:
        data: Dict containing:
            - 'revenue': float
            - 'capacity': int
            - 'status': str (e.g., 'Active', 'Inactive')
            - 'license_holder': str
            - 'payments': List[Dict] with 'amount' and 'date'
            - 'ein': str
        ml_model: Optional trained ML model for additional scoring.
            
    Returns:
        Tuple: (Risk Score Float, Risk Factors String)
    """
    score = 0.0
    factors = []
    
    revenue = data.get('revenue', 0)
    capacity = data.get('capacity', 0)
    status = data.get('status', 'Unknown').lower()
    payments = data.get('payments', [])
    ein = data.get('ein', '')
    
    # 1. Excluded entity receiving payments: +50 points (CRITICAL!)
    if ein in EXCLUDED_EINS and revenue > 0:
        score += 50
        factors.append("CRITICAL: Excluded entity receiving payments")

    # 2. Inactive entity receiving payments: +25 points
    if status != 'active' and revenue > 0:
        score += 25
        factors.append("Inactive entity receiving payments")

    # 3. Suspicious payment frequency (< 3 payments but >$100k): +10 points
    if len(payments) < 3 and revenue > 100_000:
        score += 10
        factors.append("Suspicious payment frequency (High revenue with few payments)")

    # 4. Outlier amounts (IQR method): +5 points
    if len(payments) >= 4:
        amounts = [p['amount'] for p in payments]
        q1, q3 = np.percentile(amounts, [25, 75])
        iqr = q3 - q1
        upper_bound = q3 + 1.5 * iqr
        lower_bound = q1 - 1.5 * iqr
        if any(a > upper_bound or a < lower_bound for a in amounts):
            score += 5
            factors.append("Outlier payment amounts detected (IQR method)")

    # 5. High payment variance (CV > 1.5): +5 points
    if len(payments) > 1:
        amounts = [p['amount'] for p in payments]
        std_dev = np.std(amounts)
        mean_val = np.mean(amounts)
        if mean_val > 0:
            cv = std_dev / mean_val
            if cv > 1.5:
                score += 5
                factors.append(f"High payment variance (CV: {cv:.2f})")

    # ML Integration: Add ML score if model is provided
    if ml_model and len(payments) > 0:
        # Prepare lightweight feature vector for ML
        try:
            # This is a placeholder for actual feature engineering
            features = pd.DataFrame([{
                'revenue': revenue,
                'capacity': capacity,
                'payment_count': len(payments),
                'avg_payment': revenue / len(payments) if payments else 0
            }])
            ml_prob = ml_model.predict_proba(features)[0][1] * 100
            score += ml_prob * 0.2  # ML score contributes 20% to the total points
            if ml_prob > 80:
                factors.append(f"ML Classifier High Risk Flag ({ml_prob:.1f}%)")
        except Exception as e:
            print(f"ML Prediction Error: {e}")

    # Cap score at 100%
    final_score = min(score, 100.0)
    
    return float(final_score), "; ".join(factors)