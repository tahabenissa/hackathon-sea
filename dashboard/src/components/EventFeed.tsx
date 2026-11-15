import type { LiveEvent } from "../api/client";
import VerdictBadge from "./VerdictBadge";

function v(x: number | null | undefined, unit: string) {
  return x === null || x === undefined ? "" : `${x.toFixed(1)}${unit}`;
}

export default function EventFeed({ events }: { events: LiveEvent[] }) {
  const rows = events.slice(-40).reverse();
  return (
    <section className="card">
      <h2>Live message feed</h2>
      <div className="feed">
        <table>
          <thead>
            <tr>
              <th>Measured</th><th>Buoy</th><th>Waves</th><th>Wind</th><th>Pressure</th>
              <th>Verdict</th><th>Why</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((e) => (
              <tr key={`${e.buoy_id}-${e.seq}-${e.received_at}`} className={e.simulated_attack ? "row-attack" : ""}>
                <td>{e.observed_at?.replace("T", " ").slice(5, 16)}</td>
                <td>{e.buoy_id}</td>
                <td>{v(e.data.wave_height_m, " m")}</td>
                <td>{v(e.data.wind_speed_ms, " m/s")}</td>
                <td>{v(e.data.pressure_hpa, "")}</td>
                <td>
                  <VerdictBadge verdict={e.verdict} />
                  {e.simulated_attack && <span className="tag tag-bad">attack: {e.simulated_attack}</span>}
                </td>
                <td className="why">{e.explanation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
