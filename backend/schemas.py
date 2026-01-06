from pydantic import BaseModel, ConfigDict
from typing import Optional

class ProviderBase(BaseModel):
    license_holder: str
    license_number: str
    license_type: str
    city: str
    capacity: int
    revenue: int
    risk_score: float
    risk_factors: Optional[str] = None
    status: str

class ProviderResponse(ProviderBase):
    id: int

    model_config = ConfigDict(from_attributes=True)