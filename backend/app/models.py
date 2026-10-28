from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Product(Base):
    __tablename__ = 'products'
    id = __import__('sqlalchemy').Column(Integer, primary_key=True, index=True)
    canonical_key = __import__('sqlalchemy').Column(String(240), unique=True, nullable=False, index=True)
    name = __import__('sqlalchemy').Column(String(240), nullable=False)
    brand = __import__('sqlalchemy').Column(String(120), nullable=True)
    pack_size = __import__('sqlalchemy').Column(String(100), nullable=True)
    category = __import__('sqlalchemy').Column(String(100), nullable=True)
    created_at = __import__('sqlalchemy').Column(DateTime, default=utcnow, nullable=False)
    offers = relationship('Offer', back_populates='product', cascade='all, delete-orphan')

class Store(Base):
    __tablename__ = 'stores'
    id = __import__('sqlalchemy').Column(Integer, primary_key=True, index=True)
    name = __import__('sqlalchemy').Column(String(160), unique=True, nullable=False)
    source_type = __import__('sqlalchemy').Column(String(80), default='manual', nullable=False)
    offers = relationship('Offer', back_populates='store')

class Offer(Base):
    __tablename__ = 'offers'
    id = __import__('sqlalchemy').Column(Integer, primary_key=True, index=True)
    product_id = __import__('sqlalchemy').Column(Integer, ForeignKey('products.id'), nullable=False, index=True)
    store_id = __import__('sqlalchemy').Column(Integer, ForeignKey('stores.id'), nullable=False, index=True)
    product_url = __import__('sqlalchemy').Column(Text, nullable=True)
    price = __import__('sqlalchemy').Column(Float, nullable=False)
    effective_price = __import__('sqlalchemy').Column(Float, nullable=True)
    usual_price = __import__('sqlalchemy').Column(Float, nullable=True)
    confidence = __import__('sqlalchemy').Column(String(40), default='Unverified')
    reason = __import__('sqlalchemy').Column(Text, default='Offer observed; verify final checkout price and eligibility.')
    expires_at = __import__('sqlalchemy').Column(DateTime, nullable=True)
    is_active = __import__('sqlalchemy').Column(Boolean, default=True, nullable=False)
    created_at = __import__('sqlalchemy').Column(DateTime, default=utcnow, nullable=False)
    updated_at = __import__('sqlalchemy').Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    product = relationship('Product', back_populates='offers')
    store = relationship('Store', back_populates='offers')
    reviews = relationship('DealReview', back_populates='offer', cascade='all, delete-orphan')
    __table_args__ = (Index('ix_offer_product_store_active', 'product_id', 'store_id', 'is_active'),)

class DealReview(Base):
    __tablename__ = 'deal_reviews'
    id = __import__('sqlalchemy').Column(Integer, primary_key=True, index=True)
    offer_id = __import__('sqlalchemy').Column(Integer, ForeignKey('offers.id'), nullable=False, index=True)
    status = __import__('sqlalchemy').Column(String(20), nullable=False)
    decision_price = __import__('sqlalchemy').Column(Float, nullable=False)
    note = __import__('sqlalchemy').Column(Text, nullable=True)
    decided_at = __import__('sqlalchemy').Column(DateTime, default=utcnow, nullable=False, index=True)
    offer = relationship('Offer', back_populates='reviews')

class PriceObservation(Base):
    __tablename__ = 'price_history'
    id = __import__('sqlalchemy').Column(Integer, primary_key=True, index=True)
    offer_id = __import__('sqlalchemy').Column(Integer, ForeignKey('offers.id'), nullable=False, index=True)
    observed_price = __import__('sqlalchemy').Column(Float, nullable=False)
    effective_price = __import__('sqlalchemy').Column(Float, nullable=True)
    observed_at = __import__('sqlalchemy').Column(DateTime, default=utcnow, nullable=False, index=True)


class DiscoverySource(Base):
    __tablename__ = 'discovery_sources'
    id = __import__('sqlalchemy').Column(Integer, primary_key=True, index=True)
    name = __import__('sqlalchemy').Column(String(160), nullable=False)
    feed_url = __import__('sqlalchemy').Column(Text, unique=True, nullable=False)
    source_type = __import__('sqlalchemy').Column(String(40), default='rss', nullable=False)
    enabled = __import__('sqlalchemy').Column(Boolean, default=True, nullable=False)
    last_scanned_at = __import__('sqlalchemy').Column(DateTime, nullable=True)
    last_result = __import__('sqlalchemy').Column(String(240), nullable=True)
    created_at = __import__('sqlalchemy').Column(DateTime, default=utcnow, nullable=False)

class WatchlistItem(Base):
    __tablename__ = 'watchlist_items'
    id = __import__('sqlalchemy').Column(Integer, primary_key=True, index=True)
    query = __import__('sqlalchemy').Column(String(240), unique=True, nullable=False)
    category = __import__('sqlalchemy').Column(String(100), nullable=True)
    target_price = __import__('sqlalchemy').Column(Float, nullable=True)
    enabled = __import__('sqlalchemy').Column(Boolean, default=True, nullable=False)
    created_at = __import__('sqlalchemy').Column(DateTime, default=utcnow, nullable=False)

class DiscoveryRun(Base):
    __tablename__ = 'discovery_runs'
    id = __import__('sqlalchemy').Column(Integer, primary_key=True, index=True)
    started_at = __import__('sqlalchemy').Column(DateTime, default=utcnow, nullable=False)
    finished_at = __import__('sqlalchemy').Column(DateTime, nullable=True)
    status = __import__('sqlalchemy').Column(String(30), default='RUNNING', nullable=False)
    sources_checked = __import__('sqlalchemy').Column(Integer, default=0, nullable=False)
    entries_examined = __import__('sqlalchemy').Column(Integer, default=0, nullable=False)
    candidates_found = __import__('sqlalchemy').Column(Integer, default=0, nullable=False)
    offers_created = __import__('sqlalchemy').Column(Integer, default=0, nullable=False)
    message = __import__('sqlalchemy').Column(Text, nullable=True)
