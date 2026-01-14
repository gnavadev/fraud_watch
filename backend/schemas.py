from pydantic import BaseModel, ConfigDict
from typing import Optional

class ProviderBase(BaseModel):
    license_holder: str
    license_number: str
    city: str
    capacity: int
    revenue: int
    risk_score: float
    status: str
    ein: Optional[str] = None
    address: Optional[str] = None

class ProviderResponse(ProviderBase):
    id: int

    model_config = ConfigDict(from_attributes=True)