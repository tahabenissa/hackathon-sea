import Placeholder from "../components/Placeholder";

export default function Comparison() {
  return (
    <Placeholder
      title="Unprotected vs SeaShield"
      plan={[
        "Two panels fed by the same data stream",
        "Left: naive centre fires a fake disaster alert",
        "Right: SeaShield holds it and shows the evidence",
      ]}
    />
  );
}
