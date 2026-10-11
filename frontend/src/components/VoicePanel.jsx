import { useCallback, useRef } from "react";
import MicButton from "./MicButton.jsx";
import ListeningOverlay from "./ListeningOverlay.jsx";
import { QuickIcon } from "./Icons.jsx";

// The four most common requests, one tap each, for when speaking is hard.
const SHORTCUTS = ["water", "blanket", "pillow", "tv"];

/* Voice mode. The page shows one scarlet mic; tapping it opens the full-screen
   listening view, which closes by itself once the request has been sent. */
export default function VoicePanel({ voice, busy, t, onQuick }) {
  const { state } = voice;
  const micRef = useRef(null);
  const close = useCallback(() => { voice.cancel(); micRef.current?.focus(); }, [voice]);

  return (
    <div className="voice-panel" role="tabpanel" id="panel-voice" aria-labelledby="tab-voice">
      <MicButton ref={micRef} state="idle" level={0} label={t.speak}
                 disabled={state !== "idle" || busy} onPress={voice.start}>
        <div className="voice-text">
          <p className="voice-label">{busy ? t.sending : t.speak}</p>
          <p className="voice-sub">{t.speakSub}</p>
        </div>
      </MicButton>
      <div className="shortcuts" role="group" aria-label={t.quickTitle}>
        <p className="shortcuts-title">{t.quickTitle}</p>
        <div className="shortcuts-row">
          {t.quick.filter((q) => SHORTCUTS.includes(q[3])).map(([dept, label, phrase, icon]) => (
            <button key={icon} type="button" disabled={busy || state !== "idle"}
                    style={{ "--stripe": `var(--${dept})` }} onClick={() => onQuick({ text: phrase })}>
              <span className="quick-icon"><QuickIcon name={icon} /></span>
              <span>{label}</span>
            </button>
          ))}
        </div>
      </div>
      {state !== "idle" && <ListeningOverlay voice={voice} t={t} onClose={close} />}
    </div>
  );
}
