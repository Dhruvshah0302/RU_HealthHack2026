import { useCallback, useEffect, useRef, useState } from "react";
import ModeSwitch from "../components/ModeSwitch.jsx";
import VoicePanel from "../components/VoicePanel.jsx";
import TypePanel from "../components/TypePanel.jsx";
import Confirmation from "../components/Confirmation.jsx";
import Pennant from "../components/Pennant.jsx";
import { useVoiceCapture } from "../hooks/useVoiceCapture.js";
import { submitRequest } from "../lib/api.js";
import { T } from "../lib/i18n.js";
import { room, langTag, lang, initialMode, DEBUG } from "../lib/params.js";

/* Bedside page. Rules it keeps:
   - room and language come from the address (?room=412&lang=es)
   - never shows priority, never says a person was notified
   - any failure sends the request to the nurse (direct_nurse=true) */
export default function PatientPage() {
  const t = T[lang];
  const [mode, setMode] = useState(initialMode);      // "voice" | "type"
  const [view, setView] = useState("ask");            // "ask" | "done"
  const [tickets, setTickets] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState(null);
  const [said, setSaid] = useState(null);             // what the patient said, for the confirmation
  const textRef = useRef(null);

  useEffect(() => {
    document.documentElement.lang = lang;
    document.title = t.title;
  }, [t]);

  const submit = useCallback(async ({ text: words = "", direct_nurse = false }) => {
    setProblem(null);
    if (!direct_nurse && !words.trim()) {
      setProblem(t.empty);
      textRef.current?.focus();
      return;
    }
    setBusy(true);
    try {
      const data = await submitRequest({ room, text: words, direct_nurse });
      setTickets(data.tickets);
      setText("");                 // so a later nurse press never carries an old request
      setView("done");
    } catch {
      setProblem(t.failed);
    } finally {
      setBusy(false);
    }
  }, [t]);

  // Nothing understood ("") goes to the nurse, as a call bell does today.
  const voice = useVoiceCapture({
    langTag, debug: DEBUG,
    onResult: (heard, language) => {
      setSaid(heard ? { text: heard, language } : null);
      return submit(heard ? { text: heard } : { direct_nurse: true });
    },
  });

  function changeMode(next) {
    if (next !== "voice") voice.cancel();
    setProblem(null);
    setMode(next);
    if (next === "type") setTimeout(() => textRef.current?.focus(), 0);
  }

  function callNurse() {
    voice.cancel();
    submit({ text: mode === "type" ? text : "", direct_nurse: true });
  }

  return (
    <>
      {DEBUG && voice.debugText && <pre className="debug">{voice.debugText}</pre>}
      <div className="app">
      <Pennant room={room} lang={lang} t={t} onNurse={callNurse} />

      <div className="content">
      <div className="topbar">
        {view === "ask" && <ModeSwitch mode={mode} onChange={changeMode} t={t} />}
      </div>

      <main>
        {view === "ask" ? (
          <section className="ask">
            <h1>{t.title}</h1>
            {mode === "voice"
              ? <VoicePanel voice={voice} busy={busy} t={t} onQuick={submit} />
              : <TypePanel ref={textRef} text={text} onText={setText} onSubmit={submit} busy={busy} t={t} />}
            {problem && <p className="problem" role="alert">{problem}</p>}
          </section>
        ) : (
          <Confirmation tickets={tickets} t={t} said={mode === "voice" ? said : null}
                        onAgain={() => { setView("ask"); setProblem(null); setSaid(null); }} />
        )}
      </main>
      </div>
      </div>
    </>
  );
}
