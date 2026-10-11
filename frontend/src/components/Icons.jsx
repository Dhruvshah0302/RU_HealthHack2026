// Line icons, 24x24, drawn in the current text colour.
const base = {
  viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2,
  strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true,
};

export function MicIcon(props) {
  return (
    <svg {...base} {...props}>
      <rect x="9" y="2.5" width="6" height="12" rx="3" fill="currentColor" />
      <path d="M5 11a7 7 0 0 0 14 0" /><path d="M12 18v3.5" />
    </svg>
  );
}

export function KeyboardIcon(props) {
  return (
    <svg {...base} {...props}>
      <rect x="2" y="5" width="20" height="14" rx="2.5" />
      <path d="M6 9h.01M10 9h.01M14 9h.01M18 9h.01M6 13h.01M18 13h.01M9 15.5h6" />
    </svg>
  );
}

export function BedIcon(props) {
  return (
    <svg {...base} {...props}>
      <path d="M3 18V6" /><path d="M3 14h18v4" /><path d="M21 14v-2a3 3 0 0 0-3-3h-7v5" />
      <circle cx="7" cy="11" r="1.6" />
    </svg>
  );
}

export function CloseIcon(props) {
  return <svg {...base} {...props}><path d="M6 6l12 12M18 6L6 18" /></svg>;
}

export function NurseIcon(props) {
  return (
    <svg {...base} {...props}>
      <path d="M10 4h4v6h6v4h-6v6h-4v-6H4v-4h6z" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function SendIcon(props) {
  return <svg {...base} {...props}><path d="M4 12l16-8-6 16-2.5-6.5z" /><path d="M11.5 13.5L20 4" /></svg>;
}

/* One icon per team, used on the confirmation. */
export function TeamIcon({ dept, ...props }) {
  switch (dept) {
    case "housekeeping_facilities":       // sparkle: a clean room
      return <svg {...base} {...props}><path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z" /><path d="M18 15l.8 2.2L21 18l-2.2.8L18 21l-.8-2.2L15 18l2.2-.8z" /></svg>;
    case "food_services":                 // tray with a cover
      return <svg {...base} {...props}><path d="M4 16a8 8 0 0 1 16 0" /><path d="M2.5 16h19" /><path d="M12 6V4.5" /><path d="M5 19.5h14" /></svg>;
    case "unit_clerk_it":                 // a screen
      return <svg {...base} {...props}><rect x="3" y="4.5" width="18" height="12" rx="2" /><path d="M8.5 20h7M12 16.5V20" /></svg>;
    default:                              // nurse
      return <NurseIcon {...props} />;
  }
}

/* Icons for the quick choices, matched by their position in i18n.js. */
export function QuickIcon({ name, ...props }) {
  switch (name) {
    case "water":
      return <svg {...base} {...props}><path d="M6 3h12l-1.5 17a1.5 1.5 0 0 1-1.5 1.4H9a1.5 1.5 0 0 1-1.5-1.4z" /><path d="M6.6 9.5h10.8" /></svg>;
    case "blanket":
      return <svg {...base} {...props}><path d="M3 6.5C6 4.5 9 8.5 12 6.5s6 2 9 0v11c-3 2-6-2-9 0s-6-2-9 0z" /><path d="M3 12c3-2 6 2 9 0s6 2 9 0" /></svg>;
    case "pillow":
      return <svg {...base} {...props}><path d="M4.5 7.5C8 5 16 5 19.5 7.5c1.5 3 1.5 6 0 9C16 19 8 19 4.5 16.5c-1.5-3-1.5-6 0-9z" /></svg>;
    case "clean":
      return <svg {...base} {...props}><path d="M14 3l-4 9" /><path d="M6.5 12h7l2 9h-11z" /><path d="M9 16.5v4.5M12 16.5v4.5" /></svg>;
    case "tv":
      return <TeamIcon dept="unit_clerk_it" {...props} />;
    default:                               // meal
      return <TeamIcon dept="food_services" {...props} />;
  }
}

/* A plain heraldic shield, the knight motif used across the page. */
export const SHIELD_PATH = "M12 1.8l8.6 3.1v6.3c0 5.4-3.6 9.6-8.6 11.1-5-1.5-8.6-5.7-8.6-11.1V4.9z";
export function ShieldIcon({ children, ...props }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" {...props}>
      <path d={SHIELD_PATH} fill="currentColor" />
      {children}
    </svg>
  );
}

/* Confirmation: a shield outline draws itself, then the tick. */
export function CheckMark(props) {
  return (
    <svg viewBox="0 0 52 56" aria-hidden="true" {...props}>
      <path className="check-fill" d="M26 4l19 6.8v13.8c0 11.9-7.9 21.1-19 24.4C14.9 45.7 7 36.5 7 24.6V10.8z" />
      <path className="check-ring" d="M26 4l19 6.8v13.8c0 11.9-7.9 21.1-19 24.4C14.9 45.7 7 36.5 7 24.6V10.8z" fill="none" />
      <path className="check-tick" d="M16.5 27.5l6.5 6.5L36 21" fill="none" />
    </svg>
  );
}
