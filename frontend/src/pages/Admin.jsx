import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, DEPARTMENTS } from '../api'
import { usePolling } from '../hooks/usePolling'

export default function Admin() {
  const { data: beds, refresh } = usePolling(api.beds, 5000)
  const { data: metrics } = usePolling(api.metrics, 3000)
  const [room, setRoom] = useState({ room_id: '', unit: 'Med-Surg 4' })
  const [bed, setBed] = useState({ bed_id: '', room_id: '', alias: '' })
  const [msg, setMsg] = useState(null)

  const run = async (fn, ok) => {
    try { await fn(); setMsg({ ok: true, text: ok }); refresh() } catch (e) { setMsg({ ok: false, text: e.message }) }
  }

  return (
    <main className="admin">
      <header className="queue-head">
        <div><p className="eyebrow">Admin</p><h1>Rooms & beds</h1></div>
        <span className="demo-tag">Demo labels only, no patient data</span>
      </header>

      {metrics && (
        <section className="stats">
          <div className="stat"><span className="stat-n">{metrics.total}</span><span>requests</span></div>
          <div className="stat stat-accent"><span className="stat-n">{metrics.diverted_from_nursing_pct}%</span><span>kept off nursing</span></div>
          {DEPARTMENTS.map((d) => (
            <div className="stat" key={d.id}><span className="stat-n">{metrics.by_department[d.id] ?? 0}</span><span>{d.label}</span></div>
          ))}
        </section>
      )}

      {msg && <div className={`confirm ${msg.ok ? 'confirm-ok' : 'confirm-error'}`}>{msg.text}</div>}

      <section className="forms">
        <form onSubmit={(e) => { e.preventDefault(); run(() => api.addRoom(room.room_id, room.unit), `Room ${room.room_id} added`) }}>
          <h2 className="section-title">Add room</h2>
          <input placeholder="Room (e.g. 413)" value={room.room_id} onChange={(e) => setRoom({ ...room, room_id: e.target.value })} required />
          <input placeholder="Unit" value={room.unit} onChange={(e) => setRoom({ ...room, unit: e.target.value })} />
          <button className="btn btn-primary">Add room</button>
        </form>
        <form onSubmit={(e) => { e.preventDefault(); run(() => api.addBed(bed.bed_id, bed.room_id, bed.alias), `Bed ${bed.bed_id} added`) }}>
          <h2 className="section-title">Add bed</h2>
          <input placeholder="Bed (e.g. 413A)" value={bed.bed_id} onChange={(e) => setBed({ ...bed, bed_id: e.target.value })} required />
          <input placeholder="Room" value={bed.room_id} onChange={(e) => setBed({ ...bed, room_id: e.target.value })} required />
          <input placeholder="Demo patient label (optional)" value={bed.alias} onChange={(e) => setBed({ ...bed, alias: e.target.value })} />
          <button className="btn btn-primary">Add bed</button>
        </form>
      </section>

      <table className="beds">
        <thead><tr><th>Bed</th><th>Room</th><th>Demo patient</th><th>Bedside screen</th><th /></tr></thead>
        <tbody>
          {(beds || []).map((b) => (
            <tr key={b.bed_id}>
              <td><strong>{b.bed_id}</strong></td>
              <td>{b.room_id}</td>
              <td>{b.occupied ? b.patient_alias : <em>Empty</em>}</td>
              <td><Link to={`/bed/${b.bed_id}`}>Open ↗</Link></td>
              <td>
                {b.occupied
                  ? <button className="btn btn-ghost" onClick={() => run(() => api.discharge(b.bed_id), `${b.bed_id} discharged`)}>Discharge</button>
                  : <button className="btn btn-ghost" onClick={() => run(() => api.assign(b.bed_id, `Demo Patient ${b.bed_id}`), `${b.bed_id} assigned`)}>Assign demo patient</button>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  )
}
