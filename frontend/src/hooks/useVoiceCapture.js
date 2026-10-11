import { useCallback, useEffect, useRef, useState } from "react";
import { serverSpeechReady, transcribe } from "../lib/api.js";

/* One tap starts listening. We record audio for ElevenLabs and, at the same time, run
   Chrome's own speech recognition, so if ElevenLabs fails we already have a transcript
   without asking the patient to repeat. onResult gets the words, or "" when nothing was
   understood (no microphone, silence, both services failed): the page sends "" to the nurse. */

// SPEC: stop after 2 s of silence or 10 s in total.
const SILENCE_MS = 2000;
const MAX_LISTEN_MS = 10000;
// Loudness in decibels: about -52 dB is a quiet room, -40 dB soft speech into a laptop
// microphone, -25 dB a clear speaking voice. These map to a 0..1 level.
const FLOOR_DB = -52;
const FULL_DB = -22;
const SPEECH_LEVEL = 0.28;      // level that counts as speech (about -43 dB)
const QUIET_HINT_MS = 1500;     // this long without speech shows "a little louder"

const within = (promise, ms) => Promise.race([promise, new Promise((r) => setTimeout(r, ms))]);

function stopCapture(s) {
  s.analyser = null;
  clearInterval(s.meter);
  clearTimeout(s.limit);
  if (s.recorder && s.recorder.state !== "inactive") { try { s.recorder.stop(); } catch { /* already stopped */ } }
  if (s.recognition) { try { s.recognition.stop(); } catch { /* already stopped */ } }
  s.stream.getTracks().forEach((track) => track.stop());
  if (s.audio) s.audio.close().catch(() => {});
}

export function useVoiceCapture({ langTag, onResult, debug = false }) {
  const [state, setState] = useState("idle");   // idle | listening | working
  const [level, setLevel] = useState(0);         // 0..1 live loudness
  const [hint, setHint] = useState(null);        // null | "quiet" | "good"
  const [debugText, setDebugText] = useState("");
  const [heard, setHeard] = useState("");        // live words while listening (browser recognition only)
  const [serverSpeech, setServerSpeech] = useState(false);   // ElevenLabs set up on the server
  const serverSpeechRef = useRef(false);
  useEffect(() => {
    serverSpeechReady().then((ready) => { serverSpeechRef.current = ready; setServerSpeech(ready); });
  }, []);
  const sessionRef = useRef(null);
  const analyserRef = useRef(null);              // live audio for the bubble around the button
  const onResultRef = useRef(onResult);
  onResultRef.current = onResult;

  const finish = useCallback(async () => {
    const s = sessionRef.current;
    if (!s || s.finishing) return;
    s.finishing = true;
    setState("working"); setLevel(0); setHint(null);

    clearInterval(s.meter); clearTimeout(s.limit);
    analyserRef.current = null;
    if (s.recorder && s.recorder.state !== "inactive") s.recorder.stop();
    if (s.recognition) { try { s.recognition.stop(); } catch { /* ignore */ } }
    await within(Promise.all([s.stopped, s.recognitionEnded].filter(Boolean)), 2000);
    stopCapture(s);
    sessionRef.current = null;

    // ElevenLabs first (any language, much better at messy speech); the browser's words only if it fails.
    let text = "", language = null, source = "none";
    if (s.chunks.length) {
      const blob = new Blob(s.chunks, { type: s.recorder.mimeType || "audio/webm" });
      if (blob.size) ({ text, language } = await transcribe(blob, langTag));
      if (text) source = "elevenlabs";
    }
    if (!text && s.browserText.trim()) { text = s.browserText.trim(); source = "browser"; }
    if (debug) setDebugText(`heard by ${source}${language ? " (" + language + ")" : ""}: ${text || "(nothing)"}`);
    try { await onResultRef.current(text, language); } finally { setState("idle"); }
  }, [langTag]);

  const finishRef = useRef(finish);
  finishRef.current = finish;

  // The patient switched away or pressed the nurse button: drop the recording, send nothing.
  const cancel = useCallback(() => {
    const s = sessionRef.current;
    if (!s || s.finishing) return;
    s.finishing = true;
    if (s.recognition) { try { s.recognition.abort(); } catch { /* ignore */ } s.recognition = null; }
    analyserRef.current = null;
    stopCapture(s);
    sessionRef.current = null;
    setState("idle"); setLevel(0); setHint(null);
  }, []);

  const start = useCallback(async () => {
    if (sessionRef.current) return;
    // Made inside the tap itself: created after the permission prompt, Chrome may start it
    // paused, and a paused meter hears only silence.
    let audio = null;
    try { audio = new AudioContext(); } catch { /* no Web Audio: no meter */ }

    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
      });
    } catch {
      if (audio) audio.close().catch(() => {});
      await onResultRef.current("");                 // no microphone: the nurse gets the press
      return;
    }

    const now0 = performance.now();
    const s = {
      stream, audio, chunks: [], heard: false, lastLoud: now0,
      browserText: "", recognition: null, recognitionEnded: null, recorder: null, stopped: null,
    };
    sessionRef.current = s;

    // Recorder for ElevenLabs.
    try {
      const type = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find((m) => MediaRecorder.isTypeSupported(m));
      s.recorder = new MediaRecorder(stream, { ...(type ? { mimeType: type } : {}), audioBitsPerSecond: 128000 });
      s.recorder.ondataavailable = (e) => { if (e.data.size) s.chunks.push(e.data); };
      s.stopped = new Promise((resolve) => { s.recorder.onstop = resolve; });
      s.recorder.start();
    } catch { s.recorder = null; }

    // Chrome speech recognition in parallel, as the fallback transcript.
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (Recognition) {
      try {
        const r = new Recognition();
        r.lang = langTag; r.continuous = true; r.interimResults = true;
        r.onresult = (e) => {
          let interim = "";
          for (let i = e.resultIndex; i < e.results.length; i++) {
            if (e.results[i].isFinal) s.browserText += " " + e.results[i][0].transcript;
            else interim += " " + e.results[i][0].transcript;
          }
          // The browser only knows one language, so its live guess is shown only without ElevenLabs.
          if (!serverSpeechRef.current) setHeard((s.browserText + interim).trim());
        };
        r.onerror = () => {};
        s.recognitionEnded = new Promise((resolve) => { r.onend = resolve; });
        r.start();
        s.recognition = r;
      } catch { s.recognition = null; }
    }

    if (!s.recorder && !s.recognition) {
      stopCapture(s); sessionRef.current = null;
      await onResultRef.current("");
      return;
    }

    // Loudness meter: drives the waves, the hint and the silence cut-off.
    try {
      s.audio = s.audio || new AudioContext();
      if (s.audio.state === "suspended") s.audio.resume().catch(() => {});
      const analyser = s.audio.createAnalyser();
      analyser.fftSize = 1024;
      analyser.smoothingTimeConstant = 0.6;
      s.audio.createMediaStreamSource(stream).connect(analyser);
      s.analyser = analyser;
      analyserRef.current = analyser;
      const buf = new Float32Array(analyser.fftSize);
      let smooth = 0;
      s.meter = setInterval(() => {
        analyser.getFloatTimeDomainData(buf);
        let sum = 0;
        for (const v of buf) sum += v * v;
        const rms = Math.sqrt(sum / buf.length);
        const db = 20 * Math.log10(rms || 1e-6);
        const raw = Math.max(0, Math.min(1, (db - FLOOR_DB) / (FULL_DB - FLOOR_DB)));
        smooth = Math.max(raw, smooth * 0.85);          // fast attack, slow release
        const now = performance.now();
        setLevel(smooth);

        if (raw > SPEECH_LEVEL) { s.heard = true; s.lastLoud = now; }
        if (now - s.lastLoud > QUIET_HINT_MS) setHint("quiet");
        else if (s.heard) setHint("good");
        if (debug) {
          setDebugText(`audio ${s.audio.state} · mic ${stream.getAudioTracks()[0]?.muted ? "MUTED" : "on"} · ${db.toFixed(0)} dB · level ${smooth.toFixed(2)}`);
        }
        if (s.heard && now - s.lastLoud > SILENCE_MS) finishRef.current();
      }, 50);
    } catch (err) {
      if (debug) setDebugText("meter failed: " + err);   // the 10 s limit and the second tap still stop it
    }

    s.limit = setTimeout(() => finishRef.current(), MAX_LISTEN_MS);
    setHeard("");
    setHint(null);
    setState("listening");
  }, [langTag, debug]);

  // Leaving the page never leaves the microphone on.
  useEffect(() => () => { if (sessionRef.current) stopCapture(sessionRef.current); }, []);

  return { state, level, hint, heard, serverSpeech, debugText, start, finish, cancel, analyser: analyserRef };
}
