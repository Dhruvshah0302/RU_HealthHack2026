import { forwardRef } from "react";
import { QuickIcon, SendIcon } from "./Icons.jsx";

const TypePanel = forwardRef(function TypePanel({ text, onText, onSubmit, busy, t }, textRef) {
  return (
    <div className="type-panel" role="tabpanel" id="panel-type" aria-labelledby="tab-type">
      <form className="compose" onSubmit={(e) => { e.preventDefault(); onSubmit({ text }); }}>
        <label className="field" htmlFor="request-text">{t.typeHint}</label>
        <textarea id="request-text" ref={textRef} maxLength={600} autoComplete="off"
                  value={text} onChange={(e) => onText(e.target.value)} />
        <button className="send" type="submit" disabled={busy}>
          <SendIcon /><span>{busy ? t.sending : t.send}</span>
        </button>
      </form>
      <h2>{t.quickTitle}</h2>
      <div className="quick">
        {t.quick.map(([dept, label, phrase, icon]) => (
          <button key={label} type="button" disabled={busy} style={{ "--stripe": `var(--${dept})` }}
                  onClick={() => onSubmit({ text: phrase })}>
            <span className="quick-icon"><QuickIcon name={icon} /></span>
            <span>{label}</span>
          </button>
        ))}
      </div>
    </div>
  );
});

export default TypePanel;
