from typing import Dict, Tuple, Any

def calculate_fraud_risk(data: Dict[str, Any]) -> Tuple[float, str]:
    """
    Analyzes provider data and returns a probability (0-100) and reasons.
    
    Args:
        data: Dict containing 'revenue', 'capacity', 'status', 'license_type', 'license_holder'
        
    Returns:
        Tuple: (Risk Score Float, Risk Factors String)
    """
    score = 0.0
    factors = []
    
    revenue = data.get('revenue', 0)
    capacity = data.get('capacity', 0)
    status = data.get('status', 'Unknown')
    # license_type = data.get('license_type', '') # Reserved for future logic

    # Scenario: A center claiming $500k revenue but only has space for 2 kids.
    if revenue > 500_000 and capacity < 3:
        score += 40
        factors.append("High Revenue / Low Capacity Anomaly")

    # Scenario: Laundering money by inflating cost per child.
    if capacity > 0:
        per_capita = revenue / capacity
        # Threshold: >$100k per child is suspicious (Avg is ~$15k)
        if per_capita > 100_000:
            score += 30
            factors.append(f"Excessive Per-Capita Spending (${int(per_capita):,}/person)")

    # Scenario: A corporate entity ("Inc") that doesn't exist in IRS records.
    if status.startswith("Not Found") and "Inc" in data.get('license_holder', ''):
        score += 15
        factors.append("Corporate Entity Missing IRS Filings")

    # Cap score at 100%
    final_score = min(score, 100.0)
    
    return final_score, "; ".join(factors)