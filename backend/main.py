from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import logging

from . import models, schemas
from .database import engine, get_db

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="MN Fraud Watch")

# --- FIX 1: CORS MIDDLEWARE ---
# Allows your Astro Frontend (http://localhost:4321) to talk to this API
origins = [
    "http://localhost:4321", # Local Astro Dev
    "http://localhost:3000", # Common React Port
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/providers", response_model=List[schemas.ProviderResponse])
def read_providers(db: Session = Depends(get_db)):
    logger.info("Fetching all providers sorted by risk") # <--- Log entry
    return db.query(models.Provider).order_by(models.Provider.risk_score.desc()).all()

@app.get("/provider/{provider_id}", response_model=schemas.ProviderResponse)
def read_provider(provider_id: int, db: Session = Depends(get_db)):
    provider = db.query(models.Provider).filter(models.Provider.id == provider_id).first()
    if provider is None:
        logger.warning(f"Provider {provider_id} not found") # <--- Log warning
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider