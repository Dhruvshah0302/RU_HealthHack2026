import { useRef } from "react";
import { MicIcon, KeyboardIcon } from "./Icons.jsx";

// Voice / Type toggle at the top centre of the page.
export default function ModeSwitch({ mode, onChange, t }) {
  const refs = { voice: useRef(null), type: useRef(null) };

  function onKeyDown(e) {
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    const next = mode === "voice" ? "type" : "voice";
    onChange(next);
    refs[next].current?.focus();
  }

  const tab = (value, label, Icon) => (
    <button
      ref={refs[value]} type="button" role="tab" id={`tab-${value}`} aria-controls={`panel-${value}`}
      aria-selected={mode === value} tabIndex={mode === value ? 0 : -1}
      onClick={() => onChange(value)} onKeyDown={onKeyDown}
    >
      <Icon /><span>{label}</span>
    </button>
  );

  return (
    <div className="switch" role="tablist" aria-label={t.howToAsk} data-mode={mode}>
      <span className="thumb" aria-hidden="true" />
      {tab("voice", t.modeVoice, MicIcon)}
      {tab("type", t.modeType, KeyboardIcon)}
    </div>
  );
}
