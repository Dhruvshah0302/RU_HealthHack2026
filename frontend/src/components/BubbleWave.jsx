import { useEffect, useRef } from "react";

/* A soft bubble around the mic button that moves with the sound the microphone hears.
   Its outline is drawn from the live frequencies, so any sound makes it wobble and a
   speaking voice makes it swell. Small bubbles float out of it while there is sound
   (more and bigger when louder), and a last handful bursts out when listening stops.
   It reads the analyser directly every animation frame (no React re-render per frame)
   and settles back to a still circle when listening stops. */

const POINTS = 72;            // points around the outline
const BANDS = 6;              // sound is grouped into a few bands, so the outline stays round and smooth
const LOW_BIN = 2;            // ~90 Hz: skip hum below the voice
const HIGH_BIN = 90;          // ~4 kHz: the top of most speech energy
const NOISE_FLOOR = 18;       // 0..255 frequency value treated as silence
const SWELL = 0.34;           // how far a full-volume band pushes the outline (x radius)
const CANVAS_SCALE = 2.6;     // canvas size / button size; must match .bubble in patient.css
const MAX_BUBBLES = 70;
const BURST = 16;             // bubbles released when listening stops

// Band edges spaced on a log scale, as hearing is: more detail in the low voice range.
const EDGES = Array.from({ length: BANDS + 1 }, (_, i) =>
  Math.round(LOW_BIN * Math.pow(HIGH_BIN / LOW_BIN, i / BANDS)));

export default function BubbleWave({ analyser, active }) {
  const canvasRef = useRef(null);
  const activeRef = useRef(active);
  activeRef.current = active;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return undefined;
    const ctx = canvas.getContext("2d");
    const amps = new Float32Array(POINTS);          // smoothed loudness per outline point
    const bands = new Float32Array(BANDS);
    let freq = null;
    let frame = 0;
    let running = false;
    let energy = 0;                                  // smoothed overall loudness, 0..1
    let bubbles = [];                                // the small bubbles floating out
    let toEmit = 0;                                  // fractional bubbles owed to the emitter
    let lastTime = 0;
    let wasActive = false;

    // A new small bubble on the edge of the big one, drifting outward and up.
    function spawn(cx, cy, r0, edge, strength, burst = false) {
      const a = burst
        ? Math.random() * Math.PI * 2
        : -Math.PI / 2 + (Math.random() - 0.5) * Math.PI * 1.6;      // mostly from the top half
      const speed = r0 * (burst ? 0.9 + Math.random() * 0.6 : 0.2 + strength * 0.9 + Math.random() * 0.25);
      bubbles.push({
        x: cx + Math.cos(a) * r0 * edge, y: cy + Math.sin(a) * r0 * edge,
        vx: Math.cos(a) * speed, vy: Math.sin(a) * speed,
        r: r0 * (0.025 + Math.random() * 0.045 + strength * 0.06),
        age: 0, life: burst ? 0.7 + Math.random() * 0.4 : 1.1 + Math.random() * 1.1,
        phase: Math.random() * Math.PI * 2,
      });
      if (bubbles.length > MAX_BUBBLES) bubbles.shift();
    }

    function drawBubbles(dt, r0) {
      bubbles = bubbles.filter((b) => (b.age += dt) < b.life);
      for (const b of bubbles) {
        b.vy -= r0 * 0.4 * dt;                         // bubbles rise
        b.vx *= 1 - 0.9 * dt; b.vy *= 1 - 0.6 * dt;    // and slow down in the "water"
        b.x += (b.vx + Math.sin(b.phase + b.age * 7) * r0 * 0.12) * dt;
        b.y += b.vy * dt;

        const k = b.age / b.life;
        const popping = k > 0.85;                      // the last moment: a quick pop
        const fade = popping ? 1 - (k - 0.85) / 0.15 : Math.min(1, b.age * 6);
        const r = b.r * (1 + k * 0.6 + (popping ? (k - 0.85) * 5 : 0));

        ctx.beginPath();
        ctx.arc(b.x, b.y, r, 0, Math.PI * 2);
        if (!popping) { ctx.fillStyle = `rgba(204, 0, 51, ${0.14 * fade})`; ctx.fill(); }
        ctx.lineWidth = Math.max(1, r * (popping ? 0.12 : 0.22));
        ctx.strokeStyle = `rgba(204, 0, 51, ${0.6 * fade})`;
        ctx.stroke();
        if (!popping) {                                // the shine that makes it a bubble
          ctx.beginPath();
          ctx.arc(b.x - r * 0.3, b.y - r * 0.3, r * 0.28, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(255, 255, 255, ${0.8 * fade})`;
          ctx.fill();
        }
      }
    }

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      const { width, height } = canvas.getBoundingClientRect();
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    resize();

    // Smooth closed curve through the points (Catmull-Rom turned into Bezier segments).
    function outline(points) {
      ctx.beginPath();
      const n = points.length;
      for (let i = 0; i < n; i++) {
        const p0 = points[(i - 1 + n) % n], p1 = points[i], p2 = points[(i + 1) % n], p3 = points[(i + 2) % n];
        if (i === 0) ctx.moveTo(p1[0], p1[1]);
        ctx.bezierCurveTo(
          p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6,
          p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6,
          p2[0], p2[1],
        );
      }
      ctx.closePath();
    }

    function draw(time) {
      const t = time / 1000;
      const w = canvas.width, h = canvas.height;
      const cx = w / 2, cy = h / 2;
      const r0 = w / (2 * CANVAS_SCALE);             // the button's radius, in canvas pixels
      const active = activeRef.current;
      const node = active ? analyser?.current : null;
      const dt = lastTime ? Math.min(0.05, t - lastTime) : 0;
      lastTime = t;

      // 1. Read the sound: one target per outline point, mirrored so the bubble stays balanced.
      let total = 0;
      if (node) {
        if (!freq || freq.length !== node.frequencyBinCount) freq = new Uint8Array(node.frequencyBinCount);
        node.getByteFrequencyData(freq);
      }
      for (let b = 0; b < BANDS; b++) {
        let sum = 0, n = 0;
        if (node) for (let k = EDGES[b]; k < Math.max(EDGES[b + 1], EDGES[b] + 1); k++) { sum += freq[k]; n++; }
        const v = n ? Math.max(0, sum / n - NOISE_FLOOR) / (255 - NOISE_FLOOR) : 0;
        bands[b] = Math.pow(v, 0.7);                 // lifts quiet sounds so they still show
      }
      // Bands go around the circle and back (low, ..., high, ..., low), blended with a cosine
      // curve between neighbours, so the bubble swells in soft lobes instead of spikes.
      const segments = BANDS * 2;
      for (let i = 0; i < POINTS; i++) {
        const pos = (i / POINTS) * segments;
        const j = Math.floor(pos), f = pos - j;
        const band = (s) => { const m = ((s % segments) + segments) % segments; return bands[m < BANDS ? m : segments - 1 - m]; };
        const mix = (1 - Math.cos(f * Math.PI)) / 2;
        const target = band(j) * (1 - mix) + band(j + 1) * mix;
        // fast attack, slower release: reacts at once, relaxes smoothly
        amps[i] += (target - amps[i]) * (target > amps[i] ? 0.45 : 0.12);
        total += amps[i];
      }
      const avg = total / POINTS;
      energy += (avg - energy) * 0.2;

      // 2. Draw three layers: a wide faint bubble, the main bubble, and a bright inner one.
      ctx.clearRect(0, 0, w, h);
      const layers = [
        { scale: 1.35, alpha: 0.10, wobble: 1.4 },
        { scale: 1.0, alpha: 0.20, wobble: 1.0 },
        { scale: 0.55, alpha: 0.30, wobble: 0.6 },
      ];
      for (const layer of layers) {
        const points = [];
        for (let i = 0; i < POINTS; i++) {
          const a = (i / POINTS) * Math.PI * 2 + t * 0.25 * layer.wobble;
          const breathe = (Math.sin(a * 3 + t * 1.7) * 0.012 + Math.sin(a * 5 - t * 2.4) * 0.008)
                          * (0.4 + energy * 6) * layer.wobble;
          const r = r0 * (1 + 0.03 + amps[i] * SWELL * layer.scale + breathe);
          points.push([cx + Math.cos(a) * r, cy + Math.sin(a) * r]);
        }
        outline(points);
        const fill = ctx.createRadialGradient(cx, cy, r0 * 0.8, cx, cy, r0 * (1.2 + SWELL * layer.scale));
        fill.addColorStop(0, `rgba(204, 0, 51, ${layer.alpha + energy * 0.25})`);
        fill.addColorStop(1, "rgba(204, 0, 51, 0)");
        ctx.fillStyle = fill;
        ctx.fill();
        ctx.lineWidth = Math.max(1, w / 260);
        ctx.strokeStyle = `rgba(204, 0, 51, ${0.18 + energy * 0.5})`;
        ctx.stroke();
      }

      // 3. Small bubbles float out while there is sound; a last handful bursts out at the end.
      if (active && node) {
        toEmit += dt * (energy > 0.01 ? 1.5 + energy * 30 : 0);
        while (toEmit >= 1) { toEmit -= 1; spawn(cx, cy, r0, 1.05 + energy * 0.3, energy); }
      }
      if (wasActive && !active) for (let i = 0; i < BURST; i++) spawn(cx, cy, r0, 1.05, 0.5, true);
      wasActive = active;
      drawBubbles(dt, r0);

      // 4. A small shine, so it reads as a bubble rather than a flat ring.
      const shine = r0 * (1.08 + energy * 0.3);
      ctx.beginPath();
      ctx.arc(cx, cy, shine, Math.PI * 1.08, Math.PI * 1.38);
      ctx.lineWidth = Math.max(2, w / 110);
      ctx.lineCap = "round";
      ctx.strokeStyle = `rgba(255, 255, 255, ${0.35 + energy * 0.4})`;
      ctx.stroke();

      // Stop drawing once listening has ended and the bubble has settled.
      if (!active && energy < 0.002 && bubbles.length === 0 && amps.every((v) => v < 0.002)) {
        ctx.clearRect(0, 0, w, h);
        running = false;
        lastTime = 0;
        return;
      }
      frame = requestAnimationFrame(draw);
    }

    const tick = () => {
      if (!running) { running = true; frame = requestAnimationFrame(draw); }
    };
    tick();
    const poll = setInterval(() => { if (activeRef.current) tick(); }, 150);

    return () => {
      cancelAnimationFrame(frame);
      clearInterval(poll);
      observer.disconnect();
    };
  }, [analyser]);

  return <canvas ref={canvasRef} className={`bubble ${active ? "on" : ""}`} aria-hidden="true" />;
}
