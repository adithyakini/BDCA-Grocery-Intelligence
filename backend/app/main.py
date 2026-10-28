import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine, SessionLocal
from . import models
from .routers.deals import router, upsert_offer
from .schemas import OfferCreate

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # Seed a few clearly-labelled demo records on first launch only.
    db = SessionLocal()
    try:
        if db.query(models.Offer).count() == 0:
            samples = [
                OfferCreate(product_name='Tata Sampann Toor Dal', brand='Tata Sampann', pack_size='1 kg', category='Pantry', store_name='Example Store A', price=129, effective_price=129, usual_price=165, confidence='Demo', reason='Demo only: illustrative saving versus usual price.'),
                OfferCreate(product_name='Aashirvaad Atta', brand='Aashirvaad', pack_size='5 kg', category='Pantry', store_name='Example Store B', price=219, effective_price=219, usual_price=260, confidence='Demo', reason='Demo only: illustrative unit-price saving.'),
                OfferCreate(product_name='Fortune Sunflower Oil', brand='Fortune', pack_size='1 L', category='Cooking oil', store_name='Example Store A', price=112, effective_price=112, usual_price=145, confidence='Demo', reason='Demo only: verify final checkout price and coupon eligibility.'),
                OfferCreate(product_name='Amul Butter', brand='Amul', pack_size='500 g', category='Dairy', store_name='Example Store C', price=245, effective_price=245, usual_price=275, confidence='Demo', reason='Demo only: illustrative offer.'),
                OfferCreate(product_name='Surf Excel Detergent', brand='Surf Excel', pack_size='2 kg', category='Home care', store_name='Example Store B', price=299, effective_price=299, usual_price=380, confidence='Demo', reason='Demo only: illustrative saving versus usual price.'),
            ]
            for sample in samples:
                upsert_offer(db, sample)
            db.commit()
    finally:
        db.close()
    yield

app = FastAPI(title='BDCA Grocery Intelligence API', version='0.1.0', lifespan=lifespan, description='Personal grocery deal review queue and price suppression API.')
origins = [x.strip() for x in os.getenv('FRONTEND_URL', 'http://localhost:5173').split(',') if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
app.include_router(router)

@app.get('/api/health')
def health():
    return {'status': 'ok', 'service': 'bdca-grocery-intelligence-api'}

@app.get('/')
def root():
    return {'name': 'BDCA Grocery Intelligence API', 'docs': '/docs', 'health': '/api/health'}
