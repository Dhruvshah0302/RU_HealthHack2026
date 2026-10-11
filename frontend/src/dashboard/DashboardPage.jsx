import { useCallback, useEffect, useMemo, useState } from "react";
import TeamSwitch from "./components/TeamSwitch.jsx";
import TicketCard from "./components/TicketCard.jsx";
import { DEPARTMENTS, findTeam, teamFor } from "./departments.js";
import { isOverdue, levelOf } from "./levels.js";
import { loadTickets, setStatus, subscribe } from "./feed.js";
import "./dashboard.css";

/* Staff screen, one team at a time. A patient's request (voice through ElevenLabs, or typed)
   is turned into one or more tickets by the backend and routed to a team; each team works
   from its own screen. The page takes the team's colour, so it is clear whose screen it is.
   ?team=food_services opens on that team. */
const params = new URLSearchParams(window.location.search);
const startTeam = findTeam(params.get("team")) ? params.get("team") : DEPARTMENTS[0].key;

export default function DashboardPage() {
  const [tickets, setTickets] = useState(new Map());
  const [stats, setStats] = useState(null);
  const [team, setTeam] = useState(startTeam);
  const [link, setLink] = useState("connecting");      // connecting | live | down
  const [loadError, setLoadError] = useState(null);
  const [fresh, setFresh] = useState(new Set());
  const [now, setNow] = useState(Date.now());

  // Every ticket this screen has seen (open or done), by id. Used for a team's total when the
  // backend does not send stats.by_department yet.
  const [seen, setSeen] = useState(new Map());
  const remember = useCallback((list) => setSeen((m) => {
    const next = new Map(m);
    list.forEach((t) => next.set(t.id, t.department));
    return next;
  }), []);

  const apply = useCallback((ticket, isNew) => {
    remember([ticket]);
    setTickets((map) => {
      const next = new Map(map);
      if (ticket.status === "done") next.delete(ticket.id); else next.set(ticket.id, ticket);
      return next;
    });
    if (isNew) {
      setFresh((s) => new Set(s).add(ticket.id));
      setTimeout(() => setFresh((s) => { const n = new Set(s); n.delete(ticket.id); return n; }), 4000);
    }
  }, [remember]);

  const reload = useCallback(async () => {
    try {
      const data = await loadTickets();
      setTickets(new Map(data.tickets.map((t) => [t.id, t])));
      remember(data.tickets);
      setStats(data.stats);
      setLoadError(null);
    } catch (err) {
      setLoadError(err.message);
    }
  }, [remember]);

  useEffect(() => {
    document.documentElement.lang = "en";
    reload();
    const stop = subscribe((event) => {
      if (event.ticket) apply(event.ticket, event.type === "ticket_created");
      if (event.stats) setStats(event.stats);
    }, (state) => { setLink(state); if (state === "live") reload(); });
    const poll = setInterval(reload, 10000);           // catches anything a dropped socket missed
    const tick = setInterval(() => setNow(Date.now()), 15000);
    return () => { stop(); clearInterval(poll); clearInterval(tick); };
  }, [reload, apply]);

  const current = findTeam(team);

  useEffect(() => {
    document.title = `${current.name} · Call bell requests`;
    const url = new URL(window.location.href);
    url.searchParams.set("team", team);
    window.history.replaceState(null, "", url);
  }, [team, current]);

  // Each ticket with its team and level, ordered by level then longest wait.
  const rows = useMemo(() => [...tickets.values()]
    .map((t) => { const tm = teamFor(t.department); return { ticket: t, team: tm, level: levelOf(t, tm) }; })
    .sort((a, b) => a.level - b.level || a.ticket.created_at - b.ticket.created_at), [tickets]);

  const counts = useMemo(() => {
    const c = {};
    for (const { ticket, team: tm, level } of rows) {
      c[tm.key] ||= { open: 0, urgent: 0 };
      c[tm.key].open += 1;
      if (level <= 2 && ticket.status === "open") c[tm.key].urgent += 1;
    }
    return c;
  }, [rows]);

  const shown = rows.filter((r) => r.team.key === team);
  const byDept = stats?.by_department;
  const received = byDept
    ? current.codes.reduce((sum, code) => sum + (byDept[code]?.total || 0), 0)
    : [...seen.values()].filter((code) => teamFor(code).key === team).length;
  const mine = {
    open: shown.length,
    urgent: shown.filter((r) => r.level <= 2 && r.ticket.status === "open").length,
    overdue: shown.filter((r) => isOverdue(r.ticket, r.level, now)).length,
  };

  async function changeStatus(id, status) {
    apply(await setStatus(id, status), false);
  }

  return (
    <div className="dash" style={{ "--team": current.color }}>
      <header className="dash-head">
        <div className="head-row">
          <div className="title">
            <p className="eyebrow">
              Call bell requests
              <span className={`link ${link}`} role="status">
                {link === "live" ? "Live" : link === "down" ? "Reconnecting…" : "Connecting…"}
              </span>
            </p>
            <h1>{current.name}</h1>
            <p className="covers">{current.covers}</p>
          </div>
          <dl className="dash-stats">
            <div><dt>Open</dt><dd>{mine.open}</dd></div>
            <div><dt>Urgent waiting</dt><dd>{mine.urgent}</dd></div>
            <div><dt>Overdue</dt><dd>{mine.overdue}</dd></div>
            <div className="global" title={byDept ? "" : "Counted since this screen opened"}>
              <dt>Requests so far</dt><dd>{received}</dd>
            </div>
          </dl>
        </div>
        <TeamSwitch team={team} onChange={setTeam} counts={counts} />
      </header>

      <main className="dash-main">
        {loadError && (
          <div className="load-error" role="alert">
            <span>Could not load requests. {loadError}</span>
            <button type="button" onClick={reload}>Try again</button>
          </div>
        )}

        {shown.length === 0 && !loadError ? (
          <p className="none">Nothing waiting for {current.name}.</p>
        ) : (
          <div className="queue">
            {shown.map(({ ticket, team: tm, level }) => (
              <div key={ticket.id} className={fresh.has(ticket.id) ? "arrive" : ""}>
                <TicketCard ticket={ticket} team={tm} level={level} now={now} onStatus={changeStatus} />
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
