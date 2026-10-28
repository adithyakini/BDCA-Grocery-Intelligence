import { useCallback, useEffect, useMemo, useState } from 'react'
import { addDemoOffer, getDashboard, getOffers, healthCheck, reviewOffer, getDiscoveryOverview, addDiscoverySource, deleteDiscoverySource, addWatchlistItem, deleteWatchlistItem, runDiscovery } from './services'

const money = n => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(Number(n || 0))
const pct = n => `${Math.round(Number(n || 0))}%`

export default function App() {
  const [offers, setOffers] = useState([])
  const [summary, setSummary] = useState({ pending: 0, actioned: 0, ignored: 0, potential_savings: 0 })
  const [filter, setFilter] = useState('PENDING')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState(null)
  const [message, setMessage] = useState('')
  const [apiState, setApiState] = useState('Checking API…')
  const [view, setView] = useState('deals')
  const [discovery, setDiscovery] = useState({ sources: [], watchlist: [], runs: [] })
  const [sourceName, setSourceName] = useState('')
  const [sourceUrl, setSourceUrl] = useState('')
  const [watchQuery, setWatchQuery] = useState('')
  const [watchCategory, setWatchCategory] = useState('Grocery')
  const [watchTarget, setWatchTarget] = useState('')
  const [discoveryBusy, setDiscoveryBusy] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const [data, dash] = await Promise.all([getOffers({ status: filter }), getDashboard()])
      setOffers(data.items)
      setSummary(dash)
      setApiState('API connected')
      setMessage('')
    } catch (e) {
      setApiState('API unavailable')
      setMessage(e?.response?.data?.detail || 'Could not reach the backend. Start the FastAPI server and check VITE_API_URL.')
    } finally { setLoading(false) }
  }, [filter])

  const refreshDiscovery = useCallback(async () => { try { setDiscovery(await getDiscoveryOverview()) } catch (e) { /* keep the deals dashboard usable if discovery endpoint is unavailable */ } }, [])
  useEffect(() => { refresh(); refreshDiscovery(); healthCheck().catch(() => setApiState('API unavailable')) }, [refresh, refreshDiscovery])
  useEffect(() => { const timer = setInterval(refresh, 60000); return () => clearInterval(timer) }, [refresh])

  const visible = useMemo(() => offers.filter(o => `${o.product_name} ${o.brand || ''} ${o.store_name} ${o.category || ''}`.toLowerCase().includes(search.toLowerCase())), [offers, search])

  async function decide(offer, status) {
    setBusyId(offer.id)
    try {
      const result = await reviewOffer(offer.id, status)
      setMessage(result.message || `Marked ${status.toLowerCase()}.`)
      await refresh()
    } catch (e) { setMessage(e?.response?.data?.detail || 'Could not save this decision.') }
    finally { setBusyId(null) }
  }

  async function submitSource(e) { e.preventDefault(); try { await addDiscoverySource({ name: sourceName, feed_url: sourceUrl }); setSourceName(''); setSourceUrl(''); setMessage('Discovery feed added.'); await refreshDiscovery() } catch (e) { setMessage(e?.response?.data?.detail || 'Could not add feed source.') } }
  async function submitWatchlist(e) { e.preventDefault(); try { await addWatchlistItem({ query: watchQuery, category: watchCategory || null, target_price: watchTarget ? Number(watchTarget) : null }); setWatchQuery(''); setWatchTarget(''); setMessage('Watchlist item added.'); await refreshDiscovery() } catch (e) { setMessage(e?.response?.data?.detail || 'Could not add watchlist item.') } }
  async function startDiscovery() { setDiscoveryBusy(true); try { const result = await runDiscovery(); setMessage(result.run.message || 'Discovery run completed.'); await Promise.all([refreshDiscovery(), refresh()]) } catch (e) { setMessage(e?.response?.data?.detail || 'Discovery run failed.') } finally { setDiscoveryBusy(false) } }
  async function removeSource(id) { try { await deleteDiscoverySource(id); await refreshDiscovery() } catch (e) { setMessage('Could not remove source.') } }
  async function removeWatch(id) { try { await deleteWatchlistItem(id); await refreshDiscovery() } catch (e) { setMessage('Could not remove watchlist item.') } }

  async function addSample() {
    try { await addDemoOffer(); setFilter('PENDING'); setMessage('A sample suggestion was added.'); await refresh() }
    catch (e) { setMessage(e?.response?.data?.detail || 'Could not add sample offer.') }
  }

  return <div className="app-shell">
    <aside className="sidebar"><div className="brand-mark">B</div><div className="brand-name">BDCA<span>INTELLIGENCE</span></div><div className="side-label">WORKSPACE</div><button className={`side-link nav-button ${view==='deals'?'active':''}`} onClick={()=>setView('deals')}>▦ <span>Deal review</span></button><button className={`side-link nav-button ${view==='discovery'?'active':''}`} onClick={()=>setView('discovery')}>⌕ <span>Discovery</span></button><div className="side-link">↗ <span>Price intelligence</span><small>Next</small></div><div className="side-link">▤ <span>Basket optimizer</span><small>Next</small></div><div className="sidebar-bottom"><div className="pulse-dot"/> <span>{apiState}</span></div></aside>
    <main className="main-content"><header className="topbar"><div><div className="eyebrow">PERSONAL SHOPPING AGENT / BENGALURU</div><h1>Grocery Intelligence</h1><p className="subtitle">Review the deals worth your attention. Your decisions teach the system what to show next.</p></div><button className="button button-secondary" onClick={refresh}>↻ Refresh</button></header>
      {message && <div className="notice" role="status"><span>{message}</span><button aria-label="Dismiss message" onClick={() => setMessage('')}>×</button></div>}
      {view === 'deals' ? <><section className="metrics"><Metric label="Awaiting review" value={summary.pending} hint="Ready for your decision"/><Metric label="Actioned" value={summary.actioned} hint="Deals you chose to pursue"/><Metric label="Ignored" value={summary.ignored} hint="Decisions recorded"/><Metric label="Potential savings" value={money(summary.potential_savings)} hint="Actioned deals vs usual price"/></section>
      <section className="queue-panel"><div className="panel-heading"><div><h2>Deal review queue</h2><p>Offers are compared using effective price when known.</p></div><button className="button button-primary" onClick={addSample}>＋ Add test suggestion</button></div>
        <div className="toolbar"><div className="filter-tabs" role="group" aria-label="Filter deals">{[['PENDING','Pending'],['ACTIONED','Actioned'],['IGNORED','Ignored'],['ALL','All deals']].map(([key,label])=><button key={key} className={filter===key?'selected':''} onClick={()=>setFilter(key)}>{label}{key==='PENDING' && <span className="tab-count">{summary.pending}</span>}</button>)}</div><input className="search" type="search" placeholder="Search product or store…" value={search} onChange={e=>setSearch(e.target.value)} aria-label="Search deals"/></div>
        <div className="rule-banner"><span className="rule-icon">◷</span><div><strong>7-day suppression is enabled</strong><p>Ignored offers stay hidden for 7 days. A lower effective price can bring the deal back sooner. Decisions are saved in the database.</p></div></div>
        {loading ? <div className="empty-state">Loading offers…</div> : visible.length === 0 ? <div className="empty-state"><div className="empty-icon">⌕</div><strong>No deals in this view</strong><p>New qualifying offers will appear here when an authorized discovery source is connected.</p></div> : <div className="deal-list">{visible.map(offer => <article className="deal-card" key={offer.id}><div className="deal-top"><div className="product-symbol">{(offer.product_name || 'G').slice(0,1).toUpperCase()}</div><div className="product-info"><div className="product-title-row"><h3>{offer.product_name}</h3><span className={`status-badge status-${offer.status.toLowerCase()}`}>{offer.status}</span></div><p>{[offer.brand, offer.pack_size, offer.category].filter(Boolean).join(' · ') || 'Grocery'} </p><div className="store-line"><span className="store-dot"/> {offer.store_name} <span className="separator">·</span> {offer.confidence || 'Unverified'} confidence</div></div><div className="price-block"><strong>{money(offer.effective_price ?? offer.price)}</strong>{offer.usual_price != null && <span>Usual {money(offer.usual_price)}</span>}{offer.usual_price != null && <em>{money(Math.max(0, offer.usual_price - (offer.effective_price ?? offer.price)))} lower · {pct(offer.usual_price ? Math.max(0, (offer.usual_price - (offer.effective_price ?? offer.price)) / offer.usual_price * 100) : 0)}</em>}</div></div>
          <div className="offer-foot"><div className="offer-reason"><span>✦</span> {offer.reason || 'Offer observed; verify final checkout price and eligibility.'}{offer.expires_at && <small>Expires {new Date(offer.expires_at).toLocaleDateString('en-IN')}</small>}</div><div className="card-actions">{offer.status === 'PENDING' ? <><button className="button button-quiet" disabled={busyId===offer.id} onClick={()=>decide(offer,'IGNORED')}>Ignore</button><button className="button button-primary" disabled={busyId===offer.id} onClick={()=>decide(offer,'ACTIONED')}>{busyId===offer.id?'Saving…':'✓ Actioned'}</button></> : <span className="decision-note">Decision saved{offer.reviewed_at ? ` · ${new Date(offer.reviewed_at).toLocaleDateString('en-IN')}` : ''}</span>}</div></div>
        </article>)}</div>}
        <div className="panel-footer"><span>Showing {visible.length} {visible.length===1?'suggestion':'suggestions'}</span><span>Demo mode until offer sources are configured</span></div>
      </section>
      </> : <section className="discovery-layout">
        <div className="discovery-intro"><div><div className="eyebrow">SOURCE-AGNOSTIC DISCOVERY</div><h2>Discover offers before platform integrations</h2><p>Configure public RSS/Atom feeds and the products you care about. Discovery checks feed entries for watchlist matches and prices, then sends candidates into the existing review queue.</p></div><button className="button button-primary" disabled={discoveryBusy} onClick={startDiscovery}>{discoveryBusy ? 'Scanning…' : '▶ Run discovery now'}</button></div>
        <div className="discovery-note"><strong>Current scope:</strong> This is a generic feed-based discovery engine, not a crawler of all websites. Only add public feeds you are permitted to access. Feed-derived prices are marked low-confidence and must be verified at the source. Scheduled continuous scanning is a follow-up; this build runs scans when you click the button.</div>
        <div className="discovery-columns"><section className="discovery-card"><h3>1. Product watchlist</h3><p>Keywords to look for in feed titles and descriptions.</p><form onSubmit={submitWatchlist} className="discovery-form"><label>Product / keyword<input required minLength="2" value={watchQuery} onChange={e=>setWatchQuery(e.target.value)} placeholder="e.g. Tata Sampann Toor Dal" /></label><label>Category<input value={watchCategory} onChange={e=>setWatchCategory(e.target.value)} placeholder="Grocery" /></label><label>Optional target price (₹)<input type="number" min="1" step="0.01" value={watchTarget} onChange={e=>setWatchTarget(e.target.value)} placeholder="No limit" /></label><button className="button button-primary" type="submit">＋ Add to watchlist</button></form><div className="discovery-list">{discovery.watchlist.length ? discovery.watchlist.map(w=><div className="discovery-row" key={w.id}><div><strong>{w.query}</strong><small>{w.category || 'Any category'}{w.target_price ? ` · Target ${money(w.target_price)}` : ''}</small></div><button className="button button-quiet" onClick={()=>removeWatch(w.id)}>Remove</button></div>) : <div className="discovery-empty">No watchlist items yet.</div>}</div></section>
        <section className="discovery-card"><h3>2. Public feed sources</h3><p>Add RSS or Atom feed URLs. Store-specific app integration comes later.</p><form onSubmit={submitSource} className="discovery-form"><label>Source name<input required value={sourceName} onChange={e=>setSourceName(e.target.value)} placeholder="e.g. Brand offers feed" /></label><label>Feed URL<input required type="url" value={sourceUrl} onChange={e=>setSourceUrl(e.target.value)} placeholder="https://example.com/offers.xml" /></label><button className="button button-primary" type="submit">＋ Add feed source</button></form><div className="discovery-list">{discovery.sources.length ? discovery.sources.map(src=><div className="discovery-row" key={src.id}><div><strong>{src.name}</strong><small title={src.feed_url}>{src.feed_url}<br/>{src.last_result || 'Not scanned yet'}</small></div><button className="button button-quiet" onClick={()=>removeSource(src.id)}>Remove</button></div>) : <div className="discovery-empty">No feeds configured. Add a public RSS/Atom feed to begin.</div>}</div></section></div>
        <section className="discovery-card"><h3>3. Recent discovery runs</h3>{discovery.runs.length ? <div className="runs-table">{discovery.runs.map(r=><div className="run-row" key={r.id}><div><strong>{r.status}</strong><small>{r.started_at ? new Date(r.started_at+'Z').toLocaleString('en-IN') : 'Run'} · {r.message || ''}</small></div><div className="run-stats"><span>{r.sources_checked} sources</span><span>{r.entries_examined} entries</span><span>{r.candidates_found} candidates</span><span>{r.offers_created} new offers</span></div></div>)}</div> : <div className="discovery-empty">No runs yet. Add a watchlist item and a feed source, then run discovery.</div>}</section>
      </section>}
      <footer>BDCA Grocery Intelligence <span>·</span> Review decisions stay yours. No automatic checkout or payments.</footer>
    </main>
  </div>
}
function Metric({label,value,hint}) { return <div className="metric-card"><div className="metric-label">{label}</div><div className="metric-value">{value}</div><div className="metric-hint">{hint}</div></div> }
