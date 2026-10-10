import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, deptLabel } from '../api'
import { usePolling } from '../hooks/usePolling'
import { useRecorder } from '../hooks/useRecorder'

// Quick-tap requests: typed text goes through the same triage as voice
const QUICK = [
  { icon: '💧', label: 'Water', text: 'Can I get some water please?' },
  { icon: '🛏️', label: 'Pillow', text: 'Can I get an extra pillow?' },
  { icon: '🧣', label: 'Blanket', text: 'I need an extra blanket, I am cold.' },
  { icon: '🧹', label: 'Clean room', text: 'My room needs cleaning.' },
  { icon: '📺', label: 'TV help', text: 'The TV remote is not working.' },
  { icon: '🌡️', label: 'Too hot/cold', text: 'The room temperature is uncomfortable.' },
  { icon: '🚻', label: 'Bathroom help', text: 'I need help getting to the bathroom.', clinical: true },
  { icon: '❗', label: 'I feel unwell', text: 'I feel unwell and need a nurse.', clinical: true },
]

const STATUS_TEXT = { new: 'Sent', accepted: 'On the way', done: 'Done' }

export default function Bedside() {
  const { bedId } = useParams()
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)   // { ticket, patient_message, tts_url }
  const [error, setError] = useState(null)
  const mic = useRecorder()
  const { data: tickets } = usePolling(() => api.bedsideTickets(bedId), 3000, [bedId])

  async function send(fn) {
    setBusy(true); setError(null); setResult(null)
    try {
      const r = await fn()
      setResult(r)
      setText('')
      if (r.tts_url) new Audio(r.tts_url).play().catch(() => {})
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  async function onMic() {
    if (mic.recording) {
      const blob = await mic.stop()
      if (blob && blob.size > 0) send(() => api.submitVoice(bedId, blob))
    } else {
      try { await mic.start() } catch { setError('Microphone not available. Please type your request instead.') }
    }
  }

  const urgent = result?.ticket.priority === 'urgent'

  return (
    <main className="bedside">
      <header className="bedside-head">
        <div>
          <p className="eyebrow">Bed {bedId}</p>
          <h1>How can we help you?</h1>
        </div>
        <span className="demo-tag">Demo, simulated hospital</span>
      </header>

      <section className="mic-zone">
        <button
          className={`mic ${mic.recording ? 'mic-on' : ''}`}
          onClick={onMic}
          disabled={busy || !mic.supported}
          aria-label={mic.recording ? 'Stop recording and send' : 'Start speaking'}
        >
          <span className="mic-icon">{mic.recording ? '■' : '🎤'}</span>
          <span className="mic-label">
            {busy ? 'Sending…' : mic.recording ? `Listening… ${mic.seconds}s · tap to send` : 'Tap and speak'}
          </span>
        </button>
      </section>

      <form className="type-row" onSubmit={(e) => { e.preventDefault(); text.trim() && send(() => api.submitText(bedId, text)) }}>
        <input
          className="big-input" value={text} onChange={(e) => setText(e.target.value)}
          placeholder="Or type your request…" aria-label="Type your request" disabled={busy}
        />
        <button className="btn btn-primary btn-xl" disabled={busy || !text.trim()}>Send</button>
      </form>

      {(result || error) && (
        <div role="status" className={`confirm ${error ? 'confirm-error' : urgent ? 'confirm-urgent' : 'confirm-ok'}`}>
          {error ? (
            <>
              <strong>Sorry, that didn't go through.</strong>
              <span>{error}. Please try again, type your request, or press your bedside call button.</span>
            </>
          ) : (
            <>
              <strong>{urgent ? 'Sent as URGENT to Nursing' : `Sent to ${deptLabel(result.ticket.department)}`}</strong>
              <span>{result.patient_message}</span>
            </>
          )}
        </div>
      )}

      <section>
        <h2 className="section-title">Quick requests</h2>
        <div className="quick-grid">
          {QUICK.map((q) => (
            <button key={q.label} className={`quick ${q.clinical ? 'quick-clinical' : ''}`} disabled={busy}
              onClick={() => send(() => api.submitText(bedId, q.text))}>
              <span className="quick-icon">{q.icon}</span>{q.label}
            </button>
          ))}
        </div>
      </section>

      {tickets?.length > 0 && (
        <section>
          <h2 className="section-title">Your requests</h2>
          <ul className="my-tickets">
            {tickets.map((t) => (
              <li key={t.ticket_id}>
                <span>{t.summary}</span>
                <span className={`st st-${t.status}`}>{STATUS_TEXT[t.status]}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <p className="fineprint">For emergencies, always press your bedside call button.</p>
    </main>
  )
}
