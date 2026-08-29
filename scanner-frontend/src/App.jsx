import { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'

// Canton scanner dashboard — polls the FastAPI backend and shows the party's
// live balance plus transfer history.
//
// CORS: the browser calls http://localhost:8000 from the Vite dev server on
// http://localhost:5173, which is a cross-origin request. FastAPI must add
// CORSMiddleware with allow_origins including "http://localhost:5173", e.g.
//
//   from fastapi.middleware.cors import CORSMiddleware
//   app.add_middleware(
//       CORSMiddleware,
//       allow_origins=["http://localhost:5173"],
//       allow_methods=["*"],
//       allow_headers=["*"],
//   )
//
// Without it every fetch below throws a TypeError and the dashboard just sits
// on "Backend unreachable" — the failure is silent apart from a console note,
// so check this first if the status dot stays red while curl works fine.

const PARTY = 'alice'
const API = 'http://localhost:8000'
const POLL_MS = 1500

async function getJSON(url) {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

function relativeTime(iso) {
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return iso
  const secs = Math.max(0, Math.round((Date.now() - then) / 1000))
  if (secs < 60) return `${secs}s ago`
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`
  return new Date(then).toLocaleString()
}

function fmt(n) {
  return typeof n === 'number' ? n.toLocaleString() : n
}

// Roll the transfer list up into the numbers shown in the stat row. Purely
// derived from /history — no extra backend call.
function summarise(history) {
  let received = 0
  let sent = 0
  let inCount = 0
  let outCount = 0
  for (const t of history) {
    const amt = Number(t.amount) || 0
    if (t.direction === 'in') {
      received += amt
      inCount += 1
    } else {
      sent += amt
      outCount += 1
    }
  }
  return { received, sent, inCount, outCount, net: received - sent }
}

export default function App() {
  const [balance, setBalance] = useState(null) // last known good
  const [history, setHistory] = useState([]) // last known good
  const [loading, setLoading] = useState(true) // only true until first success
  const [online, setOnline] = useState(null) // null until the first poll settles
  const [lastUpdated, setLastUpdated] = useState(null)
  const [flash, setFlash] = useState(false)
  const [showHistory, setShowHistory] = useState(true)
  const [, setTick] = useState(0) // re-render so relative times stay live

  // The effect owns the polling loop; pollRef lets the refresh buttons fire an
  // off-schedule poll without hoisting the fetch logic out of it.
  const pollRef = useRef(() => {})
  const refresh = useCallback(() => pollRef.current(), [])

  useEffect(() => {
    let alive = true
    let flashTimer

    async function poll() {
      try {
        const [bal, hist] = await Promise.all([
          getJSON(`${API}/balance/${PARTY}`),
          getJSON(`${API}/history/${PARTY}`),
        ])
        if (!alive) return
        setBalance(bal)
        setHistory(Array.isArray(hist) ? hist : [])
        setLastUpdated(Date.now())
        setOnline(true)
        setLoading(false)
        // Pulse the balance so a refresh is visible even when nothing changed.
        setFlash(true)
        clearTimeout(flashTimer)
        flashTimer = setTimeout(() => alive && setFlash(false), 400)
      } catch (err) {
        // Keep the last known good balance/history on screen — a backend
        // restart should flip the status dot, not blank out the dashboard.
        if (!alive) return
        console.warn('poll failed:', err)
        setOnline(false)
      }
    }

    pollRef.current = poll
    poll()
    const pollId = setInterval(poll, POLL_MS)
    const tickId = setInterval(() => setTick((n) => n + 1), 1000)
    return () => {
      alive = false
      clearInterval(pollId)
      clearInterval(tickId)
      clearTimeout(flashTimer)
    }
  }, [])

  const stats = summarise(history)
  const unit = balance?.instrument ?? ''

  // Three-way status: unknown before the first poll settles, so the chip never
  // shows a green "Live" it hasn't earned. Once a poll has failed without ever
  // succeeding, the backend simply isn't up — saying "Loading…" would be a lie.
  const statusChip =
    online === null
      ? { tone: 'chip-mute', text: 'Connecting…' }
      : online
        ? { tone: 'chip-pos', text: 'Live' }
        : { tone: 'chip-neg', text: 'Backend unreachable' }

  const emptyText = !loading
    ? 'No transfers yet.'
    : online === false
      ? `Waiting for the backend at ${API}`
      : 'Loading…'

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">C</div>
          <div>
            <div className="brand-name">Canton Scanner</div>
            <div className="brand-sub">Ledger activity</div>
          </div>
        </div>

        <div className="topbar-status">
          {lastUpdated && (
            <span className="synced">
              Updated {relativeTime(new Date(lastUpdated).toISOString())}
            </span>
          )}
          <span className={`chip ${statusChip.tone}`}>
            <span className="dot" />
            {statusChip.text}
          </span>
        </div>
      </header>

      <main className="main">
        <section className="card hero span-12">
          <div>
            <p className="hero-label">Current balance</p>
            {loading ? (
              <div className="amount">
                <span className="amount-value placeholder">
                  {online === false ? '—' : 'Loading…'}
                </span>
              </div>
            ) : (
              <div className={flash ? 'amount flash' : 'amount'}>
                <span className="amount-value">{fmt(balance?.total)}</span>
                {unit && <span className="amount-unit">{unit}</span>}
              </div>
            )}
            <p className="hero-party">
              Party <code>{PARTY}</code>
            </p>
          </div>

          <div className="hero-actions">
            <button type="button" className="btn-primary" onClick={refresh}>
              Refresh now
            </button>
          </div>
        </section>

        <section className="card span-4">
          <div className="stat-head">
            <span className="stat-label">Received</span>
            <span className="chip chip-pos">↓ {stats.inCount}</span>
          </div>
          <div className="stat-value pos">{loading ? '—' : fmt(stats.received)}</div>
          <div className="stat-foot">
            {stats.inCount === 1 ? '1 incoming transfer' : `${stats.inCount} incoming transfers`}
          </div>
        </section>

        <section className="card span-4">
          <div className="stat-head">
            <span className="stat-label">Sent</span>
            <span className="chip chip-neg">↑ {stats.outCount}</span>
          </div>
          <div className="stat-value neg">{loading ? '—' : fmt(stats.sent)}</div>
          <div className="stat-foot">
            {stats.outCount === 1 ? '1 outgoing transfer' : `${stats.outCount} outgoing transfers`}
          </div>
        </section>

        <section className="card span-4">
          <div className="stat-head">
            <span className="stat-label">Net flow</span>
            <span className={stats.net < 0 ? 'chip chip-neg' : 'chip chip-pos'}>
              {stats.net < 0 ? '↓' : '↑'} {history.length}
            </span>
          </div>
          <div className={stats.net < 0 ? 'stat-value neg' : 'stat-value'}>
            {loading ? '—' : `${stats.net > 0 ? '+' : ''}${fmt(stats.net)}`}
          </div>
          <div className="stat-foot">Across {history.length} transfers</div>
        </section>

        <section className="card span-12">
          <div className="panel-head">
            <h2 className="panel-title">Transfers</h2>
            <div className="panel-tools">
              <span className="chip chip-mute">{history.length}</span>
              <button
                type="button"
                className="btn-icon"
                onClick={refresh}
                title="Refresh"
                aria-label="Refresh transfers"
              >
                ↻
              </button>
              <button
                type="button"
                className="btn-icon"
                onClick={() => setShowHistory((v) => !v)}
                title={showHistory ? 'Collapse' : 'Expand'}
                aria-expanded={showHistory}
                aria-label={showHistory ? 'Collapse transfers' : 'Expand transfers'}
              >
                {showHistory ? '⌃' : '⌄'}
              </button>
            </div>
          </div>

          {showHistory && (
            <ul className="rows">
              {history.length === 0 ? (
                <li className="empty">{emptyText}</li>
              ) : (
                history.map((t) => {
                  const dir = t.direction === 'in' ? 'in' : 'out'
                  return (
                    <li className="row" key={t.id}>
                      <span className={`row-arrow ${dir}`} aria-hidden="true">
                        {dir === 'in' ? '↓' : '↑'}
                      </span>
                      <span className={`row-amount ${dir}`}>
                        {dir === 'in' ? '+' : '−'}
                        {t.amount}
                      </span>
                      <span className="row-party">
                        <span>{dir === 'in' ? 'from' : 'to'}</span>
                        {t.counterparty}
                      </span>
                      <span className="row-time" title={t.timestamp}>
                        {relativeTime(t.timestamp)}
                      </span>
                    </li>
                  )
                })
              )}
            </ul>
          )}
        </section>
      </main>
    </div>
  )
}
