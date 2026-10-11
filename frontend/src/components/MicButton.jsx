import { forwardRef, useEffect, useRef, useState } from "react";
import { MicIcon } from "./Icons.jsx";
import BubbleWave from "./BubbleWave.jsx";

/* The scarlet mic button. While listening, a bubble around it moves with the sound the
   microphone hears (BubbleWave), small bubbles float out, and ripples spread from it:
   any sound sends small, faint ripples; a good speaking voice sends big, frequent ones.
   `big` is the full-screen listening view; without it, the button on the page. */
const MicButton = forwardRef(function MicButton(
  { state, level, analyser, label, disabled, onPress, big = false, children }, ref,
) {
  const [waves, setWaves] = useState([]);
  const lastWave = useRef(0);
  const nextId = useRef(0);

  useEffect(() => {
    if (state !== "listening") return;
    const now = performance.now();
    // any sound starts ripples; louder sound sends them more often (every ~140 ms at full voice, ~600 ms when faint)
    if (level > 0.03 && now - lastWave.current > 600 - level * 460) {
      lastWave.current = now;
      const wave = { id: nextId.current++, peak: 1.22 + level * 0.5, alpha: 0.4 + level * 0.5 };
      setWaves((list) => [...list.slice(-7), wave]);
    }
  }, [level, state]);

  useEffect(() => { if (state === "idle") setWaves([]); }, [state]);

  const drop = (id) => setWaves((list) => list.filter((w) => w.id !== id));

  return (
    <div className={`stage ${state} ${big ? "big" : ""}`} style={{ "--level": level.toFixed(3) }}>
      <div className="mic-wrap">
        <span className="halo" aria-hidden="true" />
        <span className="invite" aria-hidden="true" />
        {big && <BubbleWave analyser={analyser} active={state === "listening"} />}
        <div className="waves" aria-hidden="true">
          {waves.map((w) => (
            <span key={w.id} className="wave" onAnimationEnd={() => drop(w.id)}
                  style={{ "--peak": w.peak.toFixed(2), "--alpha": w.alpha.toFixed(2) }} />
          ))}
        </div>
        <button ref={ref} className="mic" type="button" aria-label={label} disabled={disabled} onClick={onPress}>
          <MicIcon />
        </button>
      </div>
      {children}
    </div>
  );
});

export default MicButton;
