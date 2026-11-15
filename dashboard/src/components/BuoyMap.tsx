import "leaflet/dist/leaflet.css";
import { CircleMarker, MapContainer, Popup, TileLayer, Tooltip } from "react-leaflet";
import type { Buoy, LiveEvent } from "../api/client";

const COLORS: Record<string, string> = {
  TRUSTED: "#22c55e",
  CONFIRMED_EVENT: "#a78bfa",
  SUSPECTED_FDI: "#f59e0b",
  SUPPRESSED_WARNING: "#f59e0b",
  REJECTED: "#ef4444",
  OFFLINE: "#64748b",
};

interface Props {
  buoys: Buoy[];
  latest: Record<string, LiveEvent>;
  offline: Set<string>;
}

function fmt(v: number | null | undefined, unit: string) {
  return v === null || v === undefined ? "n/a" : `${v.toFixed(1)} ${unit}`;
}

export default function BuoyMap({ buoys, latest, offline }: Props) {
  const placed = buoys.filter((b) => b.lat !== null && b.lon !== null);
  return (
    <MapContainer center={[27.2, -83.8]} zoom={6} scrollWheelZoom={false} className="map">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />
      {placed.map((b) => {
        const e = latest[b.buoy_id];
        const state = offline.has(b.buoy_id) || !e ? "OFFLINE" : e.verdict;
        return (
          <CircleMarker
            key={b.buoy_id}
            center={[b.lat as number, b.lon as number]}
            radius={11}
            pathOptions={{ color: COLORS[state], fillColor: COLORS[state], fillOpacity: 0.85, weight: 3 }}
          >
            <Tooltip permanent direction="right" offset={[12, 0]} className="map-label">
              {b.buoy_id} · {state === "OFFLINE" ? "offline" : fmt(e?.data.wave_height_m, "m")}
            </Tooltip>
            <Popup>
              <strong>{b.buoy_id} {b.name}</strong>
              <br />NOAA station {b.ndbc_station}
              <br />Waves: {fmt(e?.data.wave_height_m, "m")}
              <br />Wind: {fmt(e?.data.wind_speed_ms, "m/s")}
              <br />Pressure: {fmt(e?.data.pressure_hpa, "hPa")}
              <br />Status: {state}
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
