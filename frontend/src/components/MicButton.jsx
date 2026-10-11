import { useEffect, useRef, useState } from "react";
import { MicIcon } from "./Icons.jsx";

/* The big red button. While listening, each wave is sized and coloured by how loud the
   patient is right now: quiet speech sends small, faint, slow ripples; a good speaking voice
   sends big, strong, frequent ones that pass the dashed guide circle. */
export default function MicButton({ state, level, label, disabled, onPress, children }) {
  const [waves, setWaves] = useState([]);
  const lastWave = useRef(0);
  const nextId = useRef(0);

  useEffect(() => {
    if (state !== "listening") return;
    const now = performance.now();
    // louder voice: waves come more often (every ~140 ms at full voice, ~600 ms when faint)
    if (level > 0.08 && now - lastWave.current > 600 - level * 460) {
      lastWave.current = now;
      const wave = { id: nextId.current++, peak: 1.22 + level * 0.5, alpha: 0.4 + level * 0.5 };
      setWaves((list) => [...list.slice(-7), wave]);
    }
  }, [level, state]);

  useEffect(() => { if (state === "idle") setWaves([]); }, [state]);

  const drop = (id) => setWaves((list) => list.filter((w) => w.id !== id));

  return (
    <div className={`stage ${state}`} style={{ "--level": level.toFixed(3) }}>
      <div className="mic-wrap">
        <span className="halo" aria-hidden="true" />
        <div className="waves" aria-hidden="true">
          {waves.map((w) => (
            <span key={w.id} className="wave" onAnimationEnd={() => drop(w.id)}
                  style={{ "--peak": w.peak.toFixed(2), "--alpha": w.alpha.toFixed(2) }} />
          ))}
        </div>
        <span className="guide" aria-hidden="true" />
        <button className="mic" type="button" aria-label={label} disabled={disabled} onClick={onPress}>
          <MicIcon />
        </button>
      </div>
      {children}
    </div>
  );
}
