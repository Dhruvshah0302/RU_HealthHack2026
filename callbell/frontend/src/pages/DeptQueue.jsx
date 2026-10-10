import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, DEPARTMENTS, deptLabel } from '../api'
import TicketCard from '../components/TicketCard'
import { usePolling } from '../hooks/usePolling'

function beep(urgent) {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const o = ctx.createOscillator(); const g = ctx.createGain()
    o.frequency.value = urgent ? 880 : 520
    g.gain.value = 0.08
    o.connect(g); g.connect(ctx.destination)
    o.start(); o.stop(ctx.currentTime + (urgent ? 0.6 : 0.18))
  } catch { /* audio blocked until user interacts */ }
}

export default function DeptQueue() {
  const { dept } = useParams()
  const { data: tickets, error, refresh } = usePolling(() => api.queue(dept), 2000, [dept])
  const [busyId, setBusyId] = useState(null)
  const seen = useRef(null)
  const [flash, setFlash] = useState(false)

  // Sound + flash when a new ticket arrives
  useEffect(() => {
    if (!tickets) return
    const ids = new Set(tickets.map((t) => t.ticket_id))
    if (seen.current) {
      const fresh = tickets.filter((t) => !seen.current.has(t.ticket_id))
      if (fresh.length) {
        beep(fresh.some((t) => t.priority === 'urgent'))
        setFlash(true); setTimeout(() => setFlash(false), 1200)
      }
    }
    seen.current = ids
  }, [tickets])

  useEffect(() => { seen.current = null }, [dept])

  async function onStatus(id, status) {
    setBusyId(id)
    try { await api.setStatus(id, status); await refresh() } finally { setBusyId(null) }
  }

  const list = tickets || []
  const urgentCount = list.filter((t) => t.priority === 'urgent').length
  const info = DEPARTMENTS.find((d) => d.id === dept)

  return (
    <main className={`queue ${flash ? 'flash' : ''}`}>
      <header className="queue-head">
        <div>
          <p className="eyebrow">Department queue</p>
          <h1>{info?.icon} {deptLabel(dept)} <span className="count">{list.length} open</span></h1>
        </div>
        <nav className="dept-tabs">
          {DEPARTMENTS.map((d) => (
            <Link key={d.id} to={`/dept/${d.id}`} className={d.id === dept ? 'active' : ''}>{d.label}</Link>
          ))}
        </nav>
      </header>

      {dept === 'nursing' && urgentCount > 0 && (
        <div className="alarm" role="alert">🚨 {urgentCount} urgent clinical request{urgentCount > 1 ? 's' : ''}</div>
      )}
      {error && <div className="confirm confirm-error">Can't reach the server: {error}</div>}

      {tickets && list.length === 0 && (
        <div className="empty">
          <p className="empty-big">All clear</p>
          <p>No open requests for {deptLabel(dept)}.{dept === 'nursing' && ' Non-clinical requests are going to support teams.'}</p>
        </div>
      )}

      <section className="ticket-grid">
        {list.map((t) => <TicketCard key={t.ticket_id} t={t} onStatus={onStatus} busy={busyId === t.ticket_id} />)}
      </section>
    </main>
  )
}
