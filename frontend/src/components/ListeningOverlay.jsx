import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import MicButton from "./MicButton.jsx";
import { CloseIcon } from "./Icons.jsx";
import { EXAMPLES } from "../lib/i18n.js";

/* Full-screen listening view, like voice search on YouTube: opens when the patient taps the
   mic, shows their words as they speak, and closes on its own once the request is sent.
   Tap the mic to finish early; Close or Escape stops listening and sends nothing.
   The nurse button stays on top of this screen (z-index in patient.css). */
export default function ListeningOverlay({ voice, t, onClose }) {
  const { state, level, hint, heard, serverSpeech, analyser } = voice;
  const [example, setExample] = useState(0);
  useEffect(() => {
    if (!serverSpeech) return undefined;
    const timer = setInterval(() => setExample((i) => (i + 1) % EXAMPLES.length), 1800);
    return () => clearInterval(timer);
  }, [serverSpeech]);
  const micRef = useRef(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    const previous = document.activeElement;
    micRef.current?.focus();
    const onKey = (e) => { if (e.key === "Escape") closeRef.current(); };
    document.addEventListener("keydown", onKey);
    document.body.classList.add("overlay-open");
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.classList.remove("overlay-open");
      previous?.focus?.();
    };
  }, []);

  const title = state === "working" ? t.working : t.listening;
  let sub = state === "listening" ? t.listeningSub : "";
  let tone = "";
  if (state === "listening" && hint === "quiet") { sub = t.louder; tone = "quiet"; }
  if (state === "listening" && hint === "good" && !heard) { sub = t.good; tone = "good"; }

  return createPortal(
    <div className={`overlay ${state}`} role="dialog" aria-modal="true" aria-label={title}>
      <button className="overlay-close" type="button" onClick={onClose} aria-label={t.close}>
        <CloseIcon />
      </button>

      <div className="overlay-words" aria-live="polite">
        <p className="overlay-title">{title}<span className="dots" aria-hidden="true"><i /><i /><i /></span></p>
        {heard
          ? <p className="overlay-heard has">{heard}</p>
          : <p key={serverSpeech ? example : "x"} className="overlay-heard example">
              {serverSpeech ? EXAMPLES[example] : t.example}
            </p>}
      </div>

      <div className="overlay-stage">
        <MicButton ref={micRef} big state={state} level={level} analyser={analyser}
                   label={state === "listening" ? t.finish : t.working}
                   disabled={state === "working"} onPress={voice.finish} />
      </div>

      <p className={`overlay-sub ${tone}`} aria-live="polite">{sub}</p>
    </div>,
    document.body,
  );
}
