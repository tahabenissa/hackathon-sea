import Placeholder from "../components/Placeholder";

export default function Incidents() {
  return (
    <Placeholder
      title="Incidents & alerts"
      plan={[
        "Timeline of incidents with verdict and human-readable explanation",
        "Operator review: confirm attack / mark false positive",
        "Alert states: issued, held, released, discarded",
      ]}
    />
  );
}
