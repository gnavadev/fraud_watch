import requests
import csv
import time
import os
import random
from backend.database import SessionLocal
from backend.models import Provider
from backend.fraud_engine import calculate_fraud_risk

def get_minneapolis_child_care(query="child care", city_filter="minneapolis", limit=20):
    """
    Fetches nonprofits in MN matching the query, then filters by city locally.
    Processes fraud risk and saves to database.
    """
    base_url = "https://projects.propublica.org/nonprofits/api/v2/search.json"
    
    params = {
        "q": query,
        "state[id]": "MN",
        "page": 0
    }
    headers = {"User-Agent": "Mozilla/5.0 (Educational Project)"}

    results = []
    db = SessionLocal()
    
    print(f"Searching for '{query}' in {city_filter.title()}, MN...")

    try:
        while len(results) < limit:
            response = requests.get(base_url, params=params, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            orgs = data.get("organizations", [])
            
            if not orgs:
                print("No more pages available from API.")
                break
            
            for org in orgs:
                org_city = org.get("city", "").lower()
                
                if org_city == city_filter.lower():
                    ein = str(org.get("ein"))
                    # Skip if already in DB
                    existing = db.query(Provider).filter(Provider.ein == ein).first()
                    if existing:
                        continue

                    # Mock some additional data for fraud calculation
                    # In a real app, this would come from licensing/spending DBs
                    revenue = float(org.get("revenue", 0) or random.randint(50000, 200000))
                    capacity = random.randint(5, 50)
                    status = random.choice(["Active", "Active", "Active", "Inactive"])
                    
                    # Mock payments for Rule 3, 4, 5
                    num_payments = random.randint(1, 15)
                    payments = []
                    if revenue > 0:
                        base_pay = revenue / num_payments
                        for _ in range(num_payments):
                            payments.append({
                                "amount": base_pay * random.uniform(0.5, 1.5),
                                "date": "2024-01-01"
                            })

                    risk_data = {
                        "revenue": revenue,
                        "capacity": capacity,
                        "status": status,
                        "ein": ein,
                        "payments": payments
                    }
                    
                    risk_score, risk_factors = calculate_fraud_risk(risk_data)

                    provider = Provider(
                        license_holder=org.get("name"),
                        license_number=f"LIC-{ein}", # Mock license number
                        address=org.get("address"),
                        city=org.get("city"),
                        capacity=capacity,
                        ein=ein,
                        revenue=int(revenue),
                        risk_score=risk_score,
                        status=status
                    )
                    
                    db.add(provider)
                    results.append(org.get("name"))
                    
                    if len(results) >= limit:
                        break
            
            print(f"Checked page {params['page']}. Found {len(results)} matches so far.")
            params["page"] += 1
            time.sleep(0.5)

        db.commit()
        print(f"\nSuccess! Saved {len(results)} providers to database.")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    get_minneapolis_child_care()
