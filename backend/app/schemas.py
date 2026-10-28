from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field, ConfigDict

class OfferCreate(BaseModel):
    product_name: str = Field(min_length=1, max_length=240)
    brand: Optional[str] = Field(default=None, max_length=120)
    pack_size: Optional[str] = Field(default=None, max_length=100)
    category: Optional[str] = Field(default='Grocery', max_length=100)
    store_name: str = Field(min_length=1, max_length=160)
    price: float = Field(gt=0)
    effective_price: Optional[float] = Field(default=None, gt=0)
    usual_price: Optional[float] = Field(default=None, gt=0)
    product_url: Optional[str] = None
    confidence: str = 'Unverified'
    reason: str = 'Offer observed; verify final checkout price and eligibility.'
    expires_at: Optional[datetime] = None
    source_type: str = 'manual'

class ReviewCreate(BaseModel):
    status: Literal['ACTIONED', 'IGNORED', 'PENDING']
    note: Optional[str] = Field(default=None, max_length=1000)

class OfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_name: str
    brand: Optional[str]
    pack_size: Optional[str]
    category: Optional[str]
    store_name: str
    price: float
    effective_price: Optional[float]
    usual_price: Optional[float]
    product_url: Optional[str]
    confidence: str
    reason: str
    expires_at: Optional[datetime]
    status: str
    reviewed_at: Optional[datetime]
