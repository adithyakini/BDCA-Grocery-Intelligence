import os
import re
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from ..database import get_db
from ..models import DealReview, Offer, PriceObservation, Product, Store, utcnow
from ..schemas import OfferCreate, ReviewCreate

router = APIRouter(prefix='/api', tags=['deals'])
SUPPRESSION_DAYS = max(1, int(os.getenv('SUPPRESSION_DAYS', '7')))


def effective_price(offer: Offer) -> float:
    return float(offer.effective_price if offer.effective_price is not None else offer.price)


def canonical_key(name: str, brand: str | None, pack_size: str | None) -> str:
    raw = ' '.join(x for x in [brand or '', name, pack_size or ''] if x)
    return re.sub(r'[^a-z0-9]+', '-', raw.lower()).strip('-')[:240]


def serialize_offer(offer: Offer, db: Session) -> dict:
    latest = db.query(DealReview).filter(DealReview.offer_id == offer.id).order_by(desc(DealReview.decided_at), desc(DealReview.id)).first()
    now = utcnow()
    price = effective_price(offer)
    status = 'PENDING'
    reviewed_at = None
    if latest:
        reviewed_at = latest.decided_at
        within_window = latest.decided_at >= now - timedelta(days=SUPPRESSION_DAYS)
        # An improved effective price is always eligible for a fresh review.
        better_price = price < latest.decision_price - 0.009
        if within_window and not better_price:
            status = latest.status
    return {
        'id': offer.id,
        'product_name': offer.product.name,
        'brand': offer.product.brand,
        'pack_size': offer.product.pack_size,
        'category': offer.product.category,
        'store_name': offer.store.name,
        'price': offer.price,
        'effective_price': offer.effective_price,
        'usual_price': offer.usual_price,
        'product_url': offer.product_url,
        'confidence': offer.confidence or 'Unverified',
        'reason': offer.reason or 'Offer observed; verify final checkout price and eligibility.',
        'expires_at': offer.expires_at,
        'status': status,
        'reviewed_at': reviewed_at,
        'suppressed_until': (latest.decided_at + timedelta(days=SUPPRESSION_DAYS)) if latest and status == latest.status else None,
    }


def upsert_offer(db: Session, payload: OfferCreate) -> tuple[Offer, bool]:
    pkey = canonical_key(payload.product_name, payload.brand, payload.pack_size)
    product = db.query(Product).filter(Product.canonical_key == pkey).first()
    if not product:
        product = Product(canonical_key=pkey, name=payload.product_name.strip(), brand=payload.brand, pack_size=payload.pack_size, category=payload.category)
        db.add(product); db.flush()
    store = db.query(Store).filter(Store.name == payload.store_name.strip()).first()
    if not store:
        store = Store(name=payload.store_name.strip(), source_type=payload.source_type)
        db.add(store); db.flush()
    offer = db.query(Offer).filter(Offer.product_id == product.id, Offer.store_id == store.id, Offer.is_active.is_(True)).first()
    created = offer is None
    if offer is None:
        offer = Offer(product_id=product.id, store_id=store.id, price=payload.price)
        db.add(offer); db.flush()
    offer.product_url = payload.product_url
    offer.price = payload.price
    offer.effective_price = payload.effective_price
    offer.usual_price = payload.usual_price
    offer.confidence = payload.confidence
    offer.reason = payload.reason
    offer.expires_at = payload.expires_at.replace(tzinfo=None) if payload.expires_at and payload.expires_at.tzinfo else payload.expires_at
    offer.updated_at = utcnow()
    db.add(PriceObservation(offer_id=offer.id, observed_price=payload.price, effective_price=payload.effective_price))
    return offer, created


@router.get('/offers')
def list_offers(status: str = Query(default='PENDING', pattern='^(PENDING|ACTIONED|IGNORED|ALL)$'), search: str | None = None, db: Session = Depends(get_db)):
    rows = db.query(Offer).options(joinedload(Offer.product), joinedload(Offer.store)).filter(Offer.is_active.is_(True)).order_by(desc(Offer.updated_at)).all()
    items = [serialize_offer(o, db) for o in rows]
    if status != 'ALL':
        items = [o for o in items if o['status'] == status]
    if search:
        q = search.lower()
        items = [o for o in items if q in ' '.join([o['product_name'], o['brand'] or '', o['store_name'], o['category'] or '']).lower()]
    return {'items': items, 'count': len(items), 'suppression_days': SUPPRESSION_DAYS}


@router.get('/dashboard')
def dashboard(db: Session = Depends(get_db)):
    rows = db.query(Offer).options(joinedload(Offer.product), joinedload(Offer.store)).filter(Offer.is_active.is_(True)).all()
    items = [serialize_offer(o, db) for o in rows]
    actioned = [x for x in items if x['status'] == 'ACTIONED']
    savings = sum(max(0, float(x['usual_price']) - effective_price_obj(x)) for x in actioned if x['usual_price'] is not None)
    return {'pending': sum(x['status'] == 'PENDING' for x in items), 'actioned': len(actioned), 'ignored': sum(x['status'] == 'IGNORED' for x in items), 'potential_savings': round(savings, 2), 'total_active_offers': len(items), 'suppression_days': SUPPRESSION_DAYS}


def effective_price_obj(item: dict) -> float:
    return float(item['effective_price'] if item['effective_price'] is not None else item['price'])


@router.post('/offers')
def create_offer(payload: OfferCreate, db: Session = Depends(get_db)):
    offer, created = upsert_offer(db, payload)
    db.commit(); db.refresh(offer)
    result = serialize_offer(offer, db)
    return {'message': 'Offer created.' if created else 'Offer price refreshed.', 'item': result, 'created': created}


@router.post('/offers/{offer_id}/review')
def review_offer(offer_id: int, payload: ReviewCreate, db: Session = Depends(get_db)):
    offer = db.query(Offer).options(joinedload(Offer.product), joinedload(Offer.store)).filter(Offer.id == offer_id, Offer.is_active.is_(True)).first()
    if not offer:
        raise HTTPException(status_code=404, detail='Offer not found.')
    if payload.status == 'PENDING':
        # An explicit reopen is represented as a pending decision at the current price.
        review = DealReview(offer_id=offer.id, status='PENDING', decision_price=effective_price(offer), note=payload.note)
    else:
        review = DealReview(offer_id=offer.id, status=payload.status, decision_price=effective_price(offer), note=payload.note)
    db.add(review); db.commit(); db.refresh(review)
    return {'message': f'Decision saved: {payload.status}. Similar offers are suppressed for {SUPPRESSION_DAYS} days unless the effective price improves.', 'status': payload.status, 'decided_at': review.decided_at, 'suppressed_until': review.decided_at + timedelta(days=SUPPRESSION_DAYS)}


@router.post('/offers/demo')
def create_demo_offer(db: Session = Depends(get_db)):
    nowstamp = datetime.now(timezone.utc).strftime('%H%M%S')
    payload = OfferCreate(product_name=f'Test discovery {nowstamp}', brand='BDCA Demo', pack_size='1 pack', category='Test offer', store_name='Demo source', price=99, effective_price=99, usual_price=125, confidence='Demo', reason='Sample item to test the review workflow; not a live offer.')
    offer, _ = upsert_offer(db, payload)
    db.commit(); db.refresh(offer)
    return {'message': 'Test suggestion added.', 'item': serialize_offer(offer, db)}
