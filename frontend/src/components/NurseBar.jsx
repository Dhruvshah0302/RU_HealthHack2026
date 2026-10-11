// Always on screen, in both modes, and never depends on the sorter.
export default function NurseBar({ onPress, t }) {
  return (
    <div className="nursebar">
      <button type="button" onClick={onPress}>{t.nurse}</button>
      <p>{t.nurseHint}</p>
    </div>
  );
}
