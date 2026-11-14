import Placeholder from "../components/Placeholder";

export default function LiveData() {
  return (
    <Placeholder
      title="Live ocean data"
      plan={[
        "Recharts time series per buoy (wave height, wind, pressure, temperature)",
        "Flagged points highlighted in red, held alerts in amber",
        "Live updates from the /ws/live WebSocket",
      ]}
    />
  );
}
