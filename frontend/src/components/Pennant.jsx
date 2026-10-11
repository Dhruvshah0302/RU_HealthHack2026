import { useEffect, useState } from "react";
import { SHIELD_PATH } from "./Icons.jsx";
import NurseBar from "./NurseBar.jsx";

/* The scarlet pennant: the patient's anchor on every screen.
   Room number on a shield, a greeting and the time (patients in hospital lose track of it),
   and the nurse button, which never moves. Tall on the left on a tablet or laptop; a banner
   across the top on a phone, where the nurse button docks to the bottom instead (patient.css). */
export default function Pennant({ room, lang, t, onNurse }) {
  const now = useNow();
  const hour = now.getHours();
  const greet = hour < 12 ? t.morning : hour < 18 ? t.afternoon : t.evening;
  const locale = lang === "es" ? "es-US" : "en-US";

  return (
    <aside className="pennant">
      <svg className="pennant-mark" viewBox="0 0 24 24" aria-hidden="true"><path d={SHIELD_PATH} /></svg>

      <div className="crest" aria-label={`${t.room} ${room}`}>
        <svg className="crest-shield" viewBox="0 0 24 24" aria-hidden="true"><path d={SHIELD_PATH} /></svg>
        <span className="crest-label">{t.room}</span>
        <b className="crest-number">{room}</b>
      </div>

      <div className="hello">
        <p className="greet">{greet}</p>
        <p className="clock">{now.toLocaleTimeString(locale, { hour: "numeric", minute: "2-digit" })}</p>
        <p className="day">{now.toLocaleDateString(locale, { weekday: "long", month: "long", day: "numeric" })}</p>
      </div>

      <NurseBar onPress={onNurse} t={t} />
    </aside>
  );
}

function useNow() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 20000);
    return () => clearInterval(timer);
  }, []);
  return now;
}
