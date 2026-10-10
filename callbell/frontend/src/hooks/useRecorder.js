import { useRef, useState } from 'react'

// Tap to start, tap to stop. Resolves stop() with an audio Blob.
// Mic access needs HTTPS or localhost.
export function useRecorder() {
  const [recording, setRecording] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const rec = useRef(null)
  const chunks = useRef([])
  const timer = useRef(null)

  const supported = typeof window !== 'undefined' && !!navigator.mediaDevices?.getUserMedia && !!window.MediaRecorder

  async function start() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const mime = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : ''
    const mr = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined)
    chunks.current = []
    mr.ondataavailable = (e) => e.data.size && chunks.current.push(e.data)
    mr.start()
    rec.current = mr
    setSeconds(0)
    timer.current = setInterval(() => setSeconds((s) => s + 1), 1000)
    setRecording(true)
  }

  function stop() {
    return new Promise((resolve) => {
      const mr = rec.current
      if (!mr) return resolve(null)
      mr.onstop = () => {
        mr.stream.getTracks().forEach((t) => t.stop())
        resolve(new Blob(chunks.current, { type: mr.mimeType || 'audio/webm' }))
      }
      mr.stop()
      clearInterval(timer.current)
      setRecording(false)
    })
  }

  return { supported, recording, seconds, start, stop }
}
