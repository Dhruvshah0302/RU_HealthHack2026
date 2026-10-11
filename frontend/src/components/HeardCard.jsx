import { useEffect, useRef, useState } from "react";

/* What the patient said, on the screen.
   Words heard (from ElevenLabs): shown and sent at the same moment; the backend's model
   sorts them into a team. Nothing heard: the patient can try again; if they do nothing,
   the press still goes to the nurse, as a call bell does today. */
const NURSE_AFTER = 10;

export default function HeardCard({ heard, onSend, onRetry, busy, t }) {
  const understood = Boolean(heard.text);
  const [left, setLeft] = useState(NURSE_AFTER);
  const sent = useRef(false);
  const primaryRef = useRef(null);

  const send = () => {
    if (sent.current) return;
    sent.current = true;
    onSend(understood ? { text: heard.text } : { direct_nurse: true });
  };

  // Words: send straight away, while they are on the screen.
  useEffect(() => { if (understood) send(); else primaryRef.current?.focus(); }, []);   // eslint-disable-line react-hooks/exhaustive-deps

  // Nothing heard: count down to the nurse.
  useEffect(() => {
    if (understood) return undefined;
    if (left <= 0) { send(); return undefined; }
    const timer = setTimeout(() => setLeft((n) => n - 1), 1000);
    return () => clearTimeout(timer);
  });

  let engine = "";
  if (heard.source === "elevenlabs") engine = t.viaEleven;
  else if (heard.source === "browser") engine = `${t.viaBrowser}${heard.elevenError ? ` (${t.elevenSaid} ${heard.elevenError})` : ""}`;
  else if (heard.noMic) engine = t.noMic;
  else if (heard.elevenError) engine = `${t.elevenSaid} ${heard.elevenError}`;

  if (understood) {
    return (
      <div className="heard ok" role="status" aria-live="polite">
        <p className="heard-label">{t.youSaid}</p>
        <p className="heard-text">“{heard.text}”</p>
        {engine && <p className="heard-engine">{engine}</p>}
        <p className="heard-count">{t.sendingNow}</p>
      </div>
    );
  }

  return (
    <div className="heard empty" role="status" aria-live="polite">
      <p className="heard-text">{t.notHeard}</p>
      {engine && <p className="heard-engine">{engine}</p>}
      <p className="heard-count">{t.nurseIn.replace("{n}", left)}</p>
      <div className="heard-actions">
        <button type="button" className="heard-retry" onClick={onRetry} disabled={busy}>{t.sayAgain}</button>
        <button ref={primaryRef} type="button" className="heard-send" onClick={send} disabled={busy}>{t.nurseNow}</button>
      </div>
    </div>
  );
}
