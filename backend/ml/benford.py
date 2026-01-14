import numpy as np
import pandas as pd

def get_leading_digit(number):
    """Extracts the first non-zero digit from a transaction amount."""
    try:
        s = str(abs(number))
        s = s.replace('.', '')
        for char in s:
            if char in '123456789':
                return int(char)
        return 0
    except:
        return 0

def calculate_benford_deviation(df: pd.DataFrame, column_name='amount'):
    """
    Analyzes transaction amounts against Benford's Law.
    Returns a DataFrame with the deviation for each digit (1-9).
    """
    # 1. Extract leading digits
    df['leading_digit'] = df[column_name].apply(get_leading_digit)
    
    # 2. Filter valid digits
    valid_digits = df[df['leading_digit'] > 0]
    total_count = len(valid_digits)
    
    if total_count == 0:
        return None

    # 3. Calculate actual frequencies
    actual_counts = valid_digits['leading_digit'].value_counts().sort_index()
    actual_freq = actual_counts / total_count
    
    # 4. Calculate Theoretical Benford Frequencies: P(d) = log10(1 + 1/d)
    digits = np.arange(1, 10)
    benford_freq = np.log10(1 + 1 / digits)
    
    # 5. Compare
    results = pd.DataFrame({
        'digit': digits,
        'actual_freq': actual_freq.reindex(digits, fill_value=0).values,
        'benford_freq': benford_freq
    })
    
    # Calculate anomaly score (Euclidean distance or simple difference)
    results['diff'] = np.abs(results['actual_freq'] - results['benford_freq'])
    
    # Flag significant deviations (> 5%)
    results['is_anomaly'] = results['diff'] > 0.05
    
    return results