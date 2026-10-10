// Thin REST client. All paths match backend/app/routers/*.py
const BASE = import.meta.env.VITE_API_BASE || ''   // '' = same origin (Vite proxy)

async function req(path, opts = {}) {
  const res = await fetch(BASE + path, opts)
  if (!res.ok) {
    let detail = res.statusText
    try { detail = (await res.json()).detail || detail } catch { /* not json */ }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return res.status === 204 ? null : res.json()
}

const json = (method, body) => ({
  method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
})

export const api = {
  submitText: (bed_id, text) => req('/api/requests/text', json('POST', { bed_id, text })),
  submitVoice: (bed_id, blob) => {
    const fd = new FormData()
    fd.append('bed_id', bed_id)
    fd.append('audio', blob, 'note.webm')
    return req('/api/requests/voice', { method: 'POST', body: fd })
  },
  bedsideTickets: (bed_id) => req(`/api/bedside/${bed_id}/tickets`),
  queue: (department, status = 'open') =>
    req(`/api/tickets?department=${department}&status=${status}`),
  setStatus: (id, status) => req(`/api/tickets/${id}`, json('PATCH', { status })),
  metrics: () => req('/api/tickets/metrics/summary'),
  beds: () => req('/api/admin/beds'),
  rooms: () => req('/api/admin/rooms'),
  addRoom: (room_id, unit) => req('/api/admin/rooms', json('POST', { room_id, unit })),
  addBed: (bed_id, room_id, patient_alias) =>
    req('/api/admin/beds', json('POST', { bed_id, room_id, patient_alias: patient_alias || null })),
  assign: (bed_id, alias) =>
    req(`/api/admin/beds/${bed_id}/assign?patient_alias=${encodeURIComponent(alias)}`, { method: 'PATCH' }),
  discharge: (bed_id) => req(`/api/admin/beds/${bed_id}/discharge`, { method: 'PATCH' }),
}

export const DEPARTMENTS = [
  { id: 'nursing', label: 'Nursing', icon: '🩺' },
  { id: 'housekeeping', label: 'Housekeeping', icon: '🧺' },
  { id: 'food_services', label: 'Food Services', icon: '🍎' },
  { id: 'facilities', label: 'Facilities', icon: '🔧' },
  { id: 'it_support', label: 'IT Support', icon: '📺' },
]

export const deptLabel = (id) => DEPARTMENTS.find((d) => d.id === id)?.label ?? id
