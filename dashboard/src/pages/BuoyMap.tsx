import Placeholder from "../components/Placeholder";

export default function BuoyMap() {
  return (
    <Placeholder
      title="Buoy network map"
      plan={[
        "Leaflet map with every buoy at its real NDBC position",
        "Marker colour = current trust verdict (green / amber / red)",
        "Click a buoy: latest reading, evidence, history",
      ]}
    />
  );
}
