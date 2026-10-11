/* Priority levels and time targets from SPEC.md ("The targets are placeholders. A hospital sets its own").
   Tickets carry `level` once the backend adds it; until then it is derived from `priority`. */
export const LEVELS = {
  1: { name: "Emergency", badge: "Emergency", targetMin: 0 },
  2: { name: "Urgent", badge: "Urgent", targetMin: 2 },
  3: { name: "Routine clinical", badge: "Routine", targetMin: 10 },
  4: { name: "Non-clinical", badge: "Routine", targetMin: 15 },
};

export function levelOf(ticket, team) {
  if (ticket.level) return ticket.level;
  if (ticket.priority === "urgent") return 2;
  return team.group === "clinical" ? 3 : 4;
}

export function minutesWaiting(ticket, now = Date.now()) {
  return Math.max(0, (now / 1000 - ticket.created_at) / 60);
}

// Only open tickets go overdue; "On it" stops the clock for this view.
export function isOverdue(ticket, level, now = Date.now()) {
  if (ticket.status !== "open") return false;
  const target = LEVELS[level]?.targetMin ?? 15;
  return minutesWaiting(ticket, now) > Math.max(target, 1);
}
