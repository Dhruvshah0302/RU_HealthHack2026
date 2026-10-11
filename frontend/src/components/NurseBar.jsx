import { NurseIcon } from "./Icons.jsx";

// Always on screen, in both modes and over the listening view, and never depends on the sorter.
export default function NurseBar({ onPress, t }) {
  return (
    <div className="nursebar">
      <button type="button" onClick={onPress}><NurseIcon /><span>{t.nurse}</span></button>
      <p>{t.nurseHint}</p>
    </div>
  );
}
