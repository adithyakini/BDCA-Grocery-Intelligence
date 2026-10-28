from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..database import get_db
from ..models import DiscoveryRun, DiscoverySource, WatchlistItem
from ..schemas import DiscoverySourceCreate, WatchlistCreate
from ..services.discovery import discover_from_sources

router = APIRouter(prefix='/api/discovery', tags=['discovery'])

def source_out(s):
    return {'id':s.id,'name':s.name,'feed_url':s.feed_url,'source_type':s.source_type,'enabled':s.enabled,'last_scanned_at':s.last_scanned_at,'last_result':s.last_result}
def watch_out(w):
    return {'id':w.id,'query':w.query,'category':w.category,'target_price':w.target_price,'enabled':w.enabled}
def run_out(r):
    return {'id':r.id,'started_at':r.started_at,'finished_at':r.finished_at,'status':r.status,'sources_checked':r.sources_checked,'entries_examined':r.entries_examined,'candidates_found':r.candidates_found,'offers_created':r.offers_created,'message':r.message}

@router.get('/overview')
def overview(db: Session = Depends(get_db)):
    sources=db.query(DiscoverySource).order_by(DiscoverySource.created_at.desc()).all()
    watch=db.query(WatchlistItem).order_by(WatchlistItem.created_at.desc()).all()
    runs=db.query(DiscoveryRun).order_by(DiscoveryRun.started_at.desc()).limit(10).all()
    return {'sources':[source_out(x) for x in sources],'watchlist':[watch_out(x) for x in watch],'runs':[run_out(x) for x in runs]}

@router.post('/sources')
def add_source(payload: DiscoverySourceCreate, db: Session = Depends(get_db)):
    url=payload.feed_url.strip()
    if not url.lower().startswith(('http://','https://')):
        raise HTTPException(status_code=400,detail='Feed URL must start with http:// or https://')
    existing=db.query(DiscoverySource).filter(DiscoverySource.feed_url==url).first()
    if existing: raise HTTPException(status_code=409,detail='This feed URL is already configured.')
    source=DiscoverySource(name=payload.name.strip(),feed_url=url,source_type='rss',enabled=True)
    db.add(source); db.commit(); db.refresh(source)
    return {'item':source_out(source),'message':'Public feed source added.'}

@router.delete('/sources/{source_id}')
def delete_source(source_id: int, db: Session = Depends(get_db)):
    source=db.query(DiscoverySource).filter(DiscoverySource.id==source_id).first()
    if not source: raise HTTPException(status_code=404,detail='Source not found.')
    db.delete(source); db.commit(); return {'message':'Source removed.'}

@router.post('/watchlist')
def add_watchlist(payload: WatchlistCreate, db: Session = Depends(get_db)):
    query=payload.query.strip()
    existing=db.query(WatchlistItem).filter(WatchlistItem.query.ilike(query)).first()
    if existing: raise HTTPException(status_code=409,detail='That watchlist query already exists.')
    item=WatchlistItem(query=query,category=payload.category,target_price=payload.target_price,enabled=True)
    db.add(item); db.commit(); db.refresh(item)
    return {'item':watch_out(item),'message':'Watchlist item added.'}

@router.delete('/watchlist/{item_id}')
def delete_watchlist(item_id: int, db: Session = Depends(get_db)):
    item=db.query(WatchlistItem).filter(WatchlistItem.id==item_id).first()
    if not item: raise HTTPException(status_code=404,detail='Watchlist item not found.')
    db.delete(item); db.commit(); return {'message':'Watchlist item removed.'}

@router.post('/run')
def run_discovery(db: Session = Depends(get_db)):
    return {'run':run_out(discover_from_sources(db))}
