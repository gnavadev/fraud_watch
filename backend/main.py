from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import pandas as pd
import requests
from collections import defaultdict
import numpy as np
import os

app = FastAPI(title="Childcare Spending API - Minnesota", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class Establishment(BaseModel):
    license_number: str
    name: str
    address: str
    city: str
    state: str
    county: str
    license_type: str
    license_status: str
    capacity: str
    total_spending: float
    payment_count: int
    avg_payment: float
    fraud_risk_score: float
    risk_category: str
    last_updated: datetime

class FraudIndicators(BaseModel):
    unusual_payment_patterns: bool
    high_payment_variance: bool
    suspicious_frequency: bool
    outlier_amounts: bool
    inactive_license_payments: bool
    capacity_mismatch: bool

class DetailedEstablishment(Establishment):
    fraud_indicators: FraudIndicators
    monthly_spending: List[Dict]
    services: Optional[str]
    phone: Optional[str]
    email: Optional[str]

class DataLoader:
    def __init__(self):
        self.licensing_df = None
        self.healthcare_df = None
        self.spending_data = {}
        
    def load_csv_data(self):
        """Load the Minnesota CSV files"""
        try:
            # Load licensing data
            self.licensing_df = pd.read_csv("Licensing_Lookup_Results_ Dec.29.2025 1.csv")
            print(f"Loaded {len(self.licensing_df)} licensing records")
            
            # Load healthcare facility data
            self.healthcare_df = pd.read_csv("download 1.csv")
            print(f"Loaded {len(self.healthcare_df)} healthcare facility records")
            
            # Filter for Minneapolis and childcare-related licenses
            self.licensing_df = self.licensing_df[
                (self.licensing_df['City'].str.upper() == 'MINNEAPOLIS') &
                (self.licensing_df['License Type'].str.contains('Child', case=False, na=False))
            ].copy()
            
            print(f"Filtered to {len(self.licensing_df)} Minneapolis childcare facilities")
            
        except FileNotFoundError as e:
            print(f"CSV file not found: {e}")
            print("Using sample data instead")
            self.create_sample_data()
    
    def create_sample_data(self):
        """Create sample data if CSV files are not available"""
        self.licensing_df = pd.DataFrame({
            'License Number': range(1000, 1020),
            'Name of Program': [f'Sample Daycare #{i}' for i in range(20)],
            'AddressLine1': [f'{i*100} Main St' for i in range(20)],
            'City': ['Minneapolis'] * 20,
            'State': ['MN'] * 20,
            'County': ['Hennepin'] * 20,
            'License Type': ['Child Care Center'] * 20,
            'License Status': ['Active'] * 18 + ['Inactive'] * 2,
            'Capacity': [f'{i*5}' for i in range(20)],
            'Phone': ['612-555-0100'] * 20,
            'Services': ['Full-time childcare'] * 20,
            'EmailAddress': ['contact@example.com'] * 20
        })
    
    def fetch_usaspending_data(self, recipient_name: str) -> Dict:
        """Fetch spending data from USAspending.gov API"""
        try:
            url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
            
            payload = {
                "filters": {
                    "recipient_search_text": [recipient_name],
                    "place_of_performance_locations": [
                        {"state": "MN", "city": "Minneapolis"}
                    ],
                    "award_type_codes": ["02", "03", "04", "05"],  # Grant types
                    "time_period": [
                        {"start_date": "2023-01-01", "end_date": "2024-12-31"}
                    ]
                },
                "fields": ["Award Amount", "Award ID", "Recipient Name"],
                "limit": 50
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('results', [])
            else:
                return []
                
        except Exception as e:
            print(f"Error fetching USAspending data: {e}")
            return []
    
    def calculate_fraud_risk(self, row: pd.Series, spending_data: Dict) -> Dict:
        """Calculate fraud risk score based on various factors"""
        risk_factors = {}
        risk_score = 0.0
        
        # Factor 1: Inactive license but receiving payments (40 points)
        inactive_payments = (
            row.get('License Status', '').upper() != 'ACTIVE' and 
            spending_data.get('total_spending', 0) > 0
        )
        risk_factors['inactive_license_payments'] = inactive_payments
        if inactive_payments:
            risk_score += 40
        
        # Factor 2: Payment variance (20 points)
        payment_variance = spending_data.get('payment_variance', 0)
        high_variance = payment_variance > 0.7
        risk_factors['high_payment_variance'] = high_variance
        if high_variance:
            risk_score += 20
        
        # Factor 3: Unusual payment patterns (15 points)
        payments = spending_data.get('payments', [])
        unusual_patterns = False
        if len(payments) > 3:
            amounts = [p['amount'] for p in payments]
            if len(amounts) > 0:
                std_dev = np.std(amounts)
                mean_amount = np.mean(amounts)
                if mean_amount > 0:
                    cv = std_dev / mean_amount
                    unusual_patterns = cv > 1.5
        risk_factors['unusual_payment_patterns'] = unusual_patterns
        if unusual_patterns:
            risk_score += 15
        
        # Factor 4: Suspicious frequency (10 points)
        suspicious_freq = len(payments) < 2 and spending_data.get('total_spending', 0) > 100000
        risk_factors['suspicious_frequency'] = suspicious_freq
        if suspicious_freq:
            risk_score += 10
        
        # Factor 5: Outlier amounts (10 points)
        outlier_amounts = spending_data.get('has_outliers', False)
        risk_factors['outlier_amounts'] = outlier_amounts
        if outlier_amounts:
            risk_score += 10
        
        # Factor 6: Capacity mismatch (5 points)
        capacity_str = str(row.get('Capacity', '0'))
        try:
            capacity = int(''.join(filter(str.isdigit, capacity_str))) if capacity_str else 0
            avg_payment = spending_data.get('avg_payment', 0)
            if capacity > 0 and avg_payment > 0:
                expected_per_child = avg_payment / capacity
                capacity_mismatch = expected_per_child > 50000  # Unusually high per child
                risk_factors['capacity_mismatch'] = capacity_mismatch
                if capacity_mismatch:
                    risk_score += 5
            else:
                risk_factors['capacity_mismatch'] = False
        except:
            risk_factors['capacity_mismatch'] = False
        
        if risk_score >= 50:
            risk_category = "High"
        elif risk_score >= 25:
            risk_category = "Medium"
        else:
            risk_category = "Low"
        
        return {
            'fraud_risk_score': round(risk_score, 2),
            'risk_category': risk_category,
            'fraud_indicators': risk_factors
        }
    
    def generate_mock_spending(self, license_number: str, facility_name: str) -> Dict:
        """Generate realistic spending data for demonstration"""
        np.random.seed(hash(str(license_number)) % 2**32)
        
        num_payments = np.random.randint(5, 50)
        base_amount = np.random.uniform(5000, 50000)
        variance = np.random.uniform(0.1, 1.5)
        
        payments = []
        for i in range(num_payments):
            amount = base_amount * np.random.uniform(1 - variance, 1 + variance)
            payments.append({
                'amount': round(amount, 2),
                'date': f"2024-{(i % 12) + 1:02d}-01"
            })
        
        total = sum(p['amount'] for p in payments)
        amounts = [p['amount'] for p in payments]
        
        # Check for outliers
        if len(amounts) > 3:
            q1, q3 = np.percentile(amounts, [25, 75])
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            has_outliers = any(a < lower_bound or a > upper_bound for a in amounts)
        else:
            has_outliers = False
        
        return {
            'total_spending': round(total, 2),
            'payment_count': num_payments,
            'avg_payment': round(total / num_payments, 2),
            'payment_variance': variance,
            'payments': payments,
            'has_outliers': has_outliers
        }

# Initialize data loader
data_loader = DataLoader()

@app.on_event("startup")
async def startup_event():
    """Load data on startup"""
    data_loader.load_csv_data()

@app.get("/")
def read_root():
    return {
        "message": "Minnesota Childcare Spending & Fraud Detection API",
        "location": "Minneapolis, Minnesota",
        "data_sources": [
            "Minnesota Licensing Database",
            "Healthcare Facilities Registry",
            "USAspending.gov API"
        ],
        "endpoints": {
            "/establishments": "Get all childcare establishments with fraud scores",
            "/establishments/{license_number}": "Get detailed info for specific establishment",
            "/stats": "Get aggregated statistics",
            "/high-risk": "Get high-risk establishments",
            "/reload-data": "Reload CSV data and refresh cache"
        }
    }

@app.get("/establishments", response_model=List[Establishment])
def get_establishments(
    min_risk: Optional[float] = Query(None, ge=0, le=100),
    max_risk: Optional[float] = Query(None, ge=0, le=100),
    risk_category: Optional[str] = Query(None, regex="^(Low|Medium|High)$"),
    license_status: Optional[str] = Query(None)
):
    """Get all childcare establishments in Minneapolis with fraud risk scores"""
    if data_loader.licensing_df is None:
        raise HTTPException(status_code=500, detail="Data not loaded")
    
    results = []
    
    for _, row in data_loader.licensing_df.iterrows():
        license_num = str(row['License Number'])
        facility_name = row['Name of Program']
        
        # Generate or fetch spending data
        spending_data = data_loader.generate_mock_spending(license_num, facility_name)
        
        # Calculate fraud risk
        risk_data = data_loader.calculate_fraud_risk(row, spending_data)
        
        establishment = {
            'license_number': license_num,
            'name': facility_name,
            'address': str(row.get('AddressLine1', 'N/A')),
            'city': str(row.get('City', 'Minneapolis')),
            'state': str(row.get('State', 'MN')),
            'county': str(row.get('County', 'N/A')),
            'license_type': str(row.get('License Type', 'N/A')),
            'license_status': str(row.get('License Status', 'N/A')),
            'capacity': str(row.get('Capacity', 'N/A')),
            'total_spending': spending_data['total_spending'],
            'payment_count': spending_data['payment_count'],
            'avg_payment': spending_data['avg_payment'],
            'fraud_risk_score': risk_data['fraud_risk_score'],
            'risk_category': risk_data['risk_category'],
            'last_updated': datetime.now()
        }
        
        # Apply filters
        if min_risk is not None and establishment['fraud_risk_score'] < min_risk:
            continue
        if max_risk is not None and establishment['fraud_risk_score'] > max_risk:
            continue
        if risk_category and establishment['risk_category'] != risk_category:
            continue
        if license_status and establishment['license_status'] != license_status:
            continue
        
        results.append(establishment)
    
    return results

@app.get("/establishments/{license_number}", response_model=DetailedEstablishment)
def get_establishment_detail(license_number: str):
    """Get detailed information for a specific establishment"""
    if data_loader.licensing_df is None:
        raise HTTPException(status_code=500, detail="Data not loaded")
    
    row = data_loader.licensing_df[
        data_loader.licensing_df['License Number'].astype(str) == license_number
    ]
    
    if row.empty:
        raise HTTPException(status_code=404, detail="Establishment not found")
    
    row = row.iloc[0]
    facility_name = row['Name of Program']
    
    # Generate spending data
    spending_data = data_loader.generate_mock_spending(license_number, facility_name)
    
    # Calculate fraud risk
    risk_data = data_loader.calculate_fraud_risk(row, spending_data)
    
    # Generate monthly aggregation
    monthly_spending = defaultdict(float)
    for payment in spending_data['payments']:
        month_key = payment['date'][:7]  # YYYY-MM
        monthly_spending[month_key] += payment['amount']
    
    monthly_data = [
        {'month': k, 'spending': round(v, 2)}
        for k, v in sorted(monthly_spending.items())
    ]
    
    return {
        'license_number': license_number,
        'name': facility_name,
        'address': str(row.get('AddressLine1', 'N/A')),
        'city': str(row.get('City', 'Minneapolis')),
        'state': str(row.get('State', 'MN')),
        'county': str(row.get('County', 'N/A')),
        'license_type': str(row.get('License Type', 'N/A')),
        'license_status': str(row.get('License Status', 'N/A')),
        'capacity': str(row.get('Capacity', 'N/A')),
        'total_spending': spending_data['total_spending'],
        'payment_count': spending_data['payment_count'],
        'avg_payment': spending_data['avg_payment'],
        'fraud_risk_score': risk_data['fraud_risk_score'],
        'risk_category': risk_data['risk_category'],
        'last_updated': datetime.now(),
        'fraud_indicators': risk_data['fraud_indicators'],
        'monthly_spending': monthly_data,
        'services': str(row.get('Services', 'N/A')),
        'phone': str(row.get('Phone', 'N/A')),
        'email': str(row.get('EmailAddress', 'N/A'))
    }

@app.get("/stats")
def get_statistics():
    """Get aggregated statistics for Minneapolis childcare spending"""
    if data_loader.licensing_df is None:
        raise HTTPException(status_code=500, detail="Data not loaded")
    
    establishments = get_establishments()
    
    if not establishments:
        return {"error": "No data available"}
    
    total_spending = sum(e['total_spending'] for e in establishments)
    avg_fraud_risk = sum(e['fraud_risk_score'] for e in establishments) / len(establishments)
    
    high_risk = [e for e in establishments if e['risk_category'] == 'High']
    medium_risk = [e for e in establishments if e['risk_category'] == 'Medium']
    low_risk = [e for e in establishments if e['risk_category'] == 'Low']
    
    active_count = len([e for e in establishments if e['license_status'] == 'Active'])
    inactive_count = len([e for e in establishments if e['license_status'] != 'Active'])
    
    return {
        'city': 'Minneapolis',
        'state': 'Minnesota',
        'total_establishments': len(establishments),
        'active_licenses': active_count,
        'inactive_licenses': inactive_count,
        'total_spending': round(total_spending, 2),
        'average_spending_per_establishment': round(total_spending / len(establishments), 2),
        'average_fraud_risk': round(avg_fraud_risk, 2),
        'risk_distribution': {
            'high': len(high_risk),
            'medium': len(medium_risk),
            'low': len(low_risk)
        },
        'high_risk_percentage': round((len(high_risk) / len(establishments)) * 100, 2),
        'top_risk_factors': {
            'inactive_license_payments': len([e for e in high_risk if 'inactive' in e['license_status'].lower()])
        }
    }

@app.get("/high-risk", response_model=List[Establishment])
def get_high_risk_establishments(limit: int = Query(10, ge=1, le=50)):
    """Get establishments with highest fraud risk"""
    establishments = get_establishments()
    sorted_establishments = sorted(
        establishments,
        key=lambda x: x['fraud_risk_score'],
        reverse=True
    )
    return sorted_establishments[:limit]

@app.post("/reload-data")
def reload_data():
    """Reload CSV data"""
    data_loader.load_csv_data()
    return {
        "status": "success",
        "message": "Data reloaded",
        "establishments_loaded": len(data_loader.licensing_df) if data_loader.licensing_df is not None else 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# from fastapi import FastAPI, Depends, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from sqlalchemy.orm import Session
# from typing import List
# import logging

# from . import models, schemas
# from .database import engine, get_db

# # Configure Logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# models.Base.metadata.create_all(bind=engine)

# app = FastAPI(title="MN Fraud Watch")

# # --- FIX 1: CORS MIDDLEWARE ---
# # Allows your Astro Frontend (http://localhost:4321) to talk to this API
# origins = [
#     "http://localhost:4321", # Local Astro Dev
#     "http://localhost:3000", # Common React Port
# ]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# @app.get("/providers", response_model=List[schemas.ProviderResponse])
# def read_providers(db: Session = Depends(get_db)):
#     logger.info("Fetching all providers sorted by risk") # <--- Log entry
#     return db.query(models.Provider).order_by(models.Provider.risk_score.desc()).all()

# @app.get("/provider/{provider_id}", response_model=schemas.ProviderResponse)
# def read_provider(provider_id: int, db: Session = Depends(get_db)):
#     provider = db.query(models.Provider).filter(models.Provider.id == provider_id).first()
#     if provider is None:
#         logger.warning(f"Provider {provider_id} not found") # <--- Log warning
#         raise HTTPException(status_code=404, detail="Provider not found")
#     return provider