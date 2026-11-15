import {
  CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis,
} from "recharts";
import type { LiveEvent } from "../api/client";

const LINE_COLORS = ["#38bdf8", "#22c55e", "#f472b6", "#facc15"];

export default function WaveChart({ events, waveBuoys }: { events: LiveEvent[]; waveBuoys: string[] }) {
  const rows = new Map<number, Record<string, number>>();
  const attacks: { t: number; wave: number }[] = [];
  for (const e of events) {
    const t = e.observed_at ? Date.parse(e.observed_at) : NaN;
    const wave = e.data.wave_height_m;
    if (Number.isNaN(t) || wave === null || wave === undefined) continue;
    if (e.simulated_attack) {
      attacks.push({ t, wave });
      continue;
    }
    if (e.verdict !== "TRUSTED" && e.verdict !== "CONFIRMED_EVENT") continue;
    const row = rows.get(t) ?? { t };
    row[e.buoy_id] = wave;
    rows.set(t, row);
  }
  const data = [...rows.values()].sort((a, b) => a.t - b.t);
  const fmt = (t: number) => new Date(t).toISOString().slice(5, 13).replace("T", " ") + "h";

  return (
    <section className="card">
      <h2>Wave height, real NOAA data <span className="muted small">(red = injected fake values)</span></h2>
      <ResponsiveContainer width="100%" height={240}>
        <ComposedChart data={data} margin={{ top: 10, right: 16, bottom: 0, left: -10 }}>
          <CartesianGrid stroke="#1f4a70" strokeDasharray="3 3" />
          <XAxis dataKey="t" type="number" domain={["dataMin", "dataMax"]} tickFormatter={fmt}
                 stroke="#8fb0cc" fontSize={11} />
          <YAxis stroke="#8fb0cc" fontSize={11} unit=" m" />
          <Tooltip labelFormatter={(t) => fmt(Number(t))}
                   contentStyle={{ background: "#0d2740", border: "1px solid #1f4a70" }} />
          <Legend />
          {waveBuoys.map((b, i) => (
            <Line key={b} dataKey={b} stroke={LINE_COLORS[i % LINE_COLORS.length]} dot={false}
                  connectNulls isAnimationActive={false} />
          ))}
          <Scatter name="fake (attack)" data={attacks} dataKey="wave" fill="#ef4444" isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </section>
  );
}
