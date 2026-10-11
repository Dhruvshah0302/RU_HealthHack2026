import { DEPARTMENTS } from "../departments.js";

// Switch between team screens: Clinical, then the support teams. Each shows its open count.
export default function TeamSwitch({ team, onChange, counts }) {
  const tab = (d) => {
    const c = counts[d.key] || { open: 0, urgent: 0 };
    return (
      <button key={d.key} type="button" role="tab" aria-selected={team === d.key} onClick={() => onChange(d.key)}
              style={{ "--tab": d.color }} className="team-tab">
        <span className="swatch" aria-hidden="true" />
        <span className="team-name">{d.short || d.name}</span>
        <span className="team-count" aria-label={`${c.open} open${c.urgent ? `, ${c.urgent} urgent` : ""}`}>
          {c.open}
          {c.urgent > 0 && <span className="urgent-dot" aria-hidden="true" />}
        </span>
      </button>
    );
  };

  return (
    <nav className="team-switch" role="tablist" aria-label="Team screen">
      <div className="team-group">
        <span className="group-label">Clinical</span>
        <div className="tabs">{DEPARTMENTS.filter((d) => d.group === "clinical").map(tab)}</div>
      </div>
      <div className="team-group">
        <span className="group-label">Support</span>
        <div className="tabs">{DEPARTMENTS.filter((d) => d.group === "support").map(tab)}</div>
      </div>
    </nav>
  );
}
