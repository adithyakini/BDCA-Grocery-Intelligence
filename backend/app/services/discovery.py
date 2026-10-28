import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import unescape
from urllib.parse import urlparse
import httpx
from sqlalchemy.orm import Session
from ..models import DiscoveryRun, DiscoverySource, WatchlistItem
from ..schemas import OfferCreate
from ..routers.deals import upsert_offer

USER_AGENT = 'BDCA-Grocery-Intelligence/0.1 (user-configured public RSS discovery)'
PRICE_RE = re.compile(r'(?:₹|Rs\.?\s?|INR\s?)([0-9]{1,5}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)', re.I)

def _tag(element, suffix):
    for child in element.iter():
        if child.tag.lower().endswith(suffix.lower()):
            return ''.join(child.itertext()).strip()
    return ''

def parse_feed(xml_text):
    root = ET.fromstring(xml_text)
    items = []
    for node in root.iter():
        tag = node.tag.lower()
        if tag.endswith('item') or tag.endswith('entry'):
            title = _tag(node, 'title')
            summary = _tag(node, 'description') or _tag(node, 'summary') or _tag(node, 'content')
            link = ''
            for child in node:
                if child.tag.lower().endswith('link'):
                    link = child.attrib.get('href') or (child.text or '').strip()
                    if link: break
            if title:
                items.append({'title': unescape(title), 'summary': unescape(summary), 'link': link})
    return items

def clean_text(value):
    return re.sub(r'<[^>]+>', ' ', unescape(value or '')).replace('\n', ' ').strip()

def match_watchlist(text, watchlist):
    normalized = re.sub(r'[^a-z0-9]+', ' ', text.lower())
    hits = []
    for item in watchlist:
        terms = [t for t in re.sub(r'[^a-z0-9]+', ' ', item.query.lower()).split() if len(t) > 2]
        if terms and sum(1 for term in terms if term in normalized) / len(terms) >= 0.5:
            hits.append(item)
    return hits

def discover_from_sources(db: Session):
    run = DiscoveryRun(status='RUNNING')
    db.add(run); db.commit(); db.refresh(run)
    sources = db.query(DiscoverySource).filter(DiscoverySource.enabled.is_(True)).all()
    watchlist = db.query(WatchlistItem).filter(WatchlistItem.enabled.is_(True)).all()
    entries_examined = candidates_found = offers_created = 0
    errors = []
    if not sources:
        run.status = 'NO_SOURCES'
        run.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        run.message = 'Add at least one public RSS/Atom feed source before running discovery.'
        db.commit()
        return run
    if not watchlist:
        run.status = 'NO_WATCHLIST'
        run.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        run.message = 'Add at least one product or keyword to the watchlist before running discovery.'
        db.commit()
        return run
    with httpx.Client(timeout=15, follow_redirects=True, headers={'User-Agent': USER_AGENT}) as client:
        for source in sources:
            try:
                parsed = urlparse(source.feed_url)
                if parsed.scheme not in ('http', 'https') or not parsed.netloc:
                    raise ValueError('Only public http/https feed URLs are supported.')
                response = client.get(source.feed_url)
                response.raise_for_status()
                entries = parse_feed(response.text)
                for entry in entries:
                    entries_examined += 1
                    title = clean_text(entry['title'])
                    summary = clean_text(entry['summary'])
                    full = f'{title} {summary}'
                    matches = match_watchlist(full, watchlist)
                    if not matches:
                        continue
                    price_match = PRICE_RE.search(full)
                    if not price_match:
                        continue
                    price = float(price_match.group(1).replace(',', ''))
                    if price <= 0:
                        continue
                    candidates_found += 1
                    # The discovery layer deliberately marks feed-derived values unverified.
                    # It does not claim that an RSS item is a checkout-ready offer.
                    for item in matches:
                        target = item.target_price
                        if target is not None and price > target:
                            continue
                        product_name = item.query.strip()
                        payload = OfferCreate(
                            product_name=product_name,
                            brand=None,
                            pack_size=None,
                            category=item.category or 'Discovered candidate',
                            store_name=source.name,
                            price=price,
                            effective_price=price,
                            usual_price=None,
                            product_url=entry['link'] or source.feed_url,
                            confidence='Low',
                            reason=f'Discovered from public feed: {title}. Price and availability are unverified; confirm at source.',
                            source_type='public_rss'
                        )
                        offer, created = upsert_offer(db, payload)
                        if created: offers_created += 1
                source.last_scanned_at = datetime.now(timezone.utc).replace(tzinfo=None)
                source.last_result = f'Checked {len(entries)} feed entries'
            except Exception as exc:
                source.last_scanned_at = datetime.now(timezone.utc).replace(tzinfo=None)
                source.last_result = f'Error: {str(exc)[:180]}'
                errors.append(f'{source.name}: {str(exc)[:180]}')
            db.commit()
    run.status = 'COMPLETED_WITH_ERRORS' if errors else 'COMPLETED'
    run.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
    run.sources_checked = len(sources)
    run.entries_examined = entries_examined
    run.candidates_found = candidates_found
    run.offers_created = offers_created
    run.message = '; '.join(errors) if errors else 'Discovery finished. Review candidates before relying on price or availability.'
    db.commit(); db.refresh(run)
    return run
