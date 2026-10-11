import MicButton from "./MicButton.jsx";

export default function VoicePanel({ voice, busy, t }) {
  const { state, level, hint } = voice;
  const label = { idle: t.speak, listening: t.listening, working: t.working }[state];
  let sub = state === "idle" ? t.speakSub : state === "listening" ? t.listeningSub : "";
  let tone = "";
  if (state === "listening" && hint === "quiet") { sub = t.louder; tone = "quiet"; }
  if (state === "listening" && hint === "good") { sub = t.good; tone = "good"; }

  const onPress = () => (state === "listening" ? voice.finish() : voice.start());

  return (
    <div className="voice-panel" role="tabpanel" id="panel-voice" aria-labelledby="tab-voice">
      <MicButton state={state} level={level} label={label}
                 disabled={state === "working" || busy} onPress={onPress}>
        <div className="voice-text">
          <p className="voice-label" aria-live="polite">{label}</p>
          <p className={`voice-sub ${tone}`} aria-live="polite">{sub}</p>
        </div>
      </MicButton>
    </div>
  );
}
