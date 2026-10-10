import { useEffect, useState } from 'react'

function minutesSince(iso) {
  // Backend timestamps are UTC; SQLite may drop the 'Z', so add it if missing.
  const t = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + 'Z')
  return Math.max(0, Math.floor((Date.now() - t.getTime()) / 60000))
}

export function useTick(ms = 15000) {
  const [, set] = useState(0)
  useEffect(() => { const id = setInterval(() => set((n) => n + 1), ms); return () => clearInterval(id) }, [ms])
}

const PRIORITY = { urgent: 'URGENT', soon: 'SOON', routine: 'ROUTINE' }

export default function TicketCard({ t, onStatus, busy }) {
  useTick()
  const mins = minutesSince(t.created_at)
  return (
    <article className={`ticket p-${t.priority} ${t.status === 'accepted' ? 'is-accepted' : ''}`}>
      <header className="ticket-head">
        <span className={`pill pill-${t.priority}`}>{PRIORITY[t.priority]}</span>
        <span className="ticket-room">Bed {t.bed_id}</span>
        <span className={`ticket-wait ${mins >= 10 ? 'late' : ''}`}>{mins === 0 ? 'just now' : `${mins} min`}</span>
      </header>

      <h3 className="ticket-summary">{t.summary}</h3>
      <p className="ticket-quote">“{t.translated_text || t.original_text}”</p>
      {t.translated_text && (
        <p className="ticket-meta">Original ({t.language}): {t.original_text}</p>
      )}
      {t.escalation_reason && <p className="ticket-reason">⚠ {t.escalation_reason}</p>}
      {t.needs_review && <p className="ticket-review">Needs human review: AI was unsure or unavailable</p>}

      <footer className="ticket-actions">
        {t.status === 'new' && (
          <button className="btn btn-primary" disabled={busy} onClick={() => onStatus(t.ticket_id, 'accepted')}>
            Accept
          </button>
        )}
        {t.status === 'accepted' && <span className="ticket-meta">Accepted · on the way</span>}
        <button className="btn btn-ghost" disabled={busy} onClick={() => onStatus(t.ticket_id, 'done')}>
          Done ✓
        </button>
      </footer>
    </article>
  )
}
