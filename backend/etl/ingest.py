import pandas as pd
import requests
import time
import sys
import os
from difflib import SequenceMatcher

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from backend.database import SessionLocal, engine, Base
from backend.models import Provider
from backend.fraud_engine import calculate_fraud_risk

# Constants
CSV_FILE = os.path.join(current_dir, "Licensing_Lookup_Results_ Jan.02.2026.csv")
API_URL = "https://projects.propublica.org/nonprofits/api/v2/search.json"

def get_irs_data(name):
    """Searches ProPublica for EIN and Revenue."""
    clean_name = name.replace("Inc", "").replace("LLC", "").strip()
    try:
        resp = requests.get(API_URL, params={"q": clean_name, "state[id]": "MN"}, timeout=5)
        data = resp.json()
        
        if data["organizations"]:
            org = data["organizations"][0]
            # Match score > 0.6
            score = SequenceMatcher(None, name.lower(), org["name"].lower()).ratio()
            if score > 0.6: 
                return org["ein"], org.get("revenue_amount", 0), "Found"
    except Exception as e:
        print(f"API Error: {e}")
    
    return None, 0, "Not Found"

def run_pipeline():
    print("--- Starting ETL Pipeline ---")
    
    # Init DB
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    
    # Load CSV
    if not os.path.exists(CSV_FILE):
        print(f"Error: CSV file not found at {CSV_FILE}")
        return

    print("Loading CSV...")
    df = pd.read_csv(CSV_FILE)
    df = df[df['City'].str.lower() == 'minneapolis'].copy()
    df['Capacity'] = pd.to_numeric(df['Capacity'], errors='coerce').fillna(0)
    
    # Process Top 20
    top_providers = df.sort_values(by='Capacity', ascending=False).head(20)
    
    print(f"Processing {len(top_providers)} providers...")
    
    for _, row in top_providers.iterrows():
        holder_name = row['License Holder']
        license_num = str(row['License Number'])
        
        if session.query(Provider).filter_by(license_number=license_num).first():
            print(f"Skipping {holder_name} (Already processed)")
            continue

        print(f"Fetching: {holder_name}...", end=" ")
        
        ein, revenue, status = get_irs_data(holder_name)
        
        fraud_data = {
            "revenue": revenue,
            "capacity": int(row['Capacity']),
            "status": status,
            "license_holder": holder_name
        }
        risk_score, risk_factors = calculate_fraud_risk(fraud_data)
        
        provider = Provider(
            license_holder=holder_name,
            license_number=license_num,
            license_type=row['License Type'],
            address=row['AddressLine1'],
            city=row['City'],
            capacity=int(row['Capacity']),
            ein=ein,
            revenue=revenue,
            status=status,
            risk_score=risk_score,
            risk_factors=risk_factors
        )
        session.add(provider)
        print(f"Risk: {risk_score}% | Rev: ${revenue:,}")
        time.sleep(0.2) 

    session.commit()
    print("--- ETL Complete ---")

if __name__ == "__main__":
    run_pipeline()