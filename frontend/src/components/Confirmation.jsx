import { useEffect, useRef } from "react";

// "Housekeeping has your request." Never a priority, never "someone was notified".
export default function Confirmation({ tickets, onAgain, t }) {
  const againRef = useRef(null);
  useEffect(() => { againRef.current?.focus(); }, []);

  return (
    <section className="done" aria-live="polite">
      <h1>{t.doneTitle}</h1>
      <ul className="sent">
        {tickets.map((ticket) => (
          <li key={ticket.id} style={{ "--stripe": `var(--${ticket.department})` }}>
            {`${t.dept[ticket.department] || t.dept.nurse} ${t.has}`}
          </li>
        ))}
      </ul>
      <button ref={againRef} className="again" type="button" onClick={onAgain}>{t.again}</button>
    </section>
  );
}
