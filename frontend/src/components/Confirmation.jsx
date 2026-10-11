import { useEffect, useRef } from "react";
import { CheckMark, TeamIcon } from "./Icons.jsx";

// "Housekeeping has your request." Never a priority, never "someone was notified".
function languageName(code, t) {
  try { return new Intl.DisplayNames([t === undefined ? "en" : t.locale || "en"], { type: "language" }).of(code); }
  catch { return code; }
}
export default function Confirmation({ tickets, onAgain, t, said }) {
  const againRef = useRef(null);
  useEffect(() => { againRef.current?.focus(); }, []);

  return (
    <section className="done" aria-live="polite">
      <CheckMark className="check" />
      <h1>{t.doneTitle}</h1>
      {said && (
        <figure className="said">
          <figcaption>{t.youSaid}{said.language ? ` (${languageName(said.language, t)})` : ""}</figcaption>
          <blockquote>“{said.text}”</blockquote>
        </figure>
      )}
      <ul className="sent">
        {tickets.map((ticket, i) => (
          <li key={ticket.id} style={{ "--stripe": `var(--${ticket.department})`, "--i": i }}>
            <span className="team-icon"><TeamIcon dept={ticket.department} /></span>
            <span>{`${t.dept[ticket.department] || t.dept.nurse} ${t.has}`}</span>
          </li>
        ))}
      </ul>
      <button ref={againRef} className="again" type="button" onClick={onAgain}>{t.again}</button>
    </section>
  );
}
