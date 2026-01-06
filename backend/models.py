# backend/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from .database import Base


class Provider(Base):
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, index=True)

    license_holder = Column(String, index=True)
    license_number = Column(String, unique=True, index=True)
    address = Column(String)
    city = Column(String, index=True)
    capacity = Column(Integer, default=0)

    ein = Column(String, nullable=True)
    revenue = Column(Integer, default=0)

    risk_score = Column(Float, default=0.0)
    status = Column(String, default="Unknown")

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
