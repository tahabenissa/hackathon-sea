import Placeholder from "../components/Placeholder";

export default function SystemHealth() {
  return (
    <Placeholder
      title="System health"
      plan={[
        "Message rate and end-to-end detection latency",
        "API / MQTT / database status",
        "CPU, RAM and disk of the Vultr instance",
      ]}
    />
  );
}
