import { useState } from "react";
import { LEVELS, isOverdue, minutesWaiting } from "../levels.js";

function waited(min) {
  if (min < 1) return "just now";
  if (min < 60) return `${Math.floor(min)} min`;
  return `${Math.floor(min / 60)} h ${Math.floor(min % 60)} min`;
}

const MAX_NOTES = 2;
const SORTED_BY = { llm: "Sorted by AI (Bedrock)", baseline: "Sorted by keyword fallback", none: "Nurse button" };

/* Every ticket has the same size and the same layout, whatever the team:
   room | priority | waiting time, then the request, then the action at the bottom.
   Long text is cut to fit; the full text is in the tooltip. */
export default function TicketCard({ ticket, team, level, now, onStatus }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const overdue = isOverdue(ticket, level, now);
  const next = ["done", "Close ticket"];                 // one step: closing a ticket marks it done
  const away = ticket.status === "waiting_for_patient";
  const notes = ticket.notes || [];
  const said = ticket.original_text && ticket.original_text !== ticket.summary ? ticket.original_text : "";

  async function press() {
    setBusy(true); setError(null);
    try { await onStatus(ticket.id, next[0]); } catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  const cls = ["ticket", `level-${level}`, ticket.status, overdue ? "overdue" : ""].join(" ");
  return (
    <article className={cls} style={{ "--team": team.color }} aria-label={`Room ${ticket.room}, ${LEVELS[level].name}, ${team.name}`}>
      <div className="ticket-top">
        <div className="room"><small>Room</small>{ticket.room}</div>
        <span className={`level-badge l${level}`}>{LEVELS[level].badge}</span>
        <span className={`waited ${overdue ? "late" : ""}`}>
          {overdue && <span className="late-label">Overdue</span>}
          {waited(minutesWaiting(ticket, now))}
        </span>
      </div>

      <div className="ticket-body">
        {team.unknownCode && <p className="team-tag clamp-1">Sent to unknown team “{team.unknownCode}”, shown here so it is not missed</p>}
        {ticket.patient_name && <p className="patient-name clamp-1">{ticket.patient_name}</p>}
        <p className="summary clamp-2" title={ticket.summary}>{ticket.summary}</p>
        {said && <p className="said clamp-2" title={said}>Patient said: “{said}”</p>}
        {notes.length > 0 && (
          <ul className="notes" title={notes.join("\n")}>
            {notes.slice(0, MAX_NOTES).map((n) => <li key={n} className="clamp-1">{n}</li>)}
            {notes.length > MAX_NOTES && <li className="more">+{notes.length - MAX_NOTES} more</li>}
          </ul>
        )}
        {team.group === "clinical" && ticket.reasons?.length > 0 && (
          <p className="why clamp-1" title={ticket.reasons.join("; ")}>Why: {ticket.reasons.join("; ")}</p>
        )}
        {away && <p className="away clamp-1">Patient is off the unit. Waits until they are back.</p>}
      </div>

      <div className="ticket-actions">
        {ticket.classified_by && !error && ticket.status !== "acknowledged" && (
          <span className="sorted-by">{SORTED_BY[ticket.classified_by] || ticket.classified_by}</span>
        )}
        {error ? <span className="ticket-error clamp-1" role="alert">{error}</span>
               : ticket.status === "acknowledged" && <span className="state">On it</span>}
        <button type="button" className="act" onClick={press} disabled={busy}>{next[1]}</button>
      </div>
    </article>
  );
}
