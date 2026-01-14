from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime
import pandas as pd
import numpy as np
import os
import joblib

from backend import models, schemas, fraud_engine
from backend.database import engine, get_db, SessionLocal
from backend.ml.classifier import FraudClassifier

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Childcare Spending API - Minnesota", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load ML model if it exists
ml_model = None
model_path = os.path.join(os.path.dirname(__file__), 'ml', 'model.pkl')
if os.path.exists(model_path):
    try:
        # Note: In a real scenario, we'd load the full FraudClassifier or the pipeline
        ml_model = joblib.load(model_path)
    except:
        pass

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
            "/providers": "Get all childcare providers with fraud scores",
            "/providers/{provider_id}": "Get detailed info for specific provider",
            "/stats": "Get aggregated statistics"
        }
    }

@app.get("/providers", response_model=List[schemas.ProviderResponse])
def get_providers(
    db: Session = Depends(get_db),
    min_risk: Optional[float] = Query(None, ge=0, le=100),
    risk_category: Optional[str] = Query(None, regex="^(Low|Medium|High)$")
):
    """Get all childcare providers in Minneapolis with fraud risk scores"""
    query = db.query(models.Provider)
    
    if min_risk is not None:
        query = query.filter(models.Provider.risk_score >= min_risk)
        
    providers = query.order_by(models.Provider.risk_score.desc()).all()
    
    # Simple manual risk categorization logic for filtering
    if risk_category:
        if risk_category == "High":
            providers = [p for p in providers if p.risk_score >= 50]
        elif risk_category == "Medium":
            providers = [p for p in providers if 25 <= p.risk_score < 50]
        else:
            providers = [p for p in providers if p.risk_score < 25]
            
    return providers

@app.get("/providers/{provider_id}", response_model=schemas.ProviderResponse)
def get_provider_detail(provider_id: int, db: Session = Depends(get_db)):
    """Get detailed information for a specific provider"""
    provider = db.query(models.Provider).filter(models.Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider

@app.get("/stats")
def get_statistics(db: Session = Depends(get_db)):
    """Get aggregated statistics for Minneapolis childcare spending"""
    providers = db.query(models.Provider).all()
    
    if not providers:
        return {"message": "No data available in database."}
    
    total_spending = sum(p.revenue for p in providers)
    avg_risk = sum(p.risk_score for p in providers) / len(providers)
    
    high_risk = [p for p in providers if p.risk_score >= 50]
    
    return {
        'city': 'Minneapolis',
        'total_providers': len(providers),
        'total_revenue_monitored': total_spending,
        'average_fraud_risk': round(avg_risk, 2),
        'high_risk_count': len(high_risk),
        'high_risk_percentage': round((len(high_risk) / len(providers)) * 100, 2)
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